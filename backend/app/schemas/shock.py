"""Shock simulation DTOs (PLAN §12.2 `/assessments/{id}/simulate|shocks`;
§12.3 representative payload; FR-10). Sprint 5, T5.2.
"""

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import AffordEnum, ShockResilienceBandEnum, ShockTypeEnum


class SimulateShockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #: Percentage (0-100), not a fraction -- matches PLAN §12.3's
    #: `{"income_drop_pct": 20, ...}` example literally.
    income_drop_pct: Decimal | None = None
    emergency_expense: int | None = None
    proposed_instalment: int | None = None


class ShockScenarioResponse(BaseModel):
    scenario_type: ShockTypeEnum
    parameters: dict[str, object]
    projected_cash_flow: int
    minimum_projected_balance: int
    deficit_amount: int
    affordability_status: AffordEnum
    resilience_score_contribution: Decimal


class ShockResultResponse(BaseModel):
    assessment_id: uuid.UUID
    resilience_score: Decimal | None
    band: ShockResilienceBandEnum | None
    scenarios: list[ShockScenarioResponse]
