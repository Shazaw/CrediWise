"""`loan_math` golden tests (PLAN §5.7 Loan Mathematics Contract, FR-11
AC3; §21.1 gate tests, boundary/rounding cases per CLAUDE.md §7.4)."""

from decimal import Decimal

from app.engines.loan_math import (
    compute,
    effective_annual_reference_rate,
    safe_principal_for_terms,
)
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
    assert result.effective_annual_rate is not None
    assert abs(result.effective_annual_rate - expected) < Decimal("0.0002")


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

    assert result.effective_annual_rate is not None
    assert result.effective_annual_rate > Decimal("0.24")


def test_zero_principal_yields_zero_effective_rate() -> None:
    result = compute(
        principal_amount=0,
        tenor_months=12,
        nominal_annual_rate=Decimal("0.24"),
        upfront_fee=0,
        amortization_method=AmortizationEnum.FLAT,
    )

    assert result.effective_annual_rate is None


def test_all_unfinanced_fees_reduce_net_proceeds_and_raise_effective_cost() -> None:
    without_fees = compute(
        principal_amount=1_000_000,
        tenor_months=12,
        nominal_annual_rate=Decimal("0.12"),
        upfront_fee=0,
        amortization_method=AmortizationEnum.REDUCING_BALANCE,
    )
    with_fees = compute(
        principal_amount=1_000_000,
        tenor_months=12,
        nominal_annual_rate=Decimal("0.12"),
        upfront_fee=10_000,
        service_fee=20_000,
        admin_fee=30_000,
        amortization_method=AmortizationEnum.REDUCING_BALANCE,
    )

    assert with_fees.net_disbursed_amount == 940_000
    assert with_fees.total_repayment == without_fees.total_repayment
    assert with_fees.effective_annual_rate is not None
    assert without_fees.effective_annual_rate is not None
    assert with_fees.effective_annual_rate > without_fees.effective_annual_rate


def test_financed_fee_is_repaid_in_schedule_and_not_deducted_from_proceeds() -> None:
    result = compute(
        principal_amount=1_000_000,
        tenor_months=10,
        nominal_annual_rate=Decimal("0"),
        upfront_fee=0,
        financed_fee=100_000,
        amortization_method=AmortizationEnum.FLAT,
    )

    assert result.net_disbursed_amount == 1_000_000
    assert sum(entry.principal_component for entry in result.schedule) == 1_100_000
    assert result.total_repayment == 1_100_000
    assert result.instalment_amount == 110_000
    assert result.effective_annual_rate is not None
    assert result.effective_annual_rate > 0


def test_non_positive_net_proceeds_has_no_effective_rate() -> None:
    result = compute(
        principal_amount=100_000,
        tenor_months=1,
        nominal_annual_rate=Decimal("0"),
        upfront_fee=100_000,
        amortization_method=AmortizationEnum.FLAT,
    )

    assert result.net_disbursed_amount == 0
    assert result.effective_annual_rate is None


def test_safe_principal_flat_boundary_uses_complete_rounded_schedule() -> None:
    safe_principal = safe_principal_for_terms(
        maximum_safe_instalment=100_000,
        tenor_months=6,
        nominal_annual_rate=Decimal("0"),
        amortization_method=AmortizationEnum.FLAT,
    )

    assert safe_principal == 600_000
    at_ceiling = compute(
        principal_amount=safe_principal,
        tenor_months=6,
        nominal_annual_rate=Decimal("0"),
        upfront_fee=0,
        amortization_method=AmortizationEnum.FLAT,
    )
    above_ceiling = compute(
        principal_amount=safe_principal + 1,
        tenor_months=6,
        nominal_annual_rate=Decimal("0"),
        upfront_fee=0,
        amortization_method=AmortizationEnum.FLAT,
    )
    assert max(entry.payment_amount for entry in at_ceiling.schedule) == 100_000
    assert max(entry.payment_amount for entry in above_ceiling.schedule) == 100_001


def test_safe_principal_accounts_for_financed_and_unfinanced_fee_treatments() -> None:
    without_financed_fee = safe_principal_for_terms(
        maximum_safe_instalment=100_000,
        tenor_months=6,
        nominal_annual_rate=Decimal("0"),
        amortization_method=AmortizationEnum.FLAT,
        upfront_fee_ratio=Decimal("0.02"),
        service_fee=20_000,
        admin_fee=30_000,
    )
    with_financed_fee = safe_principal_for_terms(
        maximum_safe_instalment=100_000,
        tenor_months=6,
        nominal_annual_rate=Decimal("0"),
        amortization_method=AmortizationEnum.FLAT,
        upfront_fee_ratio=Decimal("0.02"),
        financed_fee=60_000,
        service_fee=20_000,
        admin_fee=30_000,
    )

    # Unfinanced fees reduce proceeds but do not enter the repayment schedule.
    # The financed fee consumes schedule capacity, including the final-payment
    # whole-IDR remainder enforced by the complete-schedule boundary.
    assert without_financed_fee == 600_000
    assert with_financed_fee == 539_995


def test_safe_principal_zero_capacity_or_fee_only_over_capacity_is_zero() -> None:
    assert (
        safe_principal_for_terms(
            maximum_safe_instalment=0,
            tenor_months=12,
            nominal_annual_rate=Decimal("0.24"),
            amortization_method=AmortizationEnum.FLAT,
        )
        == 0
    )
    assert (
        safe_principal_for_terms(
            maximum_safe_instalment=5_000,
            tenor_months=6,
            nominal_annual_rate=Decimal("0"),
            amortization_method=AmortizationEnum.FLAT,
            financed_fee=60_000,
        )
        == 0
    )


def test_effective_reference_rate_matches_same_tenor_flat_offer() -> None:
    offer = compute(
        principal_amount=1_000_000,
        tenor_months=9,
        nominal_annual_rate=Decimal("0.24"),
        upfront_fee=0,
        amortization_method=AmortizationEnum.FLAT,
    )

    assert (
        effective_annual_reference_rate(
            principal_amount=1_000_000,
            tenor_months=9,
            annual_flat_rate=Decimal("0.24"),
        )
        == offer.effective_annual_rate
    )
