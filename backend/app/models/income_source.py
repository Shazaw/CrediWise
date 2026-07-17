"""Derived source-level income behaviour (PLAN §11.3 `income_sources`;
FR-7 AC3)."""

import uuid
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import FreqEnum, IncomeSourceEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum

_RATIO = Numeric(6, 4)


class IncomeSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "income_sources"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="RESTRICT"), nullable=False
    )
    source_name: Mapped[str] = mapped_column(Text(), nullable=False)
    source_type: Mapped[IncomeSourceEnum] = mapped_column(
        sa_enum(IncomeSourceEnum, "income_source_enum"), nullable=False
    )
    average_amount: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    frequency: Mapped[FreqEnum] = mapped_column(sa_enum(FreqEnum, "freq_enum"), nullable=False)
    volatility: Mapped[Decimal] = mapped_column(_RATIO, nullable=False)
    concentration_ratio: Mapped[Decimal] = mapped_column(_RATIO, nullable=False)
    dominant_arrival_day: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    confidence: Mapped[Decimal] = mapped_column(_RATIO, nullable=False)
