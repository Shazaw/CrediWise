"""`OfferEngine` golden tests (PLAN §5.9, FR-11; §21.1 gate tests, §24.8
"engines >= 90% coverage", boundary/rounding cases per CLAUDE.md §7.4)."""

from decimal import Decimal

from app.engines.offer import DEFAULT_CONFIG, OfferInput, offer_safety_band_from_score, run
from app.models.enums import AffordEnum, OfferSafetyBandEnum, RegStatusEnum


def _safe_input(**overrides: object) -> OfferInput:
    base: dict[str, object] = {
        "instalment_amount": 350_000,
        "principal_amount": 3_500_000,
        "effective_annual_rate": Decimal("0.24"),
        "late_penalty_terms_present": True,
        "due_date": 22,
        "maximum_safe_instalment": 375_000,
        "safe_loan_amount": 3_800_000,
        "average_free_cash_flow": 1_000_000,
        "required_liquidity_buffer": 500_000,
        "shock_resilience_score_for_offer": Decimal("90"),
        "regulatory_status": RegStatusEnum.SIMULATED_REGULATED_PROVIDER,
        "recommended_due_date_start": 20,
        "recommended_due_date_end": 25,
    }
    base.update(overrides)
    return OfferInput(**base)  # type: ignore[arg-type]


def test_weights_sum_to_one() -> None:
    assert sum(DEFAULT_CONFIG.weights.values()) == Decimal("1.00")


def test_within_safe_limits_scores_highly_and_raises_no_warnings() -> None:
    result = run(_safe_input())

    assert result.safe_offer_score >= Decimal("75")
    assert offer_safety_band_from_score(result.safe_offer_score) is OfferSafetyBandEnum.SAFE
    assert result.warning_flags == []
    assert result.affordability_status is AffordEnum.SURVIVABLE


def test_exceeding_safe_instalment_flags_and_penalizes() -> None:
    within = run(_safe_input())
    exceeding = run(_safe_input(instalment_amount=900_000))

    assert exceeding.instalment_affordability_score < within.instalment_affordability_score
    assert "EXCEEDS_SAFE_INSTALMENT" in exceeding.warning_flags


def test_exceeding_safe_principal_flags_and_penalizes() -> None:
    result = run(_safe_input(principal_amount=6_000_000))

    assert "EXCEEDS_SAFE_PRINCIPAL" in result.warning_flags


def test_zero_safe_capacity_ceiling_is_a_full_penalty_unless_actual_is_zero() -> None:
    zero_actual = run(_safe_input(instalment_amount=0, maximum_safe_instalment=0))
    positive_actual = run(_safe_input(instalment_amount=100_000, maximum_safe_instalment=0))

    assert zero_actual.instalment_affordability_score == Decimal(100)
    assert positive_actual.instalment_affordability_score == Decimal(0)


def test_missing_fee_disclosure_penalizes_and_flags() -> None:
    result = run(_safe_input(late_penalty_terms_present=False))

    assert result.fee_transparency_score == Decimal(30)
    assert "MISSING_FEE_DISCLOSURE" in result.warning_flags
    assert any(r.code == "OFFER_MISSING_FEE_DISCLOSURE" for r in result.reason_codes)


def test_high_effective_cost_lowers_total_cost_score() -> None:
    cheap = run(_safe_input(effective_annual_rate=Decimal("0.20")))
    expensive = run(_safe_input(effective_annual_rate=Decimal("0.60")))

    assert expensive.total_cost_score < cheap.total_cost_score
    assert cheap.total_cost_score == Decimal(100)


def test_unknown_effective_rate_is_a_neutral_score() -> None:
    result = run(_safe_input(effective_annual_rate=None))

    assert result.total_cost_score == Decimal(50)


def test_refinancing_dependency_risk_flag_when_buffer_is_thin() -> None:
    result = run(
        _safe_input(
            instalment_amount=900_000,
            average_free_cash_flow=1_000_000,
            required_liquidity_buffer=500_000,
        )
    )

    assert "REFINANCING_DEPENDENCY_RISK" in result.warning_flags
    assert any(r.code == "REFINANCING_DEPENDENCY_RISK" for r in result.reason_codes)


def test_no_refinancing_risk_when_buffer_is_comfortable() -> None:
    result = run(_safe_input(instalment_amount=100_000))

    assert "REFINANCING_DEPENDENCY_RISK" not in result.warning_flags


def test_timing_within_window_scores_full() -> None:
    result = run(
        _safe_input(due_date=22, recommended_due_date_start=20, recommended_due_date_end=25)
    )

    assert result.timing_status.value in {"GOOD"}


def test_timing_far_outside_window_scores_lower() -> None:
    aligned = run(_safe_input(due_date=22))
    misaligned = run(_safe_input(due_date=1))

    assert misaligned.timing_fit_score < aligned.timing_fit_score


def test_timing_neutral_without_recommended_window() -> None:
    result = run(_safe_input(recommended_due_date_start=None, recommended_due_date_end=None))

    assert result.timing_fit_score == Decimal(70)


def test_provider_verification_scores_regulated_above_unlisted() -> None:
    regulated = run(_safe_input(regulatory_status=RegStatusEnum.REGULATED))
    unlisted = run(_safe_input(regulatory_status=RegStatusEnum.UNLISTED))

    assert regulated.provider_verification_score > unlisted.provider_verification_score


def test_deficit_affordability_status_when_instalment_exceeds_free_cash_flow() -> None:
    result = run(_safe_input(instalment_amount=1_200_000, average_free_cash_flow=1_000_000))

    assert result.affordability_status is AffordEnum.DEFICIT


def test_dangerous_offer_scores_unsafe() -> None:
    result = run(
        _safe_input(
            instalment_amount=900_000,
            principal_amount=4_200_000,
            effective_annual_rate=Decimal("0.60"),
            late_penalty_terms_present=False,
            due_date=5,
            regulatory_status=RegStatusEnum.UNLISTED,
        )
    )

    assert offer_safety_band_from_score(result.safe_offer_score) is OfferSafetyBandEnum.UNSAFE
    assert len(result.warning_flags) >= 3


def test_band_thresholds_are_boundary_correct() -> None:
    assert offer_safety_band_from_score(Decimal("75.00")) is OfferSafetyBandEnum.SAFE
    assert offer_safety_band_from_score(Decimal("74.99")) is OfferSafetyBandEnum.CAUTION
    assert offer_safety_band_from_score(Decimal("50.00")) is OfferSafetyBandEnum.CAUTION
    assert offer_safety_band_from_score(Decimal("49.99")) is OfferSafetyBandEnum.UNSAFE


def test_no_refinancing_risk_when_required_buffer_is_zero() -> None:
    result = run(_safe_input(instalment_amount=1_000_000, required_liquidity_buffer=0))

    assert "REFINANCING_DEPENDENCY_RISK" not in result.warning_flags
    assert result.refinancing_dependency_score == Decimal(100)


def test_shock_resilience_status_covers_all_three_bands() -> None:
    high = run(_safe_input(shock_resilience_score_for_offer=Decimal("90")))
    medium = run(_safe_input(shock_resilience_score_for_offer=Decimal("60")))
    low = run(_safe_input(shock_resilience_score_for_offer=Decimal("20")))

    assert high.shock_resilience_status.value == "HIGH"
    assert medium.shock_resilience_status.value == "MEDIUM"
    assert low.shock_resilience_status.value == "LOW"
