"""Explainability records for an assessment (PLAN §11.3
`assessment_reason_codes`; FR-8/FR-12 — every score ships with >=3
human-readable reason codes)."""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ReasonTypeEnum, SeverityEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class AssessmentReasonCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_reason_codes"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="RESTRICT"), nullable=False
    )
    reason_type: Mapped[ReasonTypeEnum] = mapped_column(
        sa_enum(ReasonTypeEnum, "reason_type_enum"), nullable=False
    )
    reason_code: Mapped[str] = mapped_column(Text(), nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    severity: Mapped[SeverityEnum] = mapped_column(
        sa_enum(SeverityEnum, "severity_enum"), nullable=False
    )
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, default=dict)
