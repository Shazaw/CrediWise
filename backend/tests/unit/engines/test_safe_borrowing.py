"""`SafeBorrowingEngine` golden tests (PLAN §5.6, §5.7, FR-9; §21.1 gate
tests, §24.8 "engines >= 90% coverage", boundary/rounding/zero-cash-flow
cases per CLAUDE.md §7.4)."""

from decimal import Decimal

from app.engines.safe_borrowing import (
    DEFAULT_CONFIG,
    SafeBorrowingInput,
    principal_from_instalment,
    run,
)
from app.models.enums import FreqEnum


def _healthy_input(**overrides: object) -> SafeBorrowingInput:
    base: dict[str, object] = {
        "median_income": 3_000_000,
        "essential_expenses": 1_200_000,
        "existing_debt_service": 200_000,
        "income_volatility": Decimal("0.1"),
        "weakest_month_cash_flow": 800_000,
        "average_free_cash_flow": 1_000_000,
        "requested_amount": 3_500_000,
        "min_monthly_minimum_balance": 2_000_000,
        "dominant_income_day": 25,
        "dominant_income_frequency": FreqEnum.MONTHLY,
    }
    base.update(overrides)
    return SafeBorrowingInput(**base)  # type: ignore[arg-type]


def test_zero_free_cash_flow_yields_zero_safe_amount() -> None:
    """FR-9 EC: "free cash flow <= 0 -> safe amount = Rp0 with an
    explanatory message (no loan is safe)"."""
    result = run(_healthy_input(average_free_cash_flow=0))

    assert result.maximum_safe_instalment == 0
    assert result.safe_loan_amount == 0
    assert any(r.code == "SAFE_BORROWING_ZERO_CAPACITY" for r in result.reason_codes)


def test_negative_free_cash_flow_yields_zero_safe_amount() -> None:
    result = run(_healthy_input(average_free_cash_flow=-50_000))

    assert result.maximum_safe_instalment == 0
    assert result.safe_loan_amount == 0


def test_negative_base_capacity_floors_at_zero() -> None:
    """Essential expenses + debt + buffer exceed income -- capacity is
    floored at 0, never negative."""
    result = run(
        _healthy_input(
            median_income=1_000_000,
            essential_expenses=1_500_000,
            existing_debt_service=200_000,
            average_free_cash_flow=-700_000,
        )
    )

    assert result.base_capacity == 0
    assert result.maximum_safe_instalment == 0


def test_healthy_profile_produces_positive_recommendation() -> None:
    result = run(_healthy_input())

    assert result.maximum_safe_instalment > 0
    assert result.safe_loan_amount > 0
    assert result.recommended_tenor_months in DEFAULT_CONFIG.tenor_candidates
    assert result.recommended_due_date_start <= result.recommended_due_date_end


def test_high_dsti_binds_the_capacity() -> None:
    """When DSTI's 35% ceiling is tighter than the other three terms,
    DSTICapacity should be the binding (smallest) constraint. With income=10M
    and essential=1M, buffer is dominated by the 0.5*income term (5M), so
    BaseCapacity = income - essential - debt - buffer = 4M - debt while
    DSTICapacity = 0.35*income - debt = 3.5M - debt -- DSTI is always 500k
    tighter than base here, independent of debt."""
    result = run(
        _healthy_input(
            median_income=10_000_000,
            essential_expenses=1_000_000,
            existing_debt_service=1_000_000,
            weakest_month_cash_flow=5_000_000,
            min_monthly_minimum_balance=None,
            average_free_cash_flow=3_000_000,
        )
    )

    assert result.dsti_capacity == 2_500_000
    assert result.base_capacity == 3_000_000
    assert any(r.code == "SAFE_BORROWING_LIMITED_BY_DSTI" for r in result.reason_codes)


def test_weakest_month_binds_when_much_lower_than_average() -> None:
    result = run(_healthy_input(weakest_month_cash_flow=10_000, min_monthly_minimum_balance=None))

    assert result.maximum_safe_instalment <= 10_000
    assert any(r.code == "SAFE_BORROWING_LIMITED_BY_WEAKEST_MONTH" for r in result.reason_codes)


def test_temporal_liquidity_capacity_defaults_to_base_when_no_balance_data() -> None:
    result_with_data = run(_healthy_input(min_monthly_minimum_balance=500_000))
    result_without_data = run(_healthy_input(min_monthly_minimum_balance=None))

    assert result_without_data.temporal_liquidity_capacity == result_without_data.base_capacity
    assert (
        result_with_data.temporal_liquidity_capacity
        < result_without_data.temporal_liquidity_capacity
    )


def test_shortest_tenor_chosen_when_it_can_finance_the_full_request() -> None:
    result = run(_healthy_input(requested_amount=100_000))

    assert result.recommended_tenor_months == DEFAULT_CONFIG.tenor_candidates[0]
    assert result.safe_loan_amount >= 100_000


def test_longest_tenor_chosen_when_no_tenor_covers_the_full_request() -> None:
    result = run(_healthy_input(requested_amount=1_000_000_000))

    assert result.recommended_tenor_months == DEFAULT_CONFIG.tenor_candidates[-1]
    assert result.safe_loan_amount < 1_000_000_000


def test_due_date_window_offsets_from_dominant_income_day() -> None:
    result = run(_healthy_input(dominant_income_day=10))

    assert result.recommended_due_date_start == 10 + DEFAULT_CONFIG.due_date_offset_min_days
    assert result.recommended_due_date_end == 10 + DEFAULT_CONFIG.due_date_offset_max_days


def test_due_date_window_clamped_to_28_near_month_end() -> None:
    result = run(_healthy_input(dominant_income_day=27))

    assert result.recommended_due_date_start <= 28
    assert result.recommended_due_date_end <= 28


def test_due_date_window_defaults_without_income_day() -> None:
    result = run(_healthy_input(dominant_income_day=None))

    assert (result.recommended_due_date_start, result.recommended_due_date_end) == (
        DEFAULT_CONFIG.default_due_date_window
    )


def test_principal_from_instalment_matches_flat_rate_schedule() -> None:
    """PLAN §5.7: flat-rate amortisation -- principal recovered from its own
    instalment should round-trip to (approximately) the original instalment."""
    principal = principal_from_instalment(500_000, 12, Decimal("0.24"))
    rate_factor = Decimal(1) + Decimal("0.24") * Decimal(12) / Decimal(12)
    expected_instalment = (Decimal(principal) * rate_factor) / Decimal(12)

    assert abs(expected_instalment - Decimal(500_000)) < Decimal(1)


def test_zero_tenor_reference_rate_is_pure_principal_repayment() -> None:
    principal = principal_from_instalment(100_000, 6, Decimal("0"))

    assert principal == 600_000


def test_default_config_uses_documented_tenor_candidates() -> None:
    assert DEFAULT_CONFIG.tenor_candidates == (6, 9, 12)
    assert DEFAULT_CONFIG.reference_annual_flat_rate == Decimal("0.24")
