"""Document upload use case (PLAN §10.1; FR-3).

**Why the full FR-3 file-security stage runs here, synchronously, instead of
in the `documents` Celery worker** (see also ADR-013 and
`app/pipeline/document_tasks.py`):

1. **Dedup must gate the HTTP response** (FR-3 AC3: a re-upload of the same
   hash by the same user *returns the existing `source_document`*). That
   decision has to be made before any new row is created or any bytes are
   written to storage — it cannot happen after the fact in an async worker
   (CLAUDE.md §8's named outcome: "no second object-storage write").
2. **PDF passwords must never cross the Celery/Redis boundary** (PLAN
   §24.10). The only place a password can be used at all is inside the
   synchronous request that received it.

Both constraints force the entire security stage into this one place. The
`documents` Celery task (T2.5) still exists — it performs the state
machine's `SECURITY_CHECK → EXTRACTING` transition for documents that have
already passed validation here, which is the literal Sprint 2 exit criterion
("uploading a fixture PDF stores it, dedups on re-upload, advances to
EXTRACTING") and the seam Sprint 3's real OCR/extraction worker extends.
"""

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError, ValidationError
from app.engines.file_security import FileSecurityConfig, SecurityOutcome, validate
from app.integrations.storage import get_storage_port, raw_document_key
from app.models.correction import Correction
from app.models.document_verification_result import DocumentVerificationResult
from app.models.enums import ActorTypeEnum, DocStatusEnum, SourceTypeEnum
from app.models.source_document import SourceDocument
from app.models.transaction import Transaction
from app.models.user import User
from app.pipeline.dispatch import dispatch_document_processing
from app.repositories.correction_repository import CorrectionRepository
from app.repositories.document_verification_result_repository import (
    DocumentVerificationResultRepository,
)
from app.repositories.financial_account_repository import FinancialAccountRepository
from app.repositories.source_document_repository import SourceDocumentRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services import audit_service


@dataclass(frozen=True)
class CorrectionInput:
    """Service-layer input for `DocumentService.review` — the controller
    unpacks the `ReviewRequest` Pydantic DTO into these before calling the
    service (PLAN §10.1: services depend on plain data, not `schemas/`)."""

    transaction_id: uuid.UUID | None
    correction_type: str
    note: str | None
    raw_extracted_value: str | int | bool | None
    system_normalized_value: str | int | bool | None
    user_proposed_value: str | int | bool | None


_UNSAFE_FILENAME_CHARS = re.compile(r"[\x00-\x1f/\\]")
_MAX_FILENAME_LENGTH = 255

_OUTCOME_STATUS: dict[SecurityOutcome, DocStatusEnum] = {
    SecurityOutcome.PASSED: DocStatusEnum.UPLOADED,
    SecurityOutcome.REJECTED_SECURITY: DocStatusEnum.REJECTED_SECURITY,
    SecurityOutcome.VALIDATION_FAILED: DocStatusEnum.VALIDATION_FAILED,
}

_OUTCOME_AUDIT_ACTION: dict[SecurityOutcome, str] = {
    SecurityOutcome.PASSED: "document.uploaded",
    SecurityOutcome.REJECTED_SECURITY: "document.rejected_security",
    SecurityOutcome.VALIDATION_FAILED: "document.validation_failed",
}


