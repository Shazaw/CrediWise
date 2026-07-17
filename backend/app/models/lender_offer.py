"""An offer attached to an assessment (PLAN §11.3 `lender_offers`; FR-11
AC3, §5.7 Loan Mathematics Contract). `late_penalty_terms_json` is
nullable — PLAN §11.3 doesn't mark it `NOT NULL`, and FR-11 EC's "offer
missing fee disclosure" path relies on it being genuinely absent, not an
empty object (`app/engines/offer.py`'s `late_penalty_terms_present` signal).
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import AmortizationEnum, FreqEnum, OfferSourceEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum

_RATE = Numeric(6, 4)


class LenderOffer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lender_offers"
    __table_args__ = (
        Index(
            "uq_lender_offers_canonical_simulated_set",
            "assessment_id",
            "canonical_template_key",
            unique=True,
            postgresql_where=text(
                "deleted_at IS NULL AND offer_source = 'SIMULATED' "
                "AND canonical_template_key IS NOT NULL"
            ),
        ),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="RESTRICT"), nullable=False
    )
    lender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lenders.id", ondelete="RESTRICT"), nullable=False
    )
    offer_source: Mapped[OfferSourceEnum] = mapped_column(
        sa_enum(OfferSourceEnum, "offer_source_enum"), nullable=False
    )
    canonical_template_key: Mapped[str | None] = mapped_column(Text(), nullable=True)
    principal_amount: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    net_disbursed_amount: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    instalment_amount: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    tenor_months: Mapped[int] = mapped_column(Integer(), nullable=False)
    amortization_method: Mapped[AmortizationEnum] = mapped_column(
        sa_enum(AmortizationEnum, "amortization_enum"), nullable=False
    )
    nominal_rate: Mapped[Decimal | None] = mapped_column(_RATE, nullable=True)
    effective_annual_rate: Mapped[Decimal | None] = mapped_column(_RATE, nullable=True)
    interest_amount: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    upfront_fee: Mapped[int] = mapped_column(BigInteger(), nullable=False, default=0)
    financed_fee: Mapped[int] = mapped_column(BigInteger(), nullable=False, default=0)
    service_fee: Mapped[int] = mapped_column(BigInteger(), nullable=False, default=0)
    admin_fee: Mapped[int] = mapped_column(BigInteger(), nullable=False, default=0)
    total_repayment: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    late_penalty_terms_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    payment_schedule_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, default=dict
    )
    due_date: Mapped[int] = mapped_column(Integer(), nullable=False)
    frequency: Mapped[FreqEnum] = mapped_column(sa_enum(FreqEnum, "freq_enum"), nullable=False)
    received_at: Mapped[datetime] = mapped_column(nullable=False)
