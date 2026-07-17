"""Expected temporal liquidity events used by simulations (PLAN §11.3
`cash_flow_events`; FR-7 AC2). Populated by `CashFlowTwinEngine` in Sprint 4;
consumed by Sprint 5's `ShockEngine` for due-date/delayed-income analysis."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import CashEventEnum, DirEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class CashFlowEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cash_flow_events"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="RESTRICT"), nullable=False
    )
    event_date: Mapped[date | None] = mapped_column(nullable=True)
    expected_day_of_month: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    direction: Mapped[DirEnum] = mapped_column(sa_enum(DirEnum, "dir_enum"), nullable=False)
    event_type: Mapped[CashEventEnum] = mapped_column(
        sa_enum(CashEventEnum, "cash_event_enum"), nullable=False
    )
    recurring_series_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recurring_series.id", ondelete="RESTRICT"), nullable=True
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