class DocumentService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._documents = SourceDocumentRepository(db)
        self._financial_accounts = FinancialAccountRepository(db)

    def upload(
        self,
        *,
        user: User,
        data: bytes,
        file_name: str,
        declared_content_type: str,
        source_type: SourceTypeEnum,
        password: str | None,
        financial_account_id: uuid.UUID | None,
    ) -> tuple[SourceDocument, bool]:
        """Returns `(document, created)` — `created=False` means FR-3 AC3's
        dedup path returned an existing document untouched."""
        file_hash = hashlib.sha256(data).hexdigest()

        existing = self._documents.get_by_user_and_hash(user.id, file_hash)
        if existing is not None:
            return existing, False

        if financial_account_id is not None:
            account = self._financial_accounts.get_by_id(financial_account_id)
            if account is None or account.user_id != user.id:
                raise NotFoundError("Financial account not found")

        settings = get_settings()
        config = FileSecurityConfig(
            max_upload_bytes=settings.max_upload_mb * 1024 * 1024,
            max_pdf_pages=settings.max_pdf_pages,
            max_image_pixels=settings.max_image_pixels,
        )
        result = validate(
            data, declared_content_type=declared_content_type, password=password, config=config
        )

        document = SourceDocument(
            id=uuid.uuid4(),
            user_id=user.id,
            financial_account_id=financial_account_id,
            file_name=_sanitize_filename(file_name),
            file_hash=file_hash,
            mime_type=result.detected_mime,
            source_type=source_type,
            page_count=result.page_count,
            uploaded_at=datetime.now(UTC),
            status=_OUTCOME_STATUS[result.outcome],
        )

        if result.outcome is SecurityOutcome.PASSED:
            storage_path = raw_document_key(str(user.id), str(document.id))
            get_storage_port().put_object(storage_path, data, content_type=result.detected_mime)
            document.storage_path = storage_path

        self._documents.add(document)
        audit_service.record(
            self._db,
            actor_type=ActorTypeEnum.USER,
            actor_id=user.id,
            action=_OUTCOME_AUDIT_ACTION[result.outcome],
            entity_type="source_document",
            entity_id=document.id,
            metadata={"reason_code": result.reason_code},
        )
        self._db.commit()

        if result.outcome is SecurityOutcome.PASSED:
            dispatch_document_processing(document.id)

        return document, True

    def get_status(self, user: User, document_id: uuid.UUID) -> SourceDocument:
        document = self._documents.get_by_id(document_id)
        if document is None or document.user_id != user.id:
            raise NotFoundError("Document not found")
        return document

    def get_verification(self, user: User, document_id: uuid.UUID) -> DocumentVerificationResult:
        """FR-5; PLAN §12.2 `GET /documents/{id}/verification`."""
        document = self.get_status(user, document_id)
        result = DocumentVerificationResultRepository(self._db).get_latest_for_document(document.id)
        if result is None:
            raise NotFoundError("Verification result not found")
        return result

    def list_transactions(
        self, user: User, document_id: uuid.UUID, *, limit: int, cursor: uuid.UUID | None
    ) -> list[Transaction]:
        """FR-4; PLAN §12.2 `GET /documents/{id}/transactions`, cursor-paginated
        per §12.1."""
        document = self.get_status(user, document_id)
        return TransactionRepository(self._db).list_for_document(
            document.id, limit=limit, cursor=cursor
        )

    def review(self, user: User, document_id: uuid.UUID, corrections: list[CorrectionInput]) -> int:
        """FR-14 AC1/AC3: records flags/corrections without overwriting raw
        evidence (`transactions`/`document_processing_runs` rows are never
        mutated here). PLAN §12.2 `POST /documents/{id}/review`."""
        document = self.get_status(user, document_id)
        if document.status != DocStatusEnum.REVIEW_PENDING:
            raise ValidationError(
                "Document is not awaiting review",
                details={"status": document.status.value},
            )

        transactions = TransactionRepository(self._db)
        for correction in corrections:
            if correction.transaction_id is None:
                continue
            transaction = transactions.get_by_id(correction.transaction_id)
            if transaction is None or transaction.source_document_id != document.id:
                raise NotFoundError("Transaction not found")

        rows = [
            Correction(
                id=uuid.uuid4(),
                user_id=user.id,
                transaction_id=correction.transaction_id,
                correction_type=correction.correction_type,
                payload_json={
                    "raw_extracted_value": correction.raw_extracted_value,
                    "system_normalized_value": correction.system_normalized_value,
                    "user_proposed_value": correction.user_proposed_value,
                    **({"note": correction.note} if correction.note else {}),
                },
            )
            for correction in corrections
        ]
        if rows:
            CorrectionRepository(self._db).add_all(rows)
        audit_service.record(
            self._db,
            actor_type=ActorTypeEnum.USER,
            actor_id=user.id,
            action="document.review_submitted",
            entity_type="source_document",
            entity_id=document.id,
            metadata={"correction_count": len(rows)},
        )
        self._db.commit()
        return len(rows)

    def confirm(self, user: User, document_id: uuid.UUID) -> SourceDocument:
        """FR-14 AC2: user confirms the review state before scoring. PLAN
        §8.2 `REVIEW_PENDING -> NORMALIZING`; PLAN §12.2 `POST /documents/{id}/confirm`."""
        document = self.get_status(user, document_id)
        if document.status != DocStatusEnum.REVIEW_PENDING:
            raise ValidationError(
                "Document is not awaiting review confirmation",
                details={"status": document.status.value},
            )

        document.status = DocStatusEnum.NORMALIZING
        self._db.flush()
        audit_service.record(
            self._db,
            actor_type=ActorTypeEnum.USER,
            actor_id=user.id,
            action="document.review_confirmed",
            entity_type="source_document",
            entity_id=document.id,
        )
        self._db.commit()
        return document


def _sanitize_filename(file_name: str) -> str:
    """FR-3 AC5: filenames are never used to build storage keys (see
    `raw_document_key`), but the display name stored in the DB is still
    stripped of path separators/control characters and length-capped."""
    name = _UNSAFE_FILENAME_CHARS.sub("_", file_name).strip()
    return (name or "upload")[:_MAX_FILENAME_LENGTH]
