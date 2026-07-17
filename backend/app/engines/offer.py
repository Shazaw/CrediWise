"""`OfferEngine` — Safe Offer Score (PLAN §5.9, §15.1; FR-11).

Pure per PLAN §10.1: no DB, network, filesystem, clock, or RNG. Consumes one
already-fully-computed offer (loan-mathematics fields from
`app/engines/loan_math.py`, seeded/simulated by the service layer) plus plain
scalars from the assessment's Twin/SafeBorrowing/Shock results -- this engine
never calls `ShockEngine` directly (PLAN §10.1); the service layer runs
`shock.run()` once per offer (substituting that offer's own instalment as
`proposed_instalment`) and passes in the resulting resilience score, the same
composition pattern `assessment_service.py` already uses for Twin -> Risk ->
SafeBorrowing.

Each of PLAN §5.9's eight weighted factors is a Sprint 5 gap-fill (§24.11)
for its exact scoring curve -- PLAN names the *signal* each factor evaluates
(e.g. "respects Maximum Safe Instalment and essential coverage") but not a
point scale. Every factor score is 0-100; the composite `safe_offer_score` is
their weighted sum (weights sum to 1.00, PLAN §5.9's documented split).
Commission is never an input (PLAN §5.9: "Commission is never an input").
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.engines.config import model_config as cfg
from app.models.enums import (
    AffordEnum,
    BandEnum,
    OfferRatingEnum,
    OfferSafetyBandEnum,
    OfferSourceEnum,
    RegStatusEnum,
)

_SCORE_Q = Decimal("0.01")

#: PLAN §5.9: "Reason code REFINANCING_DEPENDENCY_RISK is required when
#: normal affordability masks inadequate volatility/emergency buffer" --
#: used verbatim, not prefixed like this engine's other codes.
REFINANCING_DEPENDENCY_RISK = "REFINANCING_DEPENDENCY_RISK"


@dataclass(frozen=True)
class ReasonCode:
    code: str
    description: str


@dataclass(frozen=True)
class OfferInput:
    instalment_amount: int
    principal_amount: int
    net_disbursed_amount: int
    effective_annual_rate: Decimal | None
    reference_effective_annual_rate: Decimal | None
    late_penalty_terms_present: bool
    due_date: int
    maximum_safe_instalment: int
    actual_safe_principal: int
    actual_terms_description: str
    average_free_cash_flow: int
    essential_expenses: int
    required_liquidity_buffer: int
    shock_resilience_score_for_offer: Decimal
    regulatory_status: RegStatusEnum
    offer_source: OfferSourceEnum = OfferSourceEnum.SIMULATED
    recommended_due_date_start: int | None = None
    recommended_due_date_end: int | None = None


@dataclass(frozen=True)
class OfferConfig:
    weights: dict[str, Decimal]
    provider_verification_scores: dict[str, int]
    refinancing_dependency_buffer_ratio: Decimal
    timing_fit_tolerance_days: int
    cost_penalty_scale: Decimal
    affordability_penalty_scale: Decimal
    reference_annual_flat_rate: Decimal
    rating_thresholds: dict[str, int]
    trust_layer_band_thresholds: dict[str, int]


@dataclass(frozen=True)
class OfferScoreResult:
    instalment_affordability_score: Decimal
    within_safe_principal_score: Decimal
    shock_survivability_score: Decimal
    total_cost_score: Decimal
    fee_transparency_score: Decimal
    timing_fit_score: Decimal
    refinancing_dependency_score: Decimal
    provider_verification_score: Decimal
    safe_offer_score: Decimal
    affordability_status: AffordEnum
    shock_resilience_status: BandEnum
    total_cost_status: OfferRatingEnum
    timing_status: OfferRatingEnum
    remaining_essential_expense_coverage: int
    remaining_essential_expense_coverage_ratio: Decimal
    refinancing_dependency: bool
    warning_flags: list[str] = field(default_factory=list)
    reason_codes: list[ReasonCode] = field(default_factory=list)


def default_config() -> OfferConfig:
    raw = cfg.CONFIG["offer"]
    assert isinstance(raw, dict)  # noqa: S101 - internal invariant, not user input
    trust_layer_raw = cfg.CONFIG["trust_layer"]
    assert isinstance(trust_layer_raw, dict)  # noqa: S101 - internal invariant, not user input
    return OfferConfig(
        weights=raw["weights"],
        provider_verification_scores=raw["provider_verification_scores"],
        refinancing_dependency_buffer_ratio=raw["refinancing_dependency_buffer_ratio"],
        timing_fit_tolerance_days=raw["timing_fit_tolerance_days"],
        cost_penalty_scale=raw["cost_penalty_scale"],
        affordability_penalty_scale=raw["affordability_penalty_scale"],
        reference_annual_flat_rate=raw["reference_annual_flat_rate"],
        rating_thresholds=raw["band_thresholds"],
        trust_layer_band_thresholds=trust_layer_raw["band_thresholds"],
    )


DEFAULT_CONFIG = default_config()


def run(inputs: OfferInput, config: OfferConfig = DEFAULT_CONFIG) -> OfferScoreResult:
    reason_codes: list[ReasonCode] = []
    warnings: list[str] = []

    instalment_score, exceeds_instalment = _ratio_score(
        inputs.instalment_amount, inputs.maximum_safe_instalment, config.affordability_penalty_scale
    )
    if exceeds_instalment:
        warnings.append("EXCEEDS_SAFE_INSTALMENT")
        reason_codes.append(
            ReasonCode(
                code="OFFER_EXCEEDS_SAFE_INSTALMENT",
                description="Instalment amount exceeds the Maximum Safe Instalment",
            )
        )

    principal_score, exceeds_principal = _ratio_score(
        inputs.principal_amount, inputs.actual_safe_principal, config.affordability_penalty_scale
    )
    if exceeds_principal:
        warnings.append("EXCEEDS_SAFE_PRINCIPAL")
        reason_codes.append(
            ReasonCode(
                code="OFFER_EXCEEDS_SAFE_PRINCIPAL",
                description=(
                    "Principal exceeds the safe ceiling calculated from actual terms: "
                    f"{inputs.actual_terms_description}"
                ),
            )
        )

    shock_score = inputs.shock_resilience_score_for_offer

    total_cost_score = _total_cost_score(inputs, config)
    if total_cost_score < config.rating_thresholds["caution"]:
        reason_codes.append(
            ReasonCode(
                code="OFFER_HIGH_EFFECTIVE_COST",
                description="Effective annual cost is materially above the reference rate",
            )
        )

    if inputs.late_penalty_terms_present:
        fee_transparency_score = Decimal(100)
    else:
        fee_transparency_score = Decimal(30)
        warnings.append("MISSING_FEE_DISCLOSURE")
        reason_codes.append(
            ReasonCode(
                code="OFFER_MISSING_FEE_DISCLOSURE",
                description="Late-penalty terms are not disclosed for this offer",
            )
        )

    timing_score = _timing_fit_score(inputs, config)

    remaining_free_cash_flow = inputs.average_free_cash_flow - inputs.instalment_amount
    refinancing_score, refinancing_risk = _refinancing_dependency_score(
        remaining_free_cash_flow, inputs.required_liquidity_buffer, config
    )
    if refinancing_risk:
        warnings.append(REFINANCING_DEPENDENCY_RISK)
        reason_codes.append(
            ReasonCode(
                code=REFINANCING_DEPENDENCY_RISK,
                description=(
                    "Remaining buffer after this instalment is inadequate for volatility or "
                    "emergency needs"
                ),
            )
        )

    provider_score = Decimal(
        config.provider_verification_scores.get(inputs.regulatory_status.value, 40)
    )

    remaining_essential_coverage = max(
        0, inputs.essential_expenses + inputs.average_free_cash_flow - inputs.instalment_amount
    )
    coverage_ratio = (
        Decimal(0)
        if inputs.essential_expenses <= 0
        else (Decimal(remaining_essential_coverage) / Decimal(inputs.essential_expenses)).quantize(
            _SCORE_Q, rounding=ROUND_HALF_UP
        )
    )

    sub_scores = {
        "instalment_affordability": instalment_score,
        "within_safe_principal": principal_score,
        "shock_survivability": shock_score,
        "total_cost": total_cost_score,
        "fee_transparency": fee_transparency_score,
        "timing_fit": timing_score,
        "refinancing_dependency": refinancing_score,
        "provider_verification": provider_score,
    }
    safe_offer_score = sum(
        (config.weights[name] * score for name, score in sub_scores.items()), start=Decimal("0")
    ).quantize(_SCORE_Q, rounding=ROUND_HALF_UP)

    # Every offer returns a stable minimum explanation set, including positive
    # evidence when no warning path fired (PLAN explainability coverage).
    reason_codes.extend(
        [
            ReasonCode(
                code="OFFER_ESSENTIAL_COVERAGE",
                description=(
                    f"Remaining cash covers {coverage_ratio} times monthly essential expenses"
                ),
            ),
            ReasonCode(
                code="OFFER_SHOCK_SURVIVABILITY",
                description=f"Offer-specific shock resilience score is {shock_score}",
            ),
        ]
    )
    if inputs.offer_source is OfferSourceEnum.SIMULATED:
        reason_codes.append(
            ReasonCode(
                code="OFFER_SIMULATED_PROVIDER",
                description="This is a simulated offer and is not a real provider endorsement",
            )
        )

    if remaining_free_cash_flow < 0:
        affordability_status = AffordEnum.DEFICIT
    elif exceeds_instalment:
        affordability_status = AffordEnum.STRAINED
    else:
        affordability_status = AffordEnum.SURVIVABLE

    return OfferScoreResult(
        instalment_affordability_score=instalment_score,
        within_safe_principal_score=principal_score,
        shock_survivability_score=shock_score,
        total_cost_score=total_cost_score,
        fee_transparency_score=fee_transparency_score,
        timing_fit_score=timing_score,
        refinancing_dependency_score=refinancing_score,
        provider_verification_score=provider_score,
        safe_offer_score=safe_offer_score,
        affordability_status=affordability_status,
        shock_resilience_status=_trust_layer_band(shock_score, config),
        total_cost_status=_rating_for(total_cost_score, config),
        timing_status=_rating_for(timing_score, config),
        remaining_essential_expense_coverage=remaining_essential_coverage,
        remaining_essential_expense_coverage_ratio=coverage_ratio,
        refinancing_dependency=refinancing_risk,
        warning_flags=warnings,
        reason_codes=reason_codes,
    )


def _ratio_score(actual: int, ceiling: int, penalty_scale: Decimal) -> tuple[Decimal, bool]:
    """100 when `actual` is within `ceiling`; scaled down the further it
    exceeds it. `ceiling <= 0` means no safe capacity exists at all -- any
    positive `actual` is a full penalty."""
    if ceiling <= 0:
        return (Decimal(100), False) if actual <= 0 else (Decimal(0), True)
    if actual <= ceiling:
        return Decimal(100), False
    excess_ratio = Decimal(actual - ceiling) / Decimal(ceiling)
    score = max(Decimal(0), Decimal(100) - excess_ratio * penalty_scale).quantize(
        _SCORE_Q, rounding=ROUND_HALF_UP
    )
    return score, True


def _total_cost_score(inputs: OfferInput, config: OfferConfig) -> Decimal:
    if inputs.effective_annual_rate is None or inputs.reference_effective_annual_rate is None:
        rate_score = Decimal(50)
    elif inputs.effective_annual_rate <= inputs.reference_effective_annual_rate:
        rate_score = Decimal(100)
    else:
        excess_ratio = (
            inputs.effective_annual_rate - inputs.reference_effective_annual_rate
        ) / inputs.reference_effective_annual_rate
        rate_score = max(Decimal(0), Decimal(100) - excess_ratio * config.cost_penalty_scale)
    proceeds_ratio = (
        Decimal(0)
        if inputs.principal_amount <= 0
        else min(
            Decimal(1),
            max(Decimal(0), Decimal(inputs.net_disbursed_amount) / inputs.principal_amount),
        )
    )
    proceeds_score = proceeds_ratio * Decimal(100)
    return ((rate_score + proceeds_score) / Decimal(2)).quantize(_SCORE_Q, rounding=ROUND_HALF_UP)


def _timing_fit_score(inputs: OfferInput, config: OfferConfig) -> Decimal:
    if inputs.recommended_due_date_start is None or inputs.recommended_due_date_end is None:
        return Decimal(70)
    tolerance = config.timing_fit_tolerance_days
    low = inputs.recommended_due_date_start - tolerance
    high = inputs.recommended_due_date_end + tolerance
    if low <= inputs.due_date <= high:
        return Decimal(100)
    distance = min(abs(inputs.due_date - low), abs(inputs.due_date - high))
    return max(Decimal(0), Decimal(100) - Decimal(distance) * Decimal(10)).quantize(
        _SCORE_Q, rounding=ROUND_HALF_UP
    )


def _refinancing_dependency_score(
    remaining_free_cash_flow: int, required_liquidity_buffer: int, config: OfferConfig
) -> tuple[Decimal, bool]:
    required = _to_money(
        Decimal(required_liquidity_buffer) * config.refinancing_dependency_buffer_ratio
    )
    if required <= 0:
        return Decimal(100), False
    if remaining_free_cash_flow >= required:
        return Decimal(100), False
    ratio = max(Decimal(0), Decimal(remaining_free_cash_flow) / Decimal(required))
    score = (ratio * Decimal(100)).quantize(_SCORE_Q, rounding=ROUND_HALF_UP)
    return score, True


def _trust_layer_band(score: Decimal, config: OfferConfig) -> BandEnum:
    if score >= config.trust_layer_band_thresholds["high"]:
        return BandEnum.HIGH
    if score >= config.trust_layer_band_thresholds["medium"]:
        return BandEnum.MEDIUM
    return BandEnum.LOW


def _rating_for(score: Decimal, config: OfferConfig) -> OfferRatingEnum:
    if score >= config.rating_thresholds["safe"]:
        return OfferRatingEnum.GOOD
    if score >= config.rating_thresholds["caution"]:
        return OfferRatingEnum.FAIR
    return OfferRatingEnum.POOR


def _to_money(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def offer_safety_band_from_score(
    score: Decimal, config: OfferConfig = DEFAULT_CONFIG
) -> OfferSafetyBandEnum:
    """PLAN §5.9: "SAFE >= 75, CAUTION 50-74, UNSAFE < 50" -- `offer_assessments`
    stores `safe_offer_score` only (§11.3), so the band is computed on read,
    the same pattern `assessment_service.band_from_score` uses for Data
    Confidence."""
    if score >= config.rating_thresholds["safe"]:
        return OfferSafetyBandEnum.SAFE
    if score >= config.rating_thresholds["caution"]:
        return OfferSafetyBandEnum.CAUTION
    return OfferSafetyBandEnum.UNSAFE
