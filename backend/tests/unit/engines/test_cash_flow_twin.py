"""`CashFlowTwinEngine` golden tests (PLAN §5.1, §15.1, FR-7; §21.1 gate
tests, §24.8 "engines >= 90% coverage")."""

import uuid
from datetime import date
from decimal import Decimal

from app.engines.cash_flow_twin import DEFAULT_CONFIG, TwinTransactionInput, run
from app.models.enums import (
    CashEventEnum,
    CategoryEnum,
    CoverageEnum,
    DirEnum,
    TransactionContextEnum,
)


def _row(
    *,
    day: date,
    amount: int,
    direction: DirEnum,
    category: CategoryEnum,
    context: TransactionContextEnum = TransactionContextEnum.PERSONAL,
    subcategory: str | None = None,
    merchant: str = "MERCHANT",
    balance_after: int | None = None,
    is_internal: bool = False,
) -> TwinTransactionInput:
    return TwinTransactionInput(
        transaction_id=uuid.uuid4(),
        transaction_date=day,
        amount=amount,
        direction=direction,
        category=category,
        transaction_context=context,
        subcategory=subcategory,
        normalized_merchant=merchant,
        is_internal_transfer=is_internal,
        balance_after=balance_after,
    )


def _six_month_salary_rows() -> list[TwinTransactionInput]:
    rows = []
    for month in range(1, 7):
        rows.append(
            _row(
                day=date(2026, month, 25),
                amount=3_000_000,
                direction=DirEnum.CREDIT,
                category=CategoryEnum.INCOME,
                subcategory="SALARY",
                merchant="GAJI PT MAJU",
                balance_after=5_000_000 + month * 100_000,
            )
        )
        rows.append(
            _row(
                day=date(2026, month, 28),
                amount=2_000_000,
                direction=DirEnum.DEBIT,
                category=CategoryEnum.ESSENTIAL_EXPENSE,
                merchant="LISTRIK PLN",
                balance_after=3_000_000 + month * 100_000,
            )
        )
    return rows


def test_sufficient_coverage_with_six_months() -> None:
    result = run(_six_month_salary_rows())

    assert result.months_covered == 6
    assert result.coverage_flag is CoverageEnum.SUFFICIENT
    assert result.median_income == 3_000_000
    assert result.essential_expenses == 2_000_000
    assert result.average_free_cash_flow == 1_000_000
    assert len(result.monthly_snapshots) == 6


def test_low_coverage_flagged_below_two_months() -> None:
    """FR-7 EC: "<2 months of data -> Twin flagged LOW_COVERAGE"."""
    rows = [
        _row(
            day=date(2026, 6, 5),
            amount=1_000_000,
            direction=DirEnum.CREDIT,
            category=CategoryEnum.INCOME,
        )
    ]
    result = run(rows)

    assert result.months_covered == 1
    assert result.coverage_flag is CoverageEnum.LOW_COVERAGE
    assert any(r.code == "TWIN_LOW_COVERAGE" for r in result.reason_codes)


def test_internal_transfers_excluded_from_income_and_expense_aggregates() -> None:
    """FR-6 AC2: internal transfers never inflate income/expense aggregates."""
    rows = [
        _row(
            day=date(2026, 6, 5),
            amount=3_000_000,
            direction=DirEnum.CREDIT,
            category=CategoryEnum.INCOME,
        ),
        _row(
            day=date(2026, 6, 6),
            amount=500_000,
            direction=DirEnum.CREDIT,
            category=CategoryEnum.INTERNAL_TRANSFER,
            is_internal=True,
        ),
        _row(
            day=date(2026, 6, 6),
            amount=500_000,
            direction=DirEnum.DEBIT,
            category=CategoryEnum.INTERNAL_TRANSFER,
            is_internal=True,
        ),
        _row(
            day=date(2026, 7, 5),
            amount=3_000_000,
            direction=DirEnum.CREDIT,
            category=CategoryEnum.INCOME,
        ),
    ]
    result = run(rows)

    assert result.average_income == 3_000_000


def test_business_and_personal_income_split_separately() -> None:
    rows = [
        _row(
            day=date(2026, 6, 5),
            amount=3_000_000,
            direction=DirEnum.CREDIT,
            category=CategoryEnum.INCOME,
            context=TransactionContextEnum.PERSONAL,
            subcategory="SALARY",
        ),
        _row(
            day=date(2026, 6, 10),
            amount=1_500_000,
            direction=DirEnum.CREDIT,
            category=CategoryEnum.INCOME,
            context=TransactionContextEnum.BUSINESS,
            subcategory="QRIS_SETTLEMENT",
        ),
        _row(
            day=date(2026, 7, 5),
            amount=3_000_000,
            direction=DirEnum.CREDIT,
            category=CategoryEnum.INCOME,
            context=TransactionContextEnum.PERSONAL,
            subcategory="SALARY",
        ),
    ]
    result = run(rows)

    june = next(m for m in result.monthly_snapshots if m.year_month == date(2026, 6, 1))
    assert june.personal_income == 3_000_000
    assert june.business_income == 1_500_000


