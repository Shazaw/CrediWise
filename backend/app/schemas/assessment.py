"""Assessment DTOs (PLAN §12.2 `/assessments`; §12.3 representative payloads;
FR-8, FR-9, FR-12). Sprint 4, T4.6.
"""

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import (
    AssessmentStatusEnum,
    BandEnum,
    CashEventEnum,
    CoverageEnum,
    DirEnum,
    FreqEnum,
    IncomeSourceEnum,
    RiskBandEnum,
)
from app.schemas.document import ReasonCodeResponse

#: PLAN §2.3/§14.6 positioning guardrail, enforced verbatim everywhere an
#: assessment result is surfaced (PLAN §12.3 dashboard payload example).
POSITIONING_NOTICE = (
    "Estimated financial-risk, affordability, and credit-readiness assessment "
    "— not an official credit score."
)


class CreateAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    financing_need_id: uuid.UUID
    source_document_ids: list[uuid.UUID]


class AssessmentCreateResponse(BaseModel):
    assessment_id: uuid.UUID
    status: AssessmentStatusEnum
    poll: str


class AssessmentResponse(BaseModel):
    assessment_id: uuid.UUID
    status: AssessmentStatusEnum
    data_confidence_score: Decimal | None
    data_confidence_band: BandEnum | None
    indicative_risk_band: RiskBandEnum | None
    model_confidence: BandEnum | None
    shock_resilience_score: Decimal | None
    safe_loan_amount: int | None
    maximum_safe_instalment: int | None
    recommended_tenor_months: int | None
    recommended_due_date_start: int | None
    recommended_due_date_end: int | None
    recommended_frequency: FreqEnum | None


class MonthlySnapshotResponse(BaseModel):
    year_month: date
    personal_income: int
    business_income: int
    essential_expenses: int
    discretionary_expenses: int
    business_expenses: int
    debt_service: int
    opening_balance: int
    minimum_balance: int
    closing_balance: int
    net_cash_flow: int


class IncomeSourceResponse(BaseModel):
    source_name: str
    source_type: IncomeSourceEnum
    average_amount: int
    frequency: FreqEnum
    volatility: Decimal
    concentration_ratio: Decimal
    dominant_arrival_day: int | None
    confidence: Decimal


class CashFlowEventResponse(BaseModel):
    expected_day_of_month: int | None
    amount: int
    direction: DirEnum
    event_type: CashEventEnum
    confidence: Decimal


class TwinResponse(BaseModel):
    assessment_id: uuid.UUID
    average_income: int
    median_income: int
    income_volatility: Decimal
    essential_expenses: int
    discretionary_expenses: int
    existing_debt: int
    average_free_cash_flow: int
    minimum_balance: int
    positive_cash_flow_ratio: Decimal
    weakest_month_cash_flow: int
    savings_buffer: int
    months_covered: int
    coverage_flag: CoverageEnum
    monthly_snapshots: list[MonthlySnapshotResponse]
    income_sources: list[IncomeSourceResponse]
    cash_flow_events: list[CashFlowEventResponse]


class RecommendationResponse(BaseModel):
    assessment_id: uuid.UUID
    safe_loan_amount: int | None
    maximum_safe_instalment: int | None
    recommended_tenor_months: int | None
    recommended_due_date_start: int | None
    recommended_due_date_end: int | None
    recommended_frequency: FreqEnum | None
    reason_codes: list[ReasonCodeResponse]


class DataConfidenceSummary(BaseModel):
    score: Decimal | None
    band: BandEnum | None
    reasons: list[str]


class RiskBandSummary(BaseModel):
    band: RiskBandEnum | None
    model_confidence: BandEnum | None
    positive: list[str]
    risk: list[str]


class SafeBorrowingSummary(BaseModel):
    amount: int | None
    max_instalment: int | None
    tenor_months: int | None
    due_date_window: tuple[int, int] | None
    frequency: FreqEnum | None


class TwinSummary(BaseModel):
    median_income: int
    essential_expenses: int
    existing_debt: int
    average_free_cash_flow: int
    weakest_month_cash_flow: int


class DashboardResponse(BaseModel):
    assessment_id: uuid.UUID
    status: AssessmentStatusEnum
    positioning_notice: str = POSITIONING_NOTICE
    data_confidence: DataConfidenceSummary
    risk_band: RiskBandSummary
    safe_borrowing: SafeBorrowingSummary
    twin: TwinSummary | None


class LineageResponse(BaseModel):
    assessment_id: uuid.UUID
    snapshot_hash: str
    document_ids: list[uuid.UUID]
    transaction_ids: list[uuid.UUID]
    parser_versions: dict[str, str]
    categorizer_version: str
    engine_config_hash: str
