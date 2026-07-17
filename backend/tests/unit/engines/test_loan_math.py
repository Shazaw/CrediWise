"""`loan_math` golden tests (PLAN §5.7 Loan Mathematics Contract, FR-11
AC3; §21.1 gate tests, boundary/rounding cases per CLAUDE.md §7.4)."""

from decimal import Decimal

from app.engines.loan_math import compute
from app.models.enums import AmortizationEnum


def test_flat_schedule_sums_to_principal_plus_interest() -> None:
    result = compute(
        principal_amount=3_500_000,
        tenor_months=12,
        nominal_annual_rate=Decimal("0.24"),
        upfront_fee=0,
        amortization_method=AmortizationEnum.FLAT,
    )

    assert result.total_repayment == 3_500_000 + result.interest_amount
    assert sum(e.payment_amount for e in result.schedule) == result.total_repayment
    assert sum(e.principal_component for e in result.schedule) == 3_500_000
    assert result.schedule[-1].remaining_balance == 0
    assert all(
        e.payment_amount == e.principal_component + e.interest_component for e in result.schedule
    )


def test_flat_schedule_zero_rate_has_no_interest() -> None:
    result = compute(
        principal_amount=600_000,
        tenor_months=6,
        nominal_annual_rate=Decimal("0"),
        upfront_fee=0,
        amortization_method=AmortizationEnum.FLAT,
    )

    assert result.interest_amount == 0
    assert result.total_repayment == 600_000
    assert result.instalment_amount == 100_000


def test_reducing_balance_schedule_clears_exactly() -> None:
    result = compute(
        principal_amount=3_500_000,
        tenor_months=6,
        nominal_annual_rate=Decimal("0.36"),
        upfront_fee=70_000,
        amortization_method=AmortizationEnum.REDUCING_BALANCE,
    )

    assert result.schedule[-1].remaining_balance == 0
    assert sum(e.principal_component for e in result.schedule) == 3_500_000
    assert result.net_disbursed_amount == 3_500_000 - 70_000
    assert result.total_repayment == 3_500_000 + result.interest_amount


def test_reducing_balance_zero_rate_is_level_principal_only() -> None:
    result = compute(
        principal_amount=600_000,
        tenor_months=6,
        nominal_annual_rate=Decimal("0"),
        upfront_fee=0,
        amortization_method=AmortizationEnum.REDUCING_BALANCE,
    )

    assert result.interest_amount == 0
    assert result.total_repayment == 600_000


def test_zero_tenor_produces_empty_schedule() -> None:
    result = compute(
        principal_amount=1_000_000,
        tenor_months=0,
        nominal_annual_rate=Decimal("0.24"),
        upfront_fee=0,
        amortization_method=AmortizationEnum.FLAT,
    )

    assert result.schedule == []
    assert result.instalment_amount == 0
    assert result.total_repayment == 0


def test_zero_tenor_reducing_balance_produces_empty_schedule() -> None:
    result = compute(
        principal_amount=1_000_000,
        tenor_months=0,
        nominal_annual_rate=Decimal("0.24"),
        upfront_fee=0,
        amortization_method=AmortizationEnum.REDUCING_BALANCE,
    )

    assert result.schedule == []


def test_effective_annual_rate_reducing_balance_matches_compounding_formula() -> None:
    result = compute(
        principal_amount=1_000_000,
        tenor_months=12,
        nominal_annual_rate=Decimal("0.24"),
        upfront_fee=0,
        amortization_method=AmortizationEnum.REDUCING_BALANCE,
    )

    monthly_rate = Decimal("0.24") / Decimal(12)
    expected = (Decimal(1) + monthly_rate) ** 12 - Decimal(1)
    assert abs(result.effective_annual_rate - expected) < Decimal("0.0001")


def test_effective_annual_rate_flat_exceeds_nominal_rate() -> None:
    """The flat-rate effective-cost conversion charges interest against the
    average outstanding balance (~principal/2), so it always reads higher
    than the nominal flat rate itself."""
    result = compute(
        principal_amount=1_000_000,
        tenor_months=12,
        nominal_annual_rate=Decimal("0.24"),
        upfront_fee=0,
        amortization_method=AmortizationEnum.FLAT,
    )

    assert result.effective_annual_rate > Decimal("0.24")


def test_zero_principal_yields_zero_effective_rate() -> None:
    result = compute(
        principal_amount=0,
        tenor_months=12,
        nominal_annual_rate=Decimal("0.24"),
        upfront_fee=0,
        amortization_method=AmortizationEnum.FLAT,
    )

    assert result.effective_annual_rate == Decimal(0)
