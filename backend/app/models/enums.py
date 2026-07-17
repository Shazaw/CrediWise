"""Shared enum types for ORM models.

`RoleEnum` values are fixed by PLAN Appendix A. `IdentityStatusEnum`,
`EmploymentTypeEnum`, `DocumentTypeEnum`, `VerificationStatusEnum`,
`ActorTypeEnum`, and `ModelStatusEnum` are referenced by PLAN §11.3's table
definitions but their member sets are not enumerated in Appendix A — the
values below are the Sprint 1 implementation choice (PLAN §24.11: additive,
non-architectural gap-filling, documented in PLAN.md in the same PR).

`AccountTypeEnum`, `ConnectionTypeEnum`, and `SourceTypeEnum` member sets are
fixed by PLAN Appendix A. `OwnershipEnum` and `ConnectionStatusEnum` are
referenced by PLAN §11.3's `financial_accounts` definition but their member
sets are not enumerated in Appendix A; `DocStatusEnum`'s Appendix A list is
missing two states (`VALIDATION_FAILED`, `DUPLICATE_REUSED`) that PLAN §8.2's
state diagram requires. All of these are the Sprint 2 implementation choice
(PLAN §24.11 gap-filling, documented in PLAN.md in the same PR — see §11.3).

`CategoryEnum`, `TransactionContextEnum`, and `BandEnum` member sets are fixed
by PLAN Appendix A. `ProcessingStatusEnum`, `PipelineStageEnum`,
`StageStatusEnum`, and `DirEnum` are referenced by PLAN §11.3's table
definitions but their member sets are not enumerated in Appendix A — the
Sprint 3 implementation choice (PLAN §24.11 gap-filling, documented in
PLAN.md in the same PR — see §11.3).

`PurposeEnum`, `AssessmentStatusEnum`, `RiskBandEnum`, and `FreqEnum` member
sets are fixed by PLAN Appendix A. `UrgencyEnum`, `IncomeSourceEnum`,
`RecurringTypeEnum`, `CashEventEnum`, `CoverageEnum`, `InclusionEnum`, and
`SeverityEnum` are referenced by PLAN §11.3's table definitions but their
member sets are not enumerated in Appendix A; `ReasonTypeEnum`'s set is
given inline in §11.3 prose rather than in Appendix A. `PipelineStageEnum`
gains `NORMALIZATION`/`ANALYSIS` members. All of these are the Sprint 4
implementation choice (PLAN §24.11 gap-filling, documented in PLAN.md in the
same PR — see §11.3).

`ShockTypeEnum`, `AffordEnum`, `OfferSourceEnum`, `AmortizationEnum`, and
`OfferRatingEnum` (`status_enum` in §11.3's `offer_assessments` row) are
referenced by PLAN §11.3's `shock_scenarios`/`lender_offers`/`offer_assessments`
table definitions but their member sets are not enumerated in Appendix A.
`ShockResilienceBandEnum` (§5.8: "STRONG >= 75, MODERATE 50-74, FRAGILE < 50")
and `OfferSafetyBandEnum` (§5.9: "SAFE >= 75, CAUTION 50-74, UNSAFE < 50") are
named only in §5.8/§5.9 prose, not as a table column — both are computed on
read from a stored `NUMERIC` score, the same pattern `band_from_score` already
uses for Data Confidence (`assessment_service.py`), so neither is a new DB
column. `RegStatusEnum` extends PLAN §11.3's documented two-member set
(`REGULATED, UNLISTED`) with a third, `SIMULATED_REGULATED_PROVIDER`, because
FR-11 AC5 explicitly requires that exact label for MVP seeded providers
("simulated providers use SIMULATED_REGULATED_PROVIDER, never an implied real
endorsement") — §11.3's compact list and FR-11 AC5 both bind this table, and
the AC's more specific requirement wins per §24.11's gap-filling process. All
of these are the Sprint 5 implementation choice (PLAN §24.11 gap-filling,
documented in PLAN.md in the same PR — see §11.3), except `PipelineStageEnum`
which is unchanged this sprint (Shock/Analysis remain the same `ANALYSIS`
stage — no new pipeline stage needed).
"""

