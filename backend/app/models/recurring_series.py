"""Recurring income/expense/debt patterns (PLAN §11.3 `recurring_series`;
FR-6 AC3). Scoped to `(user_id, financial_account_id)`, not an assessment —
detected once per account by `NormalizationEngine` and reused across any
assessment that later includes that account's transactions."""

import uuid
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import RecurringTypeEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum

_RATIO = Numeric(6, 4)


class RecurringSeries(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recurring_series"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    financial_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    series_type: Mapped[RecurringTypeEnum] = mapped_column(
        sa_enum(RecurringTypeEnum, "recurring_type_enum"), nullable=False
    )
    normalized_counterparty: Mapped[str] = mapped_column(Text(), nullable=False)
    median_amount: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    expected_interval_days: Mapped[int] = mapped_column(Integer(), nullable=False)
    expected_day_of_month: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    regularity_score: Mapped[Decimal] = mapped_column(_RATIO, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(_RATIO, nullable=False)
