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

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import require
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.enums import RoleEnum, SourceTypeEnum
from app.models.source_document import SourceDocument
from app.models.user import User
from app.schemas.document import DocumentStatusResponse, DocumentUploadResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])

_READ_CHUNK_BYTES = 1024 * 1024


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
