"""Resumability and observability record per pipeline stage attempt (PLAN
§11.3 `pipeline_stage_runs`; NFR-3).

Scoped to `source_document_id` for Sprint 3 (`EXTRACTION`/`VERIFICATION`
stages, PLAN §11.3's `pipeline_stage_enum` gap-fill in `app/models/enums.py`).
Sprint 4/migration `0007` adds `assessment_id` (PLAN §11.4's expand pattern —
a Postgres FK couldn't target `assessments` before this migration created
it): `NORMALIZATION` runs stay scoped to `source_document_id` (one row's own
transactions); the new `ANALYSIS` stage is scoped to `assessment_id` (Twin/
Risk/SafeBorrowing run once per assessment, not per document).
"""

import uuid
from datetime import datetime

from sqlalchemy import CHAR, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import PipelineStageEnum, StageStatusEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class PipelineStageRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pipeline_stage_runs"

    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=True
    )
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="RESTRICT"), nullable=True
    )
    stage: Mapped[PipelineStageEnum] = mapped_column(
        sa_enum(PipelineStageEnum, "pipeline_stage_enum"), nullable=False
    )
    status: Mapped[StageStatusEnum] = mapped_column(
        sa_enum(StageStatusEnum, "stage_status_enum"),
        nullable=False,
        default=StageStatusEnum.RUNNING,
    )
    attempt_number: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    input_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    output_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    worker_version: Mapped[str] = mapped_column(Text(), nullable=False)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text(), nullable=True)
    sanitized_error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
