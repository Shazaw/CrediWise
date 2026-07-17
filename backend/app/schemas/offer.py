"""Offer DTOs (PLAN §12.2 `/assessments/{id}/offers`, `/offers/{id}/safety`;
FR-11, §5.7 Loan Mathematics Contract, §5.9 Safe Offer Score). Sprint 5,
T5.4.
"""

import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AffordEnum,
    AmortizationEnum,
    BandEnum,
    FreqEnum,
    OfferRatingEnum,
    OfferSafetyBandEnum,
    OfferSourceEnum,
    RegStatusEnum,
)
from app.schemas.document import ReasonCodeResponse


class LenderResponse(BaseModel):
    lender_id: uuid.UUID
    name: str
    regulatory_status: RegStatusEnum
    logo_url: str | None


class PaymentScheduleEntryResponse(BaseModel):
    period: int
    payment_amount: int
    principal_component: int
    interest_component: int
    remaining_balance: int


class LatePenaltyTermsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger_days: int = Field(ge=0)
    rate: Decimal | None
    amount: int | None
    basis: Literal["OVERDUE_INSTALMENT_PER_DAY", "OVERDUE_INSTALMENT_PER_MONTH", "FIXED"]


class EssentialExpenseCoverageResponse(BaseModel):
    amount: int
    ratio: Decimal


class OfferResponse(BaseModel):
    offer_id: uuid.UUID
    lender: LenderResponse
    offer_source: OfferSourceEnum
    principal_amount: int
    net_disbursed_amount: int
    instalment_amount: int
    tenor_months: int
    amortization_method: AmortizationEnum
    nominal_rate: Decimal | None
    nominal_rate_basis: Literal["ANNUAL_NOMINAL"]
    effective_annual_rate: Decimal | None
    interest_amount: int
    upfront_fee: int
    financed_fee: int
    service_fee: int
    admin_fee: int
    total_repayment: int
    late_penalty_terms: LatePenaltyTermsResponse | None
    payment_schedule: list[PaymentScheduleEntryResponse]
    due_date: int
    frequency: FreqEnum
    safe_offer_score: Decimal
    safety_band: OfferSafetyBandEnum
    rank: int
    affordability_status: AffordEnum
    shock_resilience_status: BandEnum
    total_cost_status: OfferRatingEnum
    timing_status: OfferRatingEnum
    warning_flags: list[str]
    refinancing_dependency: bool
    remaining_essential_expense_coverage: EssentialExpenseCoverageResponse
    reason_codes: list[ReasonCodeResponse]
    explanation: str
    model_version: str
    config_hash: str
    simulation_notice: (
        Literal["SIMULATED offer for comparison only; not a real provider endorsement."] | None
    )


class OffersListResponse(BaseModel):
    assessment_id: uuid.UUID
    offers: list[OfferResponse]
