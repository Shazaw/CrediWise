"""Offer DTOs (PLAN §12.2 `/assessments/{id}/offers`, `/offers/{id}/safety`;
FR-11, §5.7 Loan Mathematics Contract, §5.9 Safe Offer Score). Sprint 5,
T5.4.
"""

import uuid
from decimal import Decimal

from pydantic import BaseModel

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
    effective_annual_rate: Decimal | None
    interest_amount: int
    upfront_fee: int
    financed_fee: int
    service_fee: int
    admin_fee: int
    total_repayment: int
    late_penalty_terms: dict[str, object] | None
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
    explanation: str


class OffersListResponse(BaseModel):
    assessment_id: uuid.UUID
    offers: list[OfferResponse]
