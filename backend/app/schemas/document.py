"""Document upload/status DTOs (PLAN §12.2 `/documents`; FR-3)."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import DocStatusEnum, SourceTypeEnum


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    status: DocStatusEnum
    poll: str
    duplicate: bool


class DocumentStatusResponse(BaseModel):
    document_id: uuid.UUID
    status: DocStatusEnum
    file_name: str
    mime_type: str
    source_type: SourceTypeEnum
    page_count: int | None
    uploaded_at: datetime | None
