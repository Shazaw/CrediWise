"""Exact many-to-many transaction lineage for an assessment (PLAN §11.3
`assessment_transactions`; FR-18). A `transactions` row is a source fact
shared across assessments (§11.3 `transactions` note); this junction pins
exactly which rows a specific assessment's engines consumed."""

import uuid

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import InclusionEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class AssessmentTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_transactions"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "transaction_id",
            name="uq_assessment_transactions_assessment_transaction",
        ),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="RESTRICT"), nullable=False
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False
    )
    inclusion_status: Mapped[InclusionEnum] = mapped_column(
        sa_enum(InclusionEnum, "inclusion_enum"), nullable=False, default=InclusionEnum.INCLUDED
    )
    exclusion_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
