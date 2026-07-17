"""1:1 Cash-Flow Digital Twin per assessment (PLAN §11.3 `financial_profiles`;
FR-7, §15.1 `CashFlowTwinEngine` output)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import CoverageEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum

_RATIO = Numeric(6, 4)


class FinancialProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "financial_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    average_income: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    median_income: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    income_volatility: Mapped[Decimal] = mapped_column(_RATIO, nullable=False)
    essential_expenses: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    discretionary_expenses: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    existing_debt: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    average_free_cash_flow: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    minimum_balance: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    positive_cash_flow_ratio: Mapped[Decimal] = mapped_column(_RATIO, nullable=False)
    weakest_month_cash_flow: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    savings_buffer: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    months_covered: Mapped[int] = mapped_column(Integer(), nullable=False)
    coverage_flag: Mapped[CoverageEnum] = mapped_column(
        sa_enum(CoverageEnum, "coverage_enum"), nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(nullable=False)
