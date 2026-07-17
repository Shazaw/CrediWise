"""`RiskEngine` golden tests (PLAN §5.3, §5.5, FR-8; §21.1 gate tests,
§24.8 "engines >= 90% coverage")."""

from decimal import Decimal

from app.engines.risk import DEFAULT_CONFIG, RiskInput, run
from app.models.enums import BandEnum, RiskBandEnum


def _strong_input(**overrides: object) -> RiskInput:
    base: dict[str, object] = {
        "median_income": 3_000_000,
        "essential_expenses": 1_500_000,
        "discretionary_expenses": 300_000,
        "existing_debt_service": 200_000,
        "positive_cash_flow_ratio": Decimal("0.9"),
        "income_volatility": Decimal("0.05"),
        "months_covered": 6,
        "data_confidence_band": BandEnum.HIGH,
        "income_concentration_ratio": Decimal("0.5"),
        "ocr_score": Decimal("95"),
        "ownership_score": Decimal("100"),
        "completeness_score": Decimal("100"),
    }
    base.update(overrides)
    return RiskInput(**base)  # type: ignore[arg-type]


def test_strong_profile_yields_band_a_and_high_confidence() -> None:
    result = run(_strong_input())

    assert result.band is RiskBandEnum.A
    assert result.model_confidence is BandEnum.HIGH
    assert result.composite_score >= 80


def test_insufficient_data_when_data_confidence_low() -> None:
    """PLAN §5.3: "If Data Confidence band = LOW ... -> INSUFFICIENT_DATA
    regardless of composite"."""
    result = run(_strong_input(data_confidence_band=BandEnum.LOW))

    assert result.band is RiskBandEnum.INSUFFICIENT_DATA
    assert any(r.code == "RISK_INSUFFICIENT_DATA" for r in result.reason_codes)


def test_insufficient_data_when_coverage_below_two_months() -> None:
    result = run(_strong_input(months_covered=1))

    assert result.band is RiskBandEnum.INSUFFICIENT_DATA


def test_thin_data_never_reports_high_confidence() -> None:
    """FR-8 AC2: "a low-risk result derived from thin data must be shown
    with reduced model confidence -- never high confidence"."""
    result = run(_strong_input(months_covered=3, data_confidence_band=BandEnum.MEDIUM))

    assert result.model_confidence is not BandEnum.HIGH


def test_model_confidence_low_below_two_months() -> None:
    result = run(_strong_input(months_covered=1))

    assert result.model_confidence is BandEnum.LOW


def test_high_dsti_penalizes_obligation_load_score() -> None:
    result = run(_strong_input(existing_debt_service=1_800_000))  # 60% DSTI -> "high"

    assert result.obligation_load_score == Decimal("20.00")
    assert any(r.code == "RISK_DSTI_HIGH" for r in result.reason_codes)


def test_excellent_dsti_scores_full_marks() -> None:
    result = run(_strong_input(existing_debt_service=300_000))  # 10% DSTI -> "excellent"

    assert result.obligation_load_score == Decimal("100.00")
    assert any(r.code == "RISK_DSTI_EXCELLENT" for r in result.reason_codes)


def test_weak_cash_flow_ratio_produces_lower_score_than_strong() -> None:
    weak = run(_strong_input(positive_cash_flow_ratio=Decimal("0.3")))
    strong = run(_strong_input(positive_cash_flow_ratio=Decimal("0.9")))

    assert weak.cash_flow_health_score < strong.cash_flow_health_score


def test_income_concentration_flagged_but_not_penalized() -> None:
    """PLAN §19.4 fairness: concentration is a reason code, not a score
    penalty (income_stability_score depends only on volatility)."""
    concentrated = run(_strong_input(income_concentration_ratio=Decimal("0.95")))
    diversified = run(_strong_input(income_concentration_ratio=Decimal("0.3")))

    assert concentrated.income_stability_score == diversified.income_stability_score
    assert any(r.code == "RISK_INCOME_CONCENTRATION" for r in concentrated.reason_codes)
    assert not any(r.code == "RISK_INCOME_CONCENTRATION" for r in diversified.reason_codes)


def test_high_discretionary_spending_lowers_behaviour_score() -> None:
    disciplined = run(_strong_input(discretionary_expenses=100_000))
    lax = run(_strong_input(discretionary_expenses=2_000_000))

    assert lax.behaviour_score < disciplined.behaviour_score


def test_zero_income_behaviour_score_does_not_crash() -> None:
    result = run(_strong_input(median_income=0, existing_debt_service=0))

    assert result.behaviour_score == Decimal(0)


def test_weak_profile_yields_band_d() -> None:
    result = run(
        _strong_input(
            positive_cash_flow_ratio=Decimal("0.2"),
            income_volatility=Decimal("0.8"),
            existing_debt_service=2_000_000,
            discretionary_expenses=1_500_000,
        )
    )

    assert result.band is RiskBandEnum.D


def test_default_config_loads_weights_summing_to_one() -> None:
    assert sum(DEFAULT_CONFIG.weights.values()) == Decimal("1.00")
