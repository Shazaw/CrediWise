"""A stated borrowing need (PLAN §11.3 `financing_needs`; FR-2).

Amount/tenor bounds are enforced at the API boundary (Pydantic schema) and
mirrored here as CHECK constraints (migration `0007`) per PLAN §11.1 —
`requested_amount <= 1_000_000_000`, `preferred_tenor_months` in `[1, 36]`.
"""

import uuid

from sqlalchemy import BigInteger, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import PurposeEnum, UrgencyEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class FinancingNeed(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "financing_needs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    requested_amount: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    purpose: Mapped[PurposeEnum] = mapped_column(
        sa_enum(PurposeEnum, "purpose_enum"), nullable=False
    )
    preferred_tenor_months: Mapped[int] = mapped_column(Integer(), nullable=False)
    urgency: Mapped[UrgencyEnum] = mapped_column(
        sa_enum(UrgencyEnum, "urgency_enum"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
