"""One row per assessment month (PLAN §11.3 `monthly_cash_flow_snapshots`;
FR-7 AC1)."""

import uuid
from datetime import date

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MonthlyCashFlowSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "monthly_cash_flow_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id", "year_month", name="uq_monthly_cash_flow_snapshots_assessment_month"
        ),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="RESTRICT"), nullable=False
    )
    year_month: Mapped[date] = mapped_column(nullable=False)
    personal_income: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    business_income: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    essential_expenses: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    discretionary_expenses: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    business_expenses: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    debt_service: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    opening_balance: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    minimum_balance: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    closing_balance: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    net_cash_flow: Mapped[int] = mapped_column(BigInteger(), nullable=False)
