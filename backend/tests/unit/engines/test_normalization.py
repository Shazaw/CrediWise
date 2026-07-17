"""`NormalizationEngine` golden tests (PLAN §5.1, §15.1, FR-6; §21.1 gate
tests, §24.8 "engines >= 90% coverage")."""

import uuid
from datetime import date
from decimal import Decimal

from app.engines.normalization import DEFAULT_CONFIG, NormalizationTransactionInput, run
from app.models.enums import CategoryEnum, DirEnum, RecurringTypeEnum, TransactionContextEnum

_ACCOUNT_A = uuid.uuid4()
_ACCOUNT_B = uuid.uuid4()


def _row(
    *,
    account: uuid.UUID = _ACCOUNT_A,
    day: date,
    amount: int,
    direction: DirEnum,
    description: str,
) -> NormalizationTransactionInput:
    return NormalizationTransactionInput(
        transaction_id=uuid.uuid4(),
        financial_account_id=account,
        transaction_date=day,
        amount=amount,
        direction=direction,
        raw_description=description,
    )


def test_salary_credit_categorized_as_personal_income() -> None:
    row = _row(
        day=date(2026, 6, 5),
        amount=3_000_000,
        direction=DirEnum.CREDIT,
        description="TRSF GAJI JUNI",
    )
    result = run([row])

    update = result.updates[0]
    assert update.category is CategoryEnum.INCOME
    assert update.transaction_context is TransactionContextEnum.PERSONAL
    assert update.subcategory == "SALARY"
    assert update.category_confidence == Decimal("1.0")


def test_qris_direction_sensitive_categorization() -> None:
    credit = _row(
        day=date(2026, 6, 1),
        amount=50_000,
        direction=DirEnum.CREDIT,
        description="QRIS MERCHANT SETTLE",
    )
    debit = _row(
        day=date(2026, 6, 2),
        amount=20_000,
        direction=DirEnum.DEBIT,
        description="QRIS MERCHANT PAY",
    )
    result = run([credit, debit])

    by_id = {u.transaction_id: u for u in result.updates}
    assert by_id[credit.transaction_id].category is CategoryEnum.INCOME
    assert by_id[credit.transaction_id].transaction_context is TransactionContextEnum.BUSINESS
    assert by_id[debit.transaction_id].category is CategoryEnum.DISCRETIONARY
    assert by_id[debit.transaction_id].transaction_context is TransactionContextEnum.PERSONAL


def test_unmatched_description_stays_unknown_never_guessed_as_income() -> None:
    """FR-6 EC: ambiguous category/context -> UNKNOWN, never guessed as income."""
    row = _row(
        day=date(2026, 6, 5), amount=123_456, direction=DirEnum.CREDIT, description="XYZ 998211"
    )
    result = run([row])

    update = result.updates[0]
    assert update.category is CategoryEnum.UNKNOWN
    assert update.transaction_context is TransactionContextEnum.UNKNOWN
    assert update.category_confidence == Decimal("0.0")


def test_internal_transfer_detected_across_accounts_same_amount_close_dates() -> None:
    debit = _row(
        account=_ACCOUNT_A,
        day=date(2026, 6, 10),
        amount=500_000,
        direction=DirEnum.DEBIT,
        description="TRANSFER KE TOKOPEDIA TOPUP",
    )
    credit = _row(
        account=_ACCOUNT_B,
        day=date(2026, 6, 10),
        amount=500_000,
        direction=DirEnum.CREDIT,
        description="TRANSFER DARI BANK TOPUP",
    )
    result = run([debit, credit])

    by_id = {u.transaction_id: u for u in result.updates}
    assert by_id[debit.transaction_id].is_internal_transfer is True
    assert by_id[credit.transaction_id].is_internal_transfer is True
    assert by_id[debit.transaction_id].category is CategoryEnum.INTERNAL_TRANSFER
    assert by_id[credit.transaction_id].category is CategoryEnum.INTERNAL_TRANSFER
    assert any(r.code == "NORMALIZATION_INTERNAL_TRANSFERS_DETECTED" for r in result.reason_codes)


def test_internal_transfer_not_detected_on_same_account() -> None:
    """A debit and credit on the *same* account is not a transfer between
    the user's accounts -- it's just two ordinary transactions."""
    debit = _row(
        account=_ACCOUNT_A,
        day=date(2026, 6, 10),
        amount=500_000,
        direction=DirEnum.DEBIT,
        description="A",
    )
    credit = _row(
        account=_ACCOUNT_A,
        day=date(2026, 6, 10),
        amount=500_000,
        direction=DirEnum.CREDIT,
        description="B",
    )
    result = run([debit, credit])

    assert all(not u.is_internal_transfer for u in result.updates)


