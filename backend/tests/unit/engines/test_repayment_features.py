from decimal import Decimal

from app.engines.repayment_features import (
    FEATURE_ORDER,
    RepaymentFeatureInput,
    RepaymentMonthlyInput,
    build,
)


def test_repayment_features_are_ordered_hashed_and_deterministic() -> None:
    inputs = RepaymentFeatureInput(
        months_covered=2,
        median_income=3_000_000,
        income_volatility=Decimal("0.1000"),
        positive_cash_flow_ratio=Decimal("0.5000"),
        existing_debt=300_000,
        average_free_cash_flow=600_000,
        weakest_month_cash_flow=-150_000,
        minimum_balance=-100_000,
        savings_buffer=0,
        monthly_snapshots=(
            RepaymentMonthlyInput(
                minimum_balance=-100_000,
                closing_balance=400_000,
                net_cash_flow=-150_000,
            ),
            RepaymentMonthlyInput(
                minimum_balance=200_000,
                closing_balance=1_000_000,
                net_cash_flow=1_350_000,
            ),
        ),
    )

    first = build(inputs)
    second = build(inputs)

    assert tuple(first.values) == FEATURE_ORDER
    assert first == second
    assert first.values["debt_service_ratio"] == Decimal("0.100000")
    assert first.values["negative_balance_month_ratio"] == Decimal("0.500000")
    assert first.values["monthly_balance_trend_ratio"] == Decimal("0.200000")
    assert len(first.feature_hash) == 64


def test_repayment_features_handle_zero_income_without_non_finite_values() -> None:
    result = build(
        RepaymentFeatureInput(
            months_covered=0,
            median_income=0,
            income_volatility=Decimal(0),
            positive_cash_flow_ratio=Decimal(0),
            existing_debt=0,
            average_free_cash_flow=-100,
            weakest_month_cash_flow=-100,
            minimum_balance=-100,
            savings_buffer=0,
            monthly_snapshots=(),
        )
    )

    assert all(value.is_finite() for value in result.values.values())
    assert all(value == 0 for value in result.values.values())