from enum import StrEnum


class RoleEnum(StrEnum):
    USER = "USER"
    LENDER = "LENDER"
    REVIEWER = "REVIEWER"
    ADMIN = "ADMIN"


class IdentityStatusEnum(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class EmploymentTypeEnum(StrEnum):
    EMPLOYED = "EMPLOYED"
    SELF_EMPLOYED = "SELF_EMPLOYED"
    GIG_WORKER = "GIG_WORKER"
    BUSINESS_OWNER = "BUSINESS_OWNER"
    UNEMPLOYED = "UNEMPLOYED"
    OTHER = "OTHER"


class DocumentTypeEnum(StrEnum):
    KTP = "KTP"
    PASSPORT = "PASSPORT"
    OTHER = "OTHER"


class VerificationStatusEnum(StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class ActorTypeEnum(StrEnum):
    USER = "USER"
    LENDER = "LENDER"
    SYSTEM = "SYSTEM"
    ADMIN = "ADMIN"


class ModelStatusEnum(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class AccountTypeEnum(StrEnum):
    BANK = "BANK"
    EWALLET = "EWALLET"
    QRIS = "QRIS"
    MARKETPLACE = "MARKETPLACE"


class OwnershipEnum(StrEnum):
    """Gap-fill (PLAN §24.11): PLAN §11.3 only names the default, `DECLARED`.
    `VERIFIED` is reserved for a future ownership-verification step (e.g.
    micro-deposit/OTP) — not implemented in MVP.
    """

    DECLARED = "DECLARED"
    VERIFIED = "VERIFIED"


class ConnectionTypeEnum(StrEnum):
    UPLOAD = "UPLOAD"
    API = "API"


class ConnectionStatusEnum(StrEnum):
    """Gap-fill (PLAN §24.11): not enumerated in Appendix A. `UPLOAD`-type
    accounts (the only kind created in MVP) are always `ACTIVE`; `INACTIVE`
    and `ERROR` are reserved for the post-MVP `API` connection type (§16.2).
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"


class SourceTypeEnum(StrEnum):
    BANK_API = "BANK_API"
    SIGNED_STATEMENT = "SIGNED_STATEMENT"
    ORIGINAL_PDF = "ORIGINAL_PDF"
    EXPORTED_CSV = "EXPORTED_CSV"
    SCREENSHOT = "SCREENSHOT"
    PHOTO = "PHOTO"


class ProcessingStatusEnum(StrEnum):
    """Gap-fill (PLAN §24.11): `document_processing_runs.status` is named in
    §11.3 (`processing_status_enum`) but its member set isn't enumerated in
    Appendix A. Added Sprint 3/T3.2.
    """

    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class PipelineStageEnum(StrEnum):
    """Gap-fill (PLAN §24.11): `pipeline_stage_runs.stage` — scoped to the
    stages Sprint 3 actually records (`EXTRACTION`, `VERIFICATION`); later
    sprints extend this set in their own migration (expand pattern, §11.4)
    as `NormalizationEngine`/analysis engines land.

    Sprint 4/T4.1-T4.5 adds two members: `NORMALIZATION` is document-scoped
    (like `EXTRACTION`/`VERIFICATION` — one run per `source_document_id`,
    driven by `NormalizationEngine` categorizing that document's own
    transactions). `ANALYSIS` is assessment-scoped (one run per
    `assessment_id`, driven by the Twin/Risk/SafeBorrowing engines) — this
    is why migration `0007` adds `pipeline_stage_runs.assessment_id`
    (§11.3's `pipeline_stage_runs` note: "Sprint 4's migration adds it").
    """

    EXTRACTION = "EXTRACTION"
    VERIFICATION = "VERIFICATION"
    NORMALIZATION = "NORMALIZATION"
    ANALYSIS = "ANALYSIS"


class StageStatusEnum(StrEnum):
    """Gap-fill (PLAN §24.11): `pipeline_stage_runs.status`. Added Sprint 3/T3.2."""

    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class DirEnum(StrEnum):
    """`transactions.direction` — named inline in PLAN §11.3 (`dir_enum`
    (`CREDIT, DEBIT`)) but not listed in Appendix A. Added Sprint 3/T3.2.
    """

    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class CategoryEnum(StrEnum):
    """PLAN Appendix A `category_enum`."""

    INCOME = "INCOME"
    ESSENTIAL_EXPENSE = "ESSENTIAL_EXPENSE"
    FINANCIAL_OBLIGATION = "FINANCIAL_OBLIGATION"
    DISCRETIONARY = "DISCRETIONARY"
    SAVINGS_TRANSFER = "SAVINGS_TRANSFER"
    INTERNAL_TRANSFER = "INTERNAL_TRANSFER"
    UNKNOWN = "UNKNOWN"


class TransactionContextEnum(StrEnum):
    """PLAN Appendix A `transaction_context_enum` (FR-6 AC4)."""

    PERSONAL = "PERSONAL"
    BUSINESS = "BUSINESS"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class BandEnum(StrEnum):
    """PLAN Appendix A `band_enum` — used by `document_verification_results
    .confidence_band` (§5.2: `HIGH >= 80`, `MEDIUM 50-79`, `LOW < 50`)."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PurposeEnum(StrEnum):
    """PLAN Appendix A `purpose_enum` (`financing_needs.purpose`, FR-2 AC2)."""

    MEDICAL = "MEDICAL"
    EDUCATION = "EDUCATION"
    HOUSEHOLD_EMERGENCY = "HOUSEHOLD_EMERGENCY"
    PRODUCTIVE_BUSINESS = "PRODUCTIVE_BUSINESS"
    EQUIPMENT = "EQUIPMENT"
    WORKING_CAPITAL = "WORKING_CAPITAL"
    VEHICLE_DEVICE_REPAIR = "VEHICLE_DEVICE_REPAIR"


class UrgencyEnum(StrEnum):
    """Gap-fill (PLAN §24.11): `financing_needs.urgency` is named in §11.3
    but its member set isn't enumerated in Appendix A. Added Sprint 4/T4.5.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AssessmentStatusEnum(StrEnum):
    """PLAN Appendix A `assessment_status_enum`."""

    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class RiskBandEnum(StrEnum):
    """PLAN Appendix A `risk_band_enum` (§5.3)."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class FreqEnum(StrEnum):
    """PLAN Appendix A `freq_enum`."""

    MONTHLY = "MONTHLY"
    BIWEEKLY = "BIWEEKLY"
    WEEKLY = "WEEKLY"


class IncomeSourceEnum(StrEnum):
    """Gap-fill (PLAN §24.11): `income_sources.source_type` is named in
    §11.3 but its member set isn't enumerated in Appendix A. Added
    Sprint 4/T4.2, mirrors the UMKM/gig-worker income categories FR-6 AC4
    names for `transaction_context`/category enrichment.
    """

    SALARY = "SALARY"
    BUSINESS_REVENUE = "BUSINESS_REVENUE"
    FREELANCE = "FREELANCE"
    QRIS_SETTLEMENT = "QRIS_SETTLEMENT"
    MARKETPLACE_SETTLEMENT = "MARKETPLACE_SETTLEMENT"
    OTHER = "OTHER"


class RecurringTypeEnum(StrEnum):
    """Gap-fill (PLAN §24.11): `recurring_series.series_type` — not
    enumerated in Appendix A. Added Sprint 4/T4.1.
    """

    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    DEBT_PAYMENT = "DEBT_PAYMENT"


class CashEventEnum(StrEnum):
    """Gap-fill (PLAN §24.11): `cash_flow_events.event_type` — not
    enumerated in Appendix A. Scoped to the two event classes Sprint 4's
    `CashFlowTwinEngine` actually produces (dominant income arrival,
    essential-expense due dates); Sprint 5's `ShockEngine` extends this set
    if a distinct shock-scenario event class is needed.
    """

    INCOME = "INCOME"
    ESSENTIAL_EXPENSE = "ESSENTIAL_EXPENSE"


class CoverageEnum(StrEnum):
    """Gap-fill (PLAN §24.11): `financial_profiles.coverage_flag` — not
    enumerated in Appendix A. PLAN §7.6/FR-7 EC names the `LOW_COVERAGE`
    flag explicitly (<2 months of data); `SUFFICIENT` is the complement.
    """

    SUFFICIENT = "SUFFICIENT"
    LOW_COVERAGE = "LOW_COVERAGE"


class InclusionEnum(StrEnum):
    """Gap-fill (PLAN §24.11): `assessment_documents`/`assessment_transactions
    .inclusion_status` — not enumerated in Appendix A. Added Sprint 4/T4.5.
    """

    INCLUDED = "INCLUDED"
    EXCLUDED = "EXCLUDED"


class ReasonTypeEnum(StrEnum):
    """PLAN §11.3 `assessment_reason_codes.reason_type` — member set given
    inline (`POSITIVE, RISK, DATA_QUALITY, OFFER`), not in Appendix A.
    """

    POSITIVE = "POSITIVE"
    RISK = "RISK"
    DATA_QUALITY = "DATA_QUALITY"
    OFFER = "OFFER"


class SeverityEnum(StrEnum):
    """Gap-fill (PLAN §24.11): `assessment_reason_codes.severity` — not
    enumerated in Appendix A. Added Sprint 4/T4.5.
    """

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DocStatusEnum(StrEnum):
    """PLAN §8.2's state diagram plus Appendix A, with three gap-filled
    states (PLAN §24.11) that the diagram requires but Appendix A's list
    omits: `VALIDATION_FAILED` (oversize/corrupt/zero-byte), `DUPLICATE_REUSED`
    (same user+hash re-upload) — both Sprint 2 — and `REVIEW_PENDING`
    (Sprint 3: `VERIFYING -> REVIEW_PENDING -> NORMALIZING` per the diagram,
    also missing from Appendix A).
    """

    UPLOADED = "UPLOADED"
    SECURITY_CHECK = "SECURITY_CHECK"
    REJECTED_SECURITY = "REJECTED_SECURITY"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    DUPLICATE_REUSED = "DUPLICATE_REUSED"
    EXTRACTING = "EXTRACTING"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    VERIFYING = "VERIFYING"
    REVIEW_PENDING = "REVIEW_PENDING"
    NORMALIZING = "NORMALIZING"
    ANALYZING = "ANALYZING"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    COMPLETE = "COMPLETE"


class ShockTypeEnum(StrEnum):
    """Gap-fill (PLAN §24.11): `shock_scenarios.scenario_type` — not
    enumerated in Appendix A. Member set is PLAN §5.8's documented default
    scenario battery (income-drop tiers, delayed dominant income, a fixed
    emergency expense, largest-income-source loss, weakest-month replay) plus
    `CUSTOM` for `POST /assessments/{id}/simulate`'s user-adjustable inputs
    (PLAN §12.2/§12.3). Added Sprint 5/T5.1.
    """

    INCOME_DROP_10 = "INCOME_DROP_10"
    INCOME_DROP_20 = "INCOME_DROP_20"
    INCOME_DROP_30 = "INCOME_DROP_30"
    DELAYED_INCOME = "DELAYED_INCOME"
    EMERGENCY_EXPENSE = "EMERGENCY_EXPENSE"
    INCOME_SOURCE_LOSS = "INCOME_SOURCE_LOSS"
    WEAKEST_MONTH_REPLAY = "WEAKEST_MONTH_REPLAY"
    CUSTOM = "CUSTOM"


class AffordEnum(StrEnum):
    """PLAN §5.8's documented outcome classes ("SURVIVABLE ... STRAINED ...
    DEFICIT"), used by both `shock_scenarios.affordability_status` and
    `offer_assessments.affordability_status` (both named `afford_enum` in
    §11.3 — one shared type, not two). Added Sprint 5/T5.1/T5.3.
    """

    SURVIVABLE = "SURVIVABLE"
    STRAINED = "STRAINED"
    DEFICIT = "DEFICIT"


class ShockResilienceBandEnum(StrEnum):
    """PLAN §5.8: "Bands: STRONG >= 75, MODERATE 50-74, FRAGILE < 50" — named
    only in prose, not a stored column (`assessments.shock_resilience_score`
    stores the `NUMERIC` score only; the band is computed on read, the same
    pattern `band_from_score` already uses for Data Confidence). Added
    Sprint 5/T5.1.
    """

    STRONG = "STRONG"
    MODERATE = "MODERATE"
    FRAGILE = "FRAGILE"


class OfferSourceEnum(StrEnum):
    """PLAN §11.3 `lender_offers.offer_source` — member set given inline
    (`SIMULATED, LENDER_API, MANUAL_LENDER_ENTRY`), not in Appendix A. Added
    Sprint 5/T5.3.
    """

    SIMULATED = "SIMULATED"
    LENDER_API = "LENDER_API"
    MANUAL_LENDER_ENTRY = "MANUAL_LENDER_ENTRY"


class AmortizationEnum(StrEnum):
    """PLAN §5.7 "amortisation method (`FLAT | REDUCING_BALANCE |
    FIXED_SCHEDULE`)" — not enumerated in Appendix A. `FIXED_SCHEDULE` is
    reserved for a future lender-supplied schedule that doesn't follow either
    formula (not produced by `app/engines/loan_math.py` this sprint). Added
    Sprint 5/T5.3.
    """

    FLAT = "FLAT"
    REDUCING_BALANCE = "REDUCING_BALANCE"
    FIXED_SCHEDULE = "FIXED_SCHEDULE"


class RegStatusEnum(StrEnum):
    """PLAN §11.3 `lenders.regulatory_status` (`reg_status_enum`) documents
    two members (`REGULATED, UNLISTED`); a third, `SIMULATED_REGULATED_PROVIDER`,
    is required by FR-11 AC5 for MVP seeded providers so offer copy never
    implies a real regulated endorsement (PLAN §6.4/§16 non-goals: no real
    lender integration in MVP). Added Sprint 5/T5.3.
    """

    REGULATED = "REGULATED"
    UNLISTED = "UNLISTED"
    SIMULATED_REGULATED_PROVIDER = "SIMULATED_REGULATED_PROVIDER"


class OfferRatingEnum(StrEnum):
    """Gap-fill (PLAN §24.11): PLAN §11.3's `offer_assessments` row types
    `total_cost_status`/`timing_status` as a generic `status_enum` without
    naming its members. A three-tier rating (rather than reusing `band_enum`,
    which is the Trust-Layer-specific HIGH/MEDIUM/LOW vocabulary) keeps offer
    copy in its own domain language. Added Sprint 5/T5.3.
    """

    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"


class OfferSafetyBandEnum(StrEnum):
    """PLAN §5.9: "Bands: SAFE >= 75, CAUTION 50-74, UNSAFE < 50" — named
    only in prose; `offer_assessments` stores `safe_offer_score` (`NUMERIC`)
    and `rank` (`INT`) but no band column, so this is computed on read (same
    pattern as `ShockResilienceBandEnum` above). Added Sprint 5/T5.3.
    """

    SAFE = "SAFE"
    CAUTION = "CAUTION"
    UNSAFE = "UNSAFE"