def test_internal_transfer_not_detected_outside_date_window() -> None:
    debit = _row(
        account=_ACCOUNT_A,
        day=date(2026, 6, 1),
        amount=500_000,
        direction=DirEnum.DEBIT,
        description="A",
    )
    credit = _row(
        account=_ACCOUNT_B,
        day=date(2026, 6, 10),
        amount=500_000,
        direction=DirEnum.CREDIT,
        description="B",
    )
    result = run([debit, credit])

    assert all(not u.is_internal_transfer for u in result.updates)


def test_recurring_series_detected_for_regular_monthly_salary() -> None:
    rows = [
        _row(
            day=date(2026, 4, 25),
            amount=3_000_000,
            direction=DirEnum.CREDIT,
            description="GAJI PT MAJU",
        ),
        _row(
            day=date(2026, 5, 25),
            amount=3_000_000,
            direction=DirEnum.CREDIT,
            description="GAJI PT MAJU",
        ),
        _row(
            day=date(2026, 6, 25),
            amount=3_050_000,
            direction=DirEnum.CREDIT,
            description="GAJI PT MAJU",
        ),
    ]
    result = run(rows)

    assert len(result.recurring_series) == 1
    series = result.recurring_series[0]
    assert series.series_type is RecurringTypeEnum.INCOME
    assert series.median_amount == 3_000_000
    assert series.expected_day_of_month == 25
    assert all(u.is_recurring for u in result.updates)


def test_recurring_not_detected_below_min_occurrences() -> None:
    rows = [
        _row(
            day=date(2026, 5, 25),
            amount=3_000_000,
            direction=DirEnum.CREDIT,
            description="GAJI PT MAJU",
        ),
        _row(
            day=date(2026, 6, 25),
            amount=3_000_000,
            direction=DirEnum.CREDIT,
            description="GAJI PT MAJU",
        ),
    ]
    result = run(rows)

    assert result.recurring_series == []
    assert all(not u.is_recurring for u in result.updates)


def test_recurring_not_detected_when_amount_varies_too_much() -> None:
    rows = [
        _row(
            day=date(2026, 4, 25),
            amount=1_000_000,
            direction=DirEnum.CREDIT,
            description="GAJI PT MAJU",
        ),
        _row(
            day=date(2026, 5, 25),
            amount=2_500_000,
            direction=DirEnum.CREDIT,
            description="GAJI PT MAJU",
        ),
        _row(
            day=date(2026, 6, 25),
            amount=3_000_000,
            direction=DirEnum.CREDIT,
            description="GAJI PT MAJU",
        ),
    ]
    result = run(rows)

    assert result.recurring_series == []


def test_recurring_debt_service_detected_as_debt_payment_series() -> None:
    rows = [
        _row(
            day=date(2026, 4, 15),
            amount=500_000,
            direction=DirEnum.DEBIT,
            description="CICILAN KREDITPLUS",
        ),
        _row(
            day=date(2026, 5, 15),
            amount=500_000,
            direction=DirEnum.DEBIT,
            description="CICILAN KREDITPLUS",
        ),
        _row(
            day=date(2026, 6, 15),
            amount=500_000,
            direction=DirEnum.DEBIT,
            description="CICILAN KREDITPLUS",
        ),
    ]
    result = run(rows)

    assert len(result.recurring_series) == 1
    assert result.recurring_series[0].series_type is RecurringTypeEnum.DEBT_PAYMENT


def test_merchant_normalization_strips_reference_numbers_and_punctuation() -> None:
    row = _row(
        day=date(2026, 6, 5),
        amount=50_000,
        direction=DirEnum.DEBIT,
        description="QRIS-MERCHANT/998211 #4021",
    )
    result = run([row])

    assert result.updates[0].normalized_merchant == "QRIS MERCHANT"


def test_default_config_loads_from_model_config() -> None:
    assert DEFAULT_CONFIG.recurring_min_occurrences == 3
    assert DEFAULT_CONFIG.internal_transfer_date_window_days == 1


def test_empty_input_returns_no_updates() -> None:
    result = run([])

    assert result.updates == []
    assert result.recurring_series == []
