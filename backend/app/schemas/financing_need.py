"""Financing-need DTOs (PLAN §12.2 `/financing-needs`; FR-2)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PurposeEnum, UrgencyEnum


class CreateFinancingNeedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requested_amount: int = Field(gt=0, le=1_000_000_000)
    purpose: PurposeEnum
    preferred_tenor_months: int = Field(ge=1, le=36)
    urgency: UrgencyEnum
    notes: str | None = None


class FinancingNeedResponse(BaseModel):
    financing_need_id: uuid.UUID
    requested_amount: int
    purpose: PurposeEnum
    preferred_tenor_months: int
    urgency: UrgencyEnum
    notes: str | None
    created_at: datetime


class FinancingNeedListResponse(BaseModel):
    items: list[FinancingNeedResponse]
