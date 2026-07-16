"""Append-only parser/OCR execution record (PLAN §11.3 `document_processing_runs`; FR-4 AC3).

One row per extraction attempt against a `source_document`. `input_hash` is
the hash of the bytes fed to the parser (the document's own `file_hash`);
`output_hash` is a hash of the resulting normalized rows, stamped once the
run completes — both feed the reproducibility contract (PLAN §15.4/NFR-17).
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CHAR, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ProcessingStatusEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class DocumentProcessingRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_processing_runs"

    source_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False
    )
    parser_name: Mapped[str] = mapped_column(Text(), nullable=False)
    parser_version: Mapped[str] = mapped_column(Text(), nullable=False)
    format_name: Mapped[str] = mapped_column(Text(), nullable=False)
    format_detection_confidence: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    status: Mapped[ProcessingStatusEnum] = mapped_column(
        sa_enum(ProcessingStatusEnum, "processing_status_enum"),
        nullable=False,
        default=ProcessingStatusEnum.RUNNING,
    )
    input_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    output_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    supersedes_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_processing_runs.id", ondelete="RESTRICT"),
        nullable=True,
    )
