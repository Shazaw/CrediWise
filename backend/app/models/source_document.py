"""An uploaded financial record (PLAN §11.3 `source_documents`; FR-3).

`file_hash` + the partial unique index on `(user_id, file_hash)` (created by
the migration) is the dedup mechanism (FR-3 AC3): a re-upload of the same
bytes by the same user must resolve to this existing row without a second
object-storage write or a second row (CLAUDE.md §8 named outcome).
"""

import uuid
from datetime import date, datetime

from sqlalchemy import CHAR, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import DocStatusEnum, SourceTypeEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class SourceDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_documents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    financial_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_accounts.id", ondelete="RESTRICT"), nullable=True
    )
    file_name: Mapped[str] = mapped_column(Text(), nullable=False)
    file_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(Text(), nullable=False)
    source_type: Mapped[SourceTypeEnum] = mapped_column(
        sa_enum(SourceTypeEnum, "source_type_enum"), nullable=False
    )
    storage_path: Mapped[str | None] = mapped_column(Text(), nullable=True)
    statement_start_date: Mapped[date | None] = mapped_column(nullable=True)
    statement_end_date: Mapped[date | None] = mapped_column(nullable=True)
    status: Mapped[DocStatusEnum] = mapped_column(
        sa_enum(DocStatusEnum, "doc_status_enum"), nullable=False, default=DocStatusEnum.UPLOADED
    )
    page_count: Mapped[int | None] = mapped_column(nullable=True)
    uploaded_at: Mapped[datetime | None] = mapped_column(nullable=True)
