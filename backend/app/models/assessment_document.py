"""Exact many-to-many document lineage for an assessment (PLAN §11.3
`assessment_documents`; FR-18). `processing_run_id`/`verification_result_id`
pin the exact immutable evidence used, so a later re-extraction or
re-verification of the same document never silently changes a historical
assessment (PLAN §6.4/NFR-17)."""

import uuid

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import InclusionEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class AssessmentDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_documents"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "source_document_id",
            "processing_run_id",
            name="uq_assessment_documents_assessment_document_run",
        ),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="RESTRICT"), nullable=False
    )
    source_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False
    )
    processing_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_processing_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    verification_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_verification_results.id", ondelete="RESTRICT"),
        nullable=False,
    )
    inclusion_status: Mapped[InclusionEnum] = mapped_column(
        sa_enum(InclusionEnum, "inclusion_enum"), nullable=False, default=InclusionEnum.INCLUDED
    )
    exclusion_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
