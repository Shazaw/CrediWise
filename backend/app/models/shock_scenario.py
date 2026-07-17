"""One row per shock simulation (PLAN §11.3 `shock_scenarios`; FR-10,
§15.1 `ShockEngine` output).

`minimum_projected_balance` is a Sprint 5 gap-fill column (§24.11): FR-10
AC1 requires exposing "monthly and minimum-temporal projected balance" but
§11.3's compact table listing only names `projected_cash_flow`/`deficit_amount`
-- both are needed to reconstruct the SURVIVABLE/STRAINED/DEFICIT
classification without recomputing it from `deficit_amount` alone.
"""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Boolean, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import AffordEnum, ShockTypeEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class ShockScenario(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shock_scenarios"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="RESTRICT"), nullable=False
    )
    scenario_type: Mapped[ShockTypeEnum] = mapped_column(
        sa_enum(ShockTypeEnum, "shock_type_enum"), nullable=False
    )
    scenario_parameters_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, default=dict
    )
    projected_cash_flow: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    minimum_projected_balance: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    deficit_amount: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    affordability_status: Mapped[AffordEnum] = mapped_column(
        sa_enum(AffordEnum, "afford_enum"), nullable=False
    )
    resilience_score_contribution: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    projection_points_json: Mapped[list[Any] | None] = mapped_column(JSONB(), nullable=True)
    required_buffer_breached: Mapped[bool | None] = mapped_column(Boolean(), nullable=True)