def test_weakest_month_is_the_lowest_net_cash_flow_month() -> None:
    rows = [
        _row(
            day=date(2026, 5, 5),
            amount=3_000_000,
            direction=DirEnum.CREDIT,
            category=CategoryEnum.INCOME,
        ),
        _row(
            day=date(2026, 5, 10),
            amount=500_000,
            direction=DirEnum.DEBIT,
            category=CategoryEnum.ESSENTIAL_EXPENSE,
        ),
        _row(
            day=date(2026, 6, 5),
            amount=3_000_000,
            direction=DirEnum.CREDIT,
            category=CategoryEnum.INCOME,
        ),
        _row(
            day=date(2026, 6, 10),
            amount=2_900_000,
            direction=DirEnum.DEBIT,
            category=CategoryEnum.ESSENTIAL_EXPENSE,
        ),
    ]
    result = run(rows)

    assert result.weakest_month_cash_flow == 100_000


def test_zero_free_cash_flow_reason_code() -> None:
    rows = [
        _row(
            day=date(2026, 6, 5),
            amount=1_000_000,
            direction=DirEnum.CREDIT,
            category=CategoryEnum.INCOME,
        ),
        _row(
            day=date(2026, 6, 10),
            amount=1_000_000,
            direction=DirEnum.DEBIT,
            category=CategoryEnum.ESSENTIAL_EXPENSE,
        ),
    ]
    result = run(rows)

    assert result.average_free_cash_flow == 0
    assert any(r.code == "TWIN_NON_POSITIVE_FREE_CASH_FLOW" for r in result.reason_codes)


def test_income_source_concentration_and_dominant_arrival_day() -> None:
    result = run(_six_month_salary_rows())

    assert len(result.income_sources) == 1
    source = result.income_sources[0]
    assert source.concentration_ratio == Decimal("1.0000")
    assert source.dominant_arrival_day == 25
    assert source.confidence == Decimal("1.0000")


def test_cash_flow_events_include_income_and_essential_expense() -> None:
    result = run(_six_month_salary_rows())

    income_events = [e for e in result.cash_flow_events if e.event_type is CashEventEnum.INCOME]
    expense_events = [
        e for e in result.cash_flow_events if e.event_type is CashEventEnum.ESSENTIAL_EXPENSE
    ]
    assert len(income_events) == 1
    assert income_events[0].expected_day_of_month == 25
    assert len(expense_events) == 1
    assert expense_events[0].expected_day_of_month == 28


def test_first_month_opening_balance_is_reconstructed_not_zero() -> None:
    """The statement's zero-amount anchor row never becomes a `transactions`
    row (extraction only persists `amount > 0` rows), so the first month's
    true opening balance must be reconstructed from the earliest dated row's
    `balance_after`, not defaulted to 0 (which would wrongly zero out
    `minimum_balance` for otherwise-healthy accounts)."""
    rows = [
        _row(
            day=date(2026, 5, 5),
            amount=3_000_000,
            direction=DirEnum.CREDIT,
            category=CategoryEnum.INCOME,
            balance_after=7_000_000,
        ),
        _row(
            day=date(2026, 5, 10),
            amount=300_000,
            direction=DirEnum.DEBIT,
            category=CategoryEnum.ESSENTIAL_EXPENSE,
            balance_after=6_700_000,
        ),
    ]
    result = run(rows)

    may = result.monthly_snapshots[0]
    assert may.opening_balance == 4_000_000
    assert may.minimum_balance == 4_000_000


def test_no_balance_data_defaults_to_zero_without_crashing() -> None:
    rows = [
        _row(
            day=date(2026, 6, 5),
            amount=1_000_000,
            direction=DirEnum.CREDIT,
            category=CategoryEnum.INCOME,
            balance_after=None,
        ),
    ]
    result = run(rows)

    assert result.minimum_balance == 0
    assert result.monthly_snapshots[0].opening_balance == 0


def test_empty_input_produces_zeroed_profile() -> None:
    result = run([])

    assert result.months_covered == 0
    assert result.coverage_flag is CoverageEnum.LOW_COVERAGE
    assert result.average_income == 0
    assert result.income_sources == []
    assert result.cash_flow_events == []


def test_default_config_loads_from_model_config() -> None:
    assert DEFAULT_CONFIG.low_coverage_min_months == 2
