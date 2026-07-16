"""Extraction pipeline stage (PLAN §8.2 `EXTRACTING -> VERIFYING`; §15.3
item 2; FR-4). Sprint 3, T3.1/T3.2.

Fetches the already-security-checked raw bytes from object storage, runs
the pure extraction engine, persists an append-only `DocumentProcessingRun`
+ normalized `Transaction` rows, and advances the document's state. Only
rows with a nonzero amount become `transactions` (an opening/anchor "Saldo
Awal" row with `amount=0` is a balance marker, not a real transaction, and
would otherwise violate `ck_transactions_amount_positive`) — the full,
unfiltered row sequence is still used for Trust-Layer balance
reconstruction (`app/services/verification_service.py` re-derives it from
the same immutable raw bytes rather than reading it back from
`transactions`, see that module's docstring for why).
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.engines.extraction import ExtractionResult, ExtractionStatus, extract
from app.engines.extraction.schema import ExtractedRow, duplicate_row_flags
from app.integrations.ocr import get_ocr_port
from app.integrations.storage import get_storage_port
from app.models.document_processing_run import DocumentProcessingRun
from app.models.enums import (
    AccountTypeEnum,
    ActorTypeEnum,
    ConnectionTypeEnum,
    DirEnum,
    DocStatusEnum,
    PipelineStageEnum,
    ProcessingStatusEnum,
)
from app.models.financial_account import FinancialAccount
from app.models.source_document import SourceDocument
from app.models.transaction import Transaction
from app.repositories.document_processing_run_repository import DocumentProcessingRunRepository
from app.repositories.financial_account_repository import FinancialAccountRepository
from app.repositories.source_document_repository import SourceDocumentRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services import audit_service
from app.services.pipeline_stage_tracking import track_stage

_IMAGE_MIME_TYPES = frozenset({"image/png", "image/jpeg"})

# Sprint 3 gap-fill (PLAN §24.11, ADR-014): no dedicated create/account route
# ships in MVP (PLAN §11.3 `financial_accounts` docstring), so extraction
# infers a coarse account type from the document's declared source and
# auto-provisions a `financial_accounts` row the first time a user uploads
# from that class of source.
_SOURCE_TYPE_TO_ACCOUNT_TYPE: dict[str, AccountTypeEnum] = {
    "BANK_API": AccountTypeEnum.BANK,
    "SIGNED_STATEMENT": AccountTypeEnum.BANK,
    "ORIGINAL_PDF": AccountTypeEnum.BANK,
    "EXPORTED_CSV": AccountTypeEnum.BANK,
    "SCREENSHOT": AccountTypeEnum.EWALLET,
    "PHOTO": AccountTypeEnum.EWALLET,
}


def run_extraction(db: Session, document_id: uuid.UUID) -> None:
    """Idempotent/resumable per NFR-3: a document not sitting in `EXTRACTING`
    has already been extracted (or is terminal), so a retry is a no-op."""
    documents = SourceDocumentRepository(db)
    document = documents.get_by_id(document_id)
    if document is None or document.status != DocStatusEnum.EXTRACTING:
        return

    with track_stage(db, document.id, PipelineStageEnum.EXTRACTION):
        assert document.storage_path is not None  # noqa: S101 - PASSED docs always have one
        data = get_storage_port().get_object(document.storage_path)
        ocr_text = maybe_recognize_text(data, document.mime_type)
        result = extract(data, mime_type=document.mime_type, ocr_text=ocr_text)

        processing_run = _persist_processing_run(db, document, result)

        if result.status is not ExtractionStatus.EXTRACTED:
            document.status = DocStatusEnum.UNSUPPORTED_FORMAT
            db.flush()
            audit_service.record(
                db,
                actor_type=ActorTypeEnum.SYSTEM,
                actor_id=None,
                action="document.extraction_unsupported_format",
                entity_type="source_document",
                entity_id=document.id,
                metadata={"reason_code": result.reason_code},
            )
            db.commit()
            return

        account = _ensure_financial_account(db, document, result)
        _persist_transactions(db, document, account, processing_run, result)
        document.statement_start_date = result.statement_start_date
        document.statement_end_date = result.statement_end_date
        document.status = DocStatusEnum.VERIFYING
        db.flush()
        audit_service.record(
            db,
            actor_type=ActorTypeEnum.SYSTEM,
            actor_id=None,
            action="document.extraction_completed",
            entity_type="source_document",
            entity_id=document.id,
            metadata={"row_count": len(result.rows), "format_name": result.format_name},
        )
        db.commit()


def maybe_recognize_text(data: bytes, mime_type: str) -> str | None:
    if mime_type not in _IMAGE_MIME_TYPES:
        return None
    try:
        return get_ocr_port().extract_text(data)
    except Exception:  # noqa: BLE001 - OCR failure degrades to UNSUPPORTED_FORMAT, not a crash
        return None


def _persist_processing_run(
    db: Session, document: SourceDocument, result: ExtractionResult
) -> DocumentProcessingRun:
    now = datetime.now(UTC)
    output_hash = _hash_rows(result.rows) if result.status is ExtractionStatus.EXTRACTED else None
    run = DocumentProcessingRun(
        id=uuid.uuid4(),
        source_document_id=document.id,
        parser_name=result.parser_name,
        parser_version=result.parser_version,
        format_name=result.format_name,
        format_detection_confidence=result.format_detection_confidence,
        status=(
            ProcessingStatusEnum.COMPLETE
            if result.status is ExtractionStatus.EXTRACTED
            else ProcessingStatusEnum.FAILED
        ),
        input_hash=document.file_hash,
        output_hash=output_hash,
        started_at=now,
        completed_at=now,
    )
    return DocumentProcessingRunRepository(db).add(run)


def _ensure_financial_account(
    db: Session, document: SourceDocument, result: ExtractionResult
) -> FinancialAccount:
    financial_accounts = FinancialAccountRepository(db)
    if document.financial_account_id is not None:
        account = financial_accounts.get_by_id(document.financial_account_id)
        assert account is not None  # noqa: S101 - FK guarantees existence
        return account

    account_type = _SOURCE_TYPE_TO_ACCOUNT_TYPE.get(
        document.source_type.value, AccountTypeEnum.BANK
    )
    existing = financial_accounts.get_first_auto_provisioned(document.user_id, account_type)
    if existing is not None:
        document.financial_account_id = existing.id
        return existing

    account = FinancialAccount(
        id=uuid.uuid4(),
        user_id=document.user_id,
        account_type=account_type,
        provider_name="auto-detected",
        masked_account_number=result.detected_account_holder_name,
        connection_type=ConnectionTypeEnum.UPLOAD,
    )
    financial_accounts.add(account)
    document.financial_account_id = account.id
    return account


def _persist_transactions(
    db: Session,
    document: SourceDocument,
    account: FinancialAccount,
    processing_run: DocumentProcessingRun,
    result: ExtractionResult,
) -> None:
    rows = [
        Transaction(
            id=uuid.uuid4(),
            user_id=document.user_id,
            financial_account_id=account.id,
            source_document_id=document.id,
            processing_run_id=processing_run.id,
            transaction_date=row.transaction_date,
            transaction_time=row.transaction_time,
            amount=row.amount,
            direction=DirEnum(row.direction.value),
            balance_after=row.balance_after,
            raw_description=row.raw_description,
            extraction_confidence=row.extraction_confidence,
            row_hash=_row_hash(row),
            is_duplicate=is_duplicate,
        )
        for row, is_duplicate in zip(result.rows, duplicate_row_flags(result.rows), strict=True)
        if row.amount > 0
    ]
    if rows:
        TransactionRepository(db).add_all(rows)


def _row_hash(row: ExtractedRow) -> str:
    canonical = "|".join(
        [
            row.transaction_date.isoformat(),
            row.transaction_time.isoformat() if row.transaction_time else "",
            str(row.amount),
            row.direction.value,
            row.raw_description,
            str(row.balance_after),
        ]
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _hash_rows(rows: list[ExtractedRow]) -> str:
    canonical = json.dumps(
        [
            {
                "date": row.transaction_date.isoformat(),
                "time": row.transaction_time.isoformat() if row.transaction_time else None,
                "amount": row.amount,
                "direction": row.direction.value,
                "description": row.raw_description,
                "balance_after": row.balance_after,
            }
            for row in rows
        ],
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
