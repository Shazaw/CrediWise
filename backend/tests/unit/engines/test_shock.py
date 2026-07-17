"""`ShockEngine` golden tests (PLAN §5.8, FR-10; §21.1 gate tests, §24.8
"engines >= 90% coverage", boundary/rounding/zero-cash-flow cases per
CLAUDE.md §7.4)."""

from decimal import Decimal

from app.engines.shock import (
    DEFAULT_CONFIG,
    CashFlowEventInput,
    ShockInput,
    band_from_score,
    moderate_shock_capacity,
    run,
)
from app.models.enums import (
    AffordEnum,
    CashEventEnum,
    DirEnum,
    ShockResilienceBandEnum,
    ShockTypeEnum,
)


def _healthy_input(**overrides: object) -> ShockInput:
    base: dict[str, object] = {
        "median_income": 3_000_000,
        "essential_expenses": 1_200_000,
        "average_free_cash_flow": 1_000_000,
        "weakest_month_cash_flow": 800_000,
        "savings_buffer": 2_000_000,
        "required_liquidity_buffer": 500_000,
        "proposed_instalment": 300_000,
        "largest_income_source_amount": 2_500_000,
        "cash_flow_events": (
            CashFlowEventInput(5, 3_000_000, DirEnum.CREDIT, CashEventEnum.INCOME),
            CashFlowEventInput(10, 1_200_000, DirEnum.DEBIT, CashEventEnum.ESSENTIAL_EXPENSE),
        ),
    }
    base.update(overrides)
    return ShockInput(**base)  # type: ignore[arg-type]


def test_scenario_weights_sum_to_one() -> None:
    assert sum(DEFAULT_CONFIG.scenario_weights.values()) == Decimal("1.00")


def test_all_seven_default_scenarios_are_evaluated() -> None:
    result = run(_healthy_input())

    scenario_types = {s.scenario_type for s in result.scenarios}
    assert scenario_types == {
        ShockTypeEnum.INCOME_DROP_10,
        ShockTypeEnum.INCOME_DROP_20,
        ShockTypeEnum.INCOME_DROP_30,
        ShockTypeEnum.DELAYED_INCOME,
        ShockTypeEnum.EMERGENCY_EXPENSE,
        ShockTypeEnum.INCOME_SOURCE_LOSS,
        ShockTypeEnum.WEAKEST_MONTH_REPLAY,
    }


def test_resilience_score_is_the_weighted_sum_of_scenario_contributions() -> None:
    result = run(_healthy_input())

    total = sum((s.resilience_score_contribution for s in result.scenarios), start=Decimal(0))
    assert result.resilience_score == total


def test_healthy_profile_is_survivable_and_strong() -> None:
    """Large savings buffer + comfortable free cash flow relative to a
    modest instalment -> every scenario SURVIVABLE, resilience 100, STRONG."""
    result = run(_healthy_input(proposed_instalment=0))

    assert result.resilience_score == Decimal("100.00")
    assert result.band is ShockResilienceBandEnum.STRONG
    assert all(s.affordability_status is AffordEnum.SURVIVABLE for s in result.scenarios)


def test_zero_buffer_and_high_instalment_produces_deficits() -> None:
    result = run(
        _healthy_input(
            savings_buffer=0,
            average_free_cash_flow=200_000,
            weakest_month_cash_flow=-100_000,
            proposed_instalment=900_000,
        )
    )

    assert result.band is ShockResilienceBandEnum.FRAGILE
    assert any(s.affordability_status is AffordEnum.DEFICIT for s in result.scenarios)
    assert any(r.code.startswith("SHOCK_DEFICIT_") for r in result.reason_codes)


def test_band_thresholds_are_boundary_correct() -> None:
    assert band_from_score(Decimal("75.00")) is ShockResilienceBandEnum.STRONG
    assert band_from_score(Decimal("74.99")) is ShockResilienceBandEnum.MODERATE
    assert band_from_score(Decimal("50.00")) is ShockResilienceBandEnum.MODERATE
    assert band_from_score(Decimal("49.99")) is ShockResilienceBandEnum.FRAGILE


def test_delayed_income_preserves_monthly_cash_flow_but_moves_temporal_event() -> None:
    result = run(_healthy_input(proposed_instalment=0))

    delayed = next(s for s in result.scenarios if s.scenario_type is ShockTypeEnum.DELAYED_INCOME)
    assert delayed.projected_cash_flow == 1_000_000
    delayed_income = next(p for p in delayed.projection_points if p.event_type == "INCOME")
    assert delayed_income.day_of_month == 12


