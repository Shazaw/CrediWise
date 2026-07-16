"""`/api/v1/documents` routes (PLAN §12.2; FR-3). Thin: parse/validate, call
one service method, map to response DTO — no business logic (PLAN §10.1).

Ownership for `GET /documents/{id}/status` is enforced inside
`DocumentService.get_status` (a mismatched `user_id` raises `NotFoundError`,
i.e. a 404 rather than a 403 — deliberately not confirming another user's
document exists, PLAN §18.4 BOLA/IDOR) rather than via `core/deps.require`'s
`ownership_getter`, which only has access to `(db, current_user)` and not
this route's `{id}` path parameter.
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import require
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.document_verification_result import DocumentVerificationResult
from app.models.enums import RoleEnum, SourceTypeEnum
from app.models.source_document import SourceDocument
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.document import (
    ConfirmResponse,
    DocumentStatusResponse,
    DocumentUploadResponse,
    DocumentVerificationResponse,
    ReasonCodeResponse,
    ReviewRequest,
    ReviewResponse,
    TransactionListResponse,
    TransactionResponse,
)
from app.services.document_service import CorrectionInput, DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])

_READ_CHUNK_BYTES = 1024 * 1024
_DEFAULT_TRANSACTIONS_LIMIT = 100
_MAX_TRANSACTIONS_LIMIT = 500


def _to_status_response(document: SourceDocument) -> DocumentStatusResponse:
    return DocumentStatusResponse(
        document_id=document.id,
        status=document.status,
        file_name=document.file_name,
        mime_type=document.mime_type,
        source_type=document.source_type,
        page_count=document.page_count,
        uploaded_at=document.uploaded_at,
    )


async def _read_bounded(file: UploadFile, max_bytes: int) -> bytes:
    """Stops reading shortly past `max_bytes` so an oversized upload never
    fully buffers in memory (FR-3 AC5, NFR "upload floods / OCR bombs")."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_READ_CHUNK_BYTES)
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            break
    return b"".join(chunks)


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit("upload"))],
)
async def upload_document(
    file: UploadFile = File(...),
    source_type: SourceTypeEnum = Form(...),
    financial_account_id: uuid.UUID | None = Form(None),
    pdf_password: str | None = Form(None),
    current_user: User = Depends(require(RoleEnum.USER)),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    settings = get_settings()
    data = await _read_bounded(file, settings.max_upload_mb * 1024 * 1024 + 1)

    document, created = DocumentService(db).upload(
        user=current_user,
        data=data,
        file_name=file.filename or "upload",
        declared_content_type=file.content_type or "application/octet-stream",
        source_type=source_type,
        password=pdf_password,
        financial_account_id=financial_account_id,
    )

    return DocumentUploadResponse(
        document_id=document.id,
        status=document.status,
        poll=f"/api/v1/documents/{document.id}/status",
        duplicate=not created,
    )


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    dependencies=[Depends(rate_limit("general"))],
)
def get_document_status(
    document_id: uuid.UUID,
    current_user: User = Depends(require(RoleEnum.USER)),
    db: Session = Depends(get_db),
) -> DocumentStatusResponse:
    document = DocumentService(db).get_status(current_user, document_id)
    return _to_status_response(document)


def _to_verification_response(
    document_id: uuid.UUID, result: DocumentVerificationResult
) -> DocumentVerificationResponse:
    flags = result.flags_json or {}
    reason_codes = [
        ReasonCodeResponse(code=r["code"], description=r["description"])
        for r in flags.get("reason_codes", [])
    ]
    return DocumentVerificationResponse(
        document_id=document_id,
        data_confidence_score=result.data_confidence_score,
        band=result.confidence_band,
        provenance_score=result.provenance_score,
        consistency_score=result.consistency_score,
        metadata_score=result.metadata_score,
        ocr_score=result.ocr_score,
        visual_score=result.visual_score,
        completeness_score=result.completeness_score,
        ownership_score=result.ownership_score,
        reason_codes=reason_codes,
        recommendation=flags.get("recommendation"),
        verified_at=result.verified_at,
    )


def _to_transaction_response(transaction: Transaction) -> TransactionResponse:
    return TransactionResponse(
        transaction_id=transaction.id,
        transaction_date=transaction.transaction_date,
        transaction_time=transaction.transaction_time,
        amount=transaction.amount,
        direction=transaction.direction,
        balance_after=transaction.balance_after,
        raw_description=transaction.raw_description,
        category=transaction.category,
        transaction_context=transaction.transaction_context,
        is_internal_transfer=transaction.is_internal_transfer,
        is_recurring=transaction.is_recurring,
        extraction_confidence=transaction.extraction_confidence,
    )


@router.get(
    "/{document_id}/verification",
    response_model=DocumentVerificationResponse,
    dependencies=[Depends(rate_limit("general"))],
)
def get_document_verification(
    document_id: uuid.UUID,
    current_user: User = Depends(require(RoleEnum.USER)),
    db: Session = Depends(get_db),
) -> DocumentVerificationResponse:
    result = DocumentService(db).get_verification(current_user, document_id)
    return _to_verification_response(document_id, result)


@router.get(
    "/{document_id}/transactions",
    response_model=TransactionListResponse,
    dependencies=[Depends(rate_limit("general"))],
)
def get_document_transactions(
    document_id: uuid.UUID,
    limit: int = Query(default=_DEFAULT_TRANSACTIONS_LIMIT, ge=1, le=_MAX_TRANSACTIONS_LIMIT),
    cursor: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(require(RoleEnum.USER)),
    db: Session = Depends(get_db),
) -> TransactionListResponse:
    transactions = DocumentService(db).list_transactions(
        current_user, document_id, limit=limit, cursor=cursor
    )
    next_cursor = transactions[-1].id if len(transactions) == limit else None
    return TransactionListResponse(
        items=[_to_transaction_response(t) for t in transactions], next_cursor=next_cursor
    )


@router.post(
    "/{document_id}/review",
    response_model=ReviewResponse,
    dependencies=[Depends(rate_limit("general"))],
)
def review_document(
    document_id: uuid.UUID,
    body: ReviewRequest,
    current_user: User = Depends(require(RoleEnum.USER)),
    db: Session = Depends(get_db),
) -> ReviewResponse:
    corrections = [
        CorrectionInput(
            transaction_id=c.transaction_id, correction_type=c.correction_type.value, note=c.note
        )
        for c in body.corrections
    ]
    count = DocumentService(db).review(current_user, document_id, corrections)
    return ReviewResponse(document_id=document_id, corrections_recorded=count)


@router.post(
    "/{document_id}/confirm",
    response_model=ConfirmResponse,
    dependencies=[Depends(rate_limit("general"))],
)
def confirm_document(
    document_id: uuid.UUID,
    current_user: User = Depends(require(RoleEnum.USER)),
    db: Session = Depends(get_db),
) -> ConfirmResponse:
    document = DocumentService(db).confirm(current_user, document_id)
    return ConfirmResponse(document_id=document_id, status=document.status)
