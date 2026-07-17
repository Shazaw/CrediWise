"""1:1 Safe Offer Score per offer (PLAN §11.3 `offer_assessments`; FR-11,
§5.9, §15.1 `OfferEngine` output)."""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import AffordEnum, BandEnum, OfferRatingEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class OfferAssessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "offer_assessments"

    lender_offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lender_offers.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    safe_offer_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    affordability_status: Mapped[AffordEnum] = mapped_column(
        sa_enum(AffordEnum, "afford_enum"), nullable=False
    )
    shock_resilience_status: Mapped[BandEnum] = mapped_column(
        sa_enum(BandEnum, "band_enum"), nullable=False
    )
    total_cost_status: Mapped[OfferRatingEnum] = mapped_column(
        sa_enum(OfferRatingEnum, "offer_rating_enum"), nullable=False
    )
    timing_status: Mapped[OfferRatingEnum] = mapped_column(
        sa_enum(OfferRatingEnum, "offer_rating_enum"), nullable=False
    )
    warning_flags_json: Mapped[list[Any]] = mapped_column(JSONB(), nullable=False, default=list)
    explanation: Mapped[str] = mapped_column(Text(), nullable=False)
    rank: Mapped[int] = mapped_column(Integer(), nullable=False)
