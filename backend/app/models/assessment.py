"""The central assessment aggregate (PLAN §11.3 `assessments`; FR-8/FR-9).

Denormalizes the headline outputs of `RiskEngine`/`SafeBorrowingEngine`
directly onto this row (score/band/amount columns) so `GET /assessments/{id}`
and the dashboard composite read (§7.11) don't have to join every engine's
detail table for the common case — the detail tables
(`financial_profiles`, `assessment_reason_codes`, ...) still hold the full
breakdown. `shock_resilience_score` stays `NULL` until Sprint 5's
`ShockEngine` ships (PLAN §25 Sprint 5) — not populated by this migration's
service code.
"""

import uuid
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import AssessmentStatusEnum, BandEnum, FreqEnum, RiskBandEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum

_SCORE = Numeric(6, 2)


class Assessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    financing_need_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financing_needs.id", ondelete="RESTRICT"), nullable=False
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False
    )
    data_confidence_score: Mapped[Decimal | None] = mapped_column(_SCORE, nullable=True)
    indicative_risk_band: Mapped[RiskBandEnum | None] = mapped_column(
        sa_enum(RiskBandEnum, "risk_band_enum"), nullable=True
    )
    model_confidence: Mapped[BandEnum | None] = mapped_column(
        sa_enum(BandEnum, "band_enum"), nullable=True
    )
    shock_resilience_score: Mapped[Decimal | None] = mapped_column(_SCORE, nullable=True)
    safe_loan_amount: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    maximum_safe_instalment: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    recommended_tenor_months: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    recommended_due_date_start: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    recommended_due_date_end: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    recommended_frequency: Mapped[FreqEnum | None] = mapped_column(
        sa_enum(FreqEnum, "freq_enum"), nullable=True
    )
    status: Mapped[AssessmentStatusEnum] = mapped_column(
        sa_enum(AssessmentStatusEnum, "assessment_status_enum"),
        nullable=False,
        default=AssessmentStatusEnum.PENDING,
    )