def test_income_source_loss_uses_largest_source_amount() -> None:
    result = run(_healthy_input(largest_income_source_amount=2_500_000, proposed_instalment=0))

    loss = next(s for s in result.scenarios if s.scenario_type is ShockTypeEnum.INCOME_SOURCE_LOSS)
    assert loss.projected_cash_flow == 1_000_000 - 2_500_000


def test_income_source_loss_defaults_to_zero_when_no_income_sources() -> None:
    result = run(_healthy_input(largest_income_source_amount=None, proposed_instalment=0))

    loss = next(s for s in result.scenarios if s.scenario_type is ShockTypeEnum.INCOME_SOURCE_LOSS)
    assert loss.projected_cash_flow == 1_000_000


def test_custom_scenario_appended_only_when_overrides_provided() -> None:
    without_overrides = run(_healthy_input())
    assert all(s.scenario_type is not ShockTypeEnum.CUSTOM for s in without_overrides.scenarios)

    with_overrides = run(
        _healthy_input(custom_income_drop_pct=Decimal("0.5"), custom_emergency_expense=2_000_000)
    )
    custom = next(s for s in with_overrides.scenarios if s.scenario_type is ShockTypeEnum.CUSTOM)
    assert custom.resilience_score_contribution == Decimal("0.00")


def test_custom_scenario_never_changes_the_resilience_score() -> None:
    baseline = run(_healthy_input())
    with_custom = run(
        _healthy_input(custom_income_drop_pct=Decimal("0.9"), custom_emergency_expense=5_000_000)
    )

    assert baseline.resilience_score == with_custom.resilience_score


def test_proposed_instalment_only_can_request_custom_preview() -> None:
    result = run(_healthy_input(include_custom_scenario=True, proposed_instalment=777_000))
    custom = next(s for s in result.scenarios if s.scenario_type is ShockTypeEnum.CUSTOM)
    assert custom.projected_cash_flow == 223_000


def test_moderate_shock_capacity_matches_safe_borrowing_derivation() -> None:
    """The exact same closed form `safe_borrowing.py` duplicates for
    `ShockCapacity` (ADR-016)."""
    capacity = moderate_shock_capacity(
        savings_buffer=2_000_000,
        average_free_cash_flow=1_000_000,
        median_income=3_000_000,
        moderate_shock_income_drop_pct=Decimal("0.20"),
    )
    assert capacity == 2_000_000 + 1_000_000 - 600_000


def test_moderate_shock_capacity_floors_at_zero() -> None:
    capacity = moderate_shock_capacity(
        savings_buffer=0,
        average_free_cash_flow=0,
        median_income=3_000_000,
        moderate_shock_income_drop_pct=Decimal("0.20"),
    )
    assert capacity == 0


def test_delayed_income_past_repayment_due_date_creates_temporary_deficit() -> None:
    result = run(
        _healthy_input(
            savings_buffer=400_000,
            required_liquidity_buffer=500_000,
            proposed_instalment=500_000,
            proposed_instalment_day=10,
            cash_flow_events=(
                CashFlowEventInput(5, 3_000_000, DirEnum.CREDIT, CashEventEnum.INCOME),
            ),
        )
    )
    delayed = next(s for s in result.scenarios if s.scenario_type is ShockTypeEnum.DELAYED_INCOME)
    assert delayed.projected_cash_flow == 500_000
    assert delayed.minimum_projected_balance == -100_000
    assert delayed.affordability_status is AffordEnum.DEFICIT
    assert delayed.required_buffer_breached is True


def test_identical_inputs_produce_identical_ordered_results() -> None:
    assert run(_healthy_input()) == run(_healthy_input())
    sequences = [p.sequence for p in run(_healthy_input()).scenarios[0].projection_points]
    assert sequences == list(range(len(sequences)))


def test_zero_and_negative_cash_flow_are_deterministic_deficits() -> None:
    zero = run(_healthy_input(average_free_cash_flow=0, savings_buffer=0))
    negative = run(_healthy_input(average_free_cash_flow=-1, savings_buffer=0))
    assert any(s.affordability_status is AffordEnum.DEFICIT for s in zero.scenarios)
    assert any(s.affordability_status is AffordEnum.DEFICIT for s in negative.scenarios)


def test_whole_idr_rounding_is_half_up() -> None:
    result = run(
        _healthy_input(
            median_income=5,
            average_free_cash_flow=0,
            proposed_instalment=0,
            custom_income_drop_pct=Decimal("0.5"),
            custom_emergency_expense=0,
            cash_flow_events=(),
        )
    )
    custom = next(s for s in result.scenarios if s.scenario_type is ShockTypeEnum.CUSTOM)
    assert custom.projected_cash_flow == -3


def test_shock_result_always_has_three_structured_reasons() -> None:
    assert len(run(_healthy_input()).reason_codes) >= 3
