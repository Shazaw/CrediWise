"""`CashFlowTwinEngine` — Cash-Flow Digital Twin (PLAN §5.1, §15.1; FR-7).

Pure per PLAN §10.1: no DB, network, filesystem, clock, or RNG. Consumes
already-normalized, already-categorized transactions (`NormalizationEngine`'s
output, mapped by the service layer) for a single assessment's document set.
Internal transfers are excluded from every income/expense aggregate (FR-6
AC2) before this engine ever sees a difference between "transfer" and
"real" cash flow -- callers are expected to have already stamped
`category=INTERNAL_TRANSFER`, but this engine defensively re-excludes any
row still flagged `is_internal_transfer=True` regardless of category, since
that flag is the authoritative signal (PLAN §11.3 `transactions` note).

`generated_at` is stamped by the service layer, not here (Golden Rule 3:
engines never read the clock).
"""

import statistics
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.engines.config import model_config as cfg
from app.models.enums import (
    CashEventEnum,
    CategoryEnum,
    CoverageEnum,
    DirEnum,
    FreqEnum,
    IncomeSourceEnum,
    TransactionContextEnum,
)

_RATIO_Q = Decimal("0.0001")


@dataclass(frozen=True)
class TwinTransactionInput:
    transaction_id: uuid.UUID
    transaction_date: date
    amount: int
    direction: DirEnum
    category: CategoryEnum
    transaction_context: TransactionContextEnum
    subcategory: str | None
    normalized_merchant: str
    is_internal_transfer: bool
    balance_after: int | None


@dataclass(frozen=True)
class ReasonCode:
    code: str
    description: str


@dataclass(frozen=True)
class CashFlowTwinConfig:
    low_coverage_min_months: int


@dataclass(frozen=True)
class MonthlySnapshotResult:
    year_month: date
    personal_income: int
    business_income: int
    essential_expenses: int
    discretionary_expenses: int
    business_expenses: int
    debt_service: int
    opening_balance: int
    minimum_balance: int
    closing_balance: int
    net_cash_flow: int


@dataclass(frozen=True)
class IncomeSourceResult:
    source_name: str
    source_type: IncomeSourceEnum
    average_amount: int
    frequency: FreqEnum
    volatility: Decimal
    concentration_ratio: Decimal
    dominant_arrival_day: int | None
    confidence: Decimal


@dataclass(frozen=True)
class CashFlowEventResult:
    expected_day_of_month: int | None
    amount: int
    direction: DirEnum
    event_type: CashEventEnum
    confidence: Decimal


@dataclass(frozen=True)
class FinancialProfileResult:
    average_income: int
    median_income: int
    income_volatility: Decimal
    essential_expenses: int
    discretionary_expenses: int
    existing_debt: int
    average_free_cash_flow: int
    minimum_balance: int
    positive_cash_flow_ratio: Decimal
    weakest_month_cash_flow: int
    savings_buffer: int
    months_covered: int
    coverage_flag: CoverageEnum
    monthly_snapshots: list[MonthlySnapshotResult] = field(default_factory=list)
    income_sources: list[IncomeSourceResult] = field(default_factory=list)
    cash_flow_events: list[CashFlowEventResult] = field(default_factory=list)
    reason_codes: list[ReasonCode] = field(default_factory=list)


def default_config() -> CashFlowTwinConfig:
    raw = cfg.CONFIG["cash_flow_twin"]
    assert isinstance(raw, dict)  # noqa: S101 - internal invariant, not user input
    return CashFlowTwinConfig(low_coverage_min_months=raw["low_coverage_min_months"])


DEFAULT_CONFIG = default_config()


def run(
    rows: list[TwinTransactionInput], config: CashFlowTwinConfig = DEFAULT_CONFIG
) -> FinancialProfileResult:
    active = [r for r in rows if not r.is_internal_transfer]
    monthly_snapshots = _build_monthly_snapshots(active)

    total_incomes = [m.personal_income + m.business_income for m in monthly_snapshots]
    average_income = round(statistics.fmean(total_incomes)) if total_incomes else 0
    median_income = int(statistics.median(total_incomes)) if total_incomes else 0
    income_volatility = _coefficient_of_variation(total_incomes)

    essential_expenses = _mean_int(m.essential_expenses for m in monthly_snapshots)
    discretionary_expenses = _mean_int(m.discretionary_expenses for m in monthly_snapshots)
    existing_debt = _mean_int(m.debt_service for m in monthly_snapshots)
    net_cash_flows = [m.net_cash_flow for m in monthly_snapshots]
    average_free_cash_flow = round(statistics.fmean(net_cash_flows)) if net_cash_flows else 0
    minimum_balance = min((m.minimum_balance for m in monthly_snapshots), default=0)
    positive_months = sum(1 for v in net_cash_flows if v > 0)
    positive_cash_flow_ratio = (
        (Decimal(positive_months) / Decimal(len(net_cash_flows))).quantize(
            _RATIO_Q, rounding=ROUND_HALF_UP
        )
        if net_cash_flows
        else Decimal(0)
    )
    weakest_month_cash_flow = min(net_cash_flows, default=0)
    savings_buffer = max(0, minimum_balance)
    months_covered = len(monthly_snapshots)
    coverage_flag = (
        CoverageEnum.LOW_COVERAGE
        if months_covered < config.low_coverage_min_months
        else CoverageEnum.SUFFICIENT
    )

    income_sources = _build_income_sources(active)
    cash_flow_events = _build_cash_flow_events(active, income_sources)

    reason_codes = [
        ReasonCode(
            code="TWIN_MONTHS_COVERED", description=f"Twin covers {months_covered} month(s) of data"
        )
    ]
    if coverage_flag is CoverageEnum.LOW_COVERAGE:
        reason_codes.append(
            ReasonCode(
                code="TWIN_LOW_COVERAGE",
                description=(
                    f"Fewer than {config.low_coverage_min_months} months of data reduce "
                    "downstream model confidence"
                ),
            )
        )
    if average_free_cash_flow <= 0:
        reason_codes.append(
            ReasonCode(
                code="TWIN_NON_POSITIVE_FREE_CASH_FLOW",
                description="Average free cash flow is zero or negative",
            )
        )

    return FinancialProfileResult(
        average_income=average_income,
        median_income=median_income,
        income_volatility=income_volatility,
        essential_expenses=essential_expenses,
        discretionary_expenses=discretionary_expenses,
        existing_debt=existing_debt,
        average_free_cash_flow=average_free_cash_flow,
        minimum_balance=minimum_balance,
        positive_cash_flow_ratio=positive_cash_flow_ratio,
        weakest_month_cash_flow=weakest_month_cash_flow,
        savings_buffer=savings_buffer,
        months_covered=months_covered,
        coverage_flag=coverage_flag,
        monthly_snapshots=monthly_snapshots,
        income_sources=income_sources,
        cash_flow_events=cash_flow_events,
        reason_codes=reason_codes,
    )


def _month_key(d: date) -> date:
    return date(d.year, d.month, 1)


def _reconstruct_pre_period_balance(rows: list[TwinTransactionInput]) -> int:
    """The statement's zero-amount opening-balance anchor row never becomes
    a `transactions` row (extraction only persists `amount > 0` rows -- see
    `app/services/extraction_service.py`'s module docstring), so the first
    covered month's true opening balance isn't directly available here.
    Reconstruct it the same way Trust-Layer balance reconstruction does:
    `Previous = balance_after - signed(amount)` on the earliest dated row
    with balance data, so `minimum_balance`/`TemporalLiquidityCapacity`
    (§5.6) aren't penalised by an artificial `0` starting balance."""
    dated = sorted(
        (r for r in rows if r.balance_after is not None), key=lambda r: r.transaction_date
    )
    if not dated:
        return 0
    earliest = dated[0]
    signed_amount = earliest.amount if earliest.direction is DirEnum.CREDIT else -earliest.amount
    assert earliest.balance_after is not None  # noqa: S101 - filtered by the generator above
    return earliest.balance_after - signed_amount


def _build_monthly_snapshots(rows: list[TwinTransactionInput]) -> list[MonthlySnapshotResult]:
    by_month: dict[date, list[TwinTransactionInput]] = {}
    for row in rows:
        by_month.setdefault(_month_key(row.transaction_date), []).append(row)

    has_balance_data = any(r.balance_after is not None for r in rows)
    snapshots: list[MonthlySnapshotResult] = []
    running_opening = _reconstruct_pre_period_balance(rows) if has_balance_data else 0
    for year_month in sorted(by_month):
        members = sorted(by_month[year_month], key=lambda r: r.transaction_date)

        personal_income = _sum(
            members,
            direction=DirEnum.CREDIT,
            category=CategoryEnum.INCOME,
            context=TransactionContextEnum.PERSONAL,
        )
        business_income = _sum_any_context(
            members,
            direction=DirEnum.CREDIT,
            category=CategoryEnum.INCOME,
            contexts=(TransactionContextEnum.BUSINESS, TransactionContextEnum.MIXED),
        )
        essential_expenses = _sum(
            members,
            direction=DirEnum.DEBIT,
            category=CategoryEnum.ESSENTIAL_EXPENSE,
            context=TransactionContextEnum.PERSONAL,
        )
        business_expenses = _sum(
            members,
            direction=DirEnum.DEBIT,
            category=CategoryEnum.ESSENTIAL_EXPENSE,
            context=TransactionContextEnum.BUSINESS,
        )
        discretionary_expenses = _sum_any_context(
            members,
            direction=DirEnum.DEBIT,
            category=CategoryEnum.DISCRETIONARY,
            contexts=tuple(TransactionContextEnum),
        )
        debt_service = _sum_any_context(
            members,
            direction=DirEnum.DEBIT,
            category=CategoryEnum.FINANCIAL_OBLIGATION,
            contexts=tuple(TransactionContextEnum),
        )
        net_cash_flow = (
            personal_income
            + business_income
            - essential_expenses
            - discretionary_expenses
            - business_expenses
            - debt_service
        )

        if has_balance_data:
            balances = [m.balance_after for m in members if m.balance_after is not None]
            opening_balance = running_opening
            minimum_balance = min([opening_balance, *balances]) if balances else opening_balance
            closing_balance = balances[-1] if balances else opening_balance
            running_opening = closing_balance
        else:
            opening_balance = 0
            minimum_balance = 0
            closing_balance = 0

        snapshots.append(
            MonthlySnapshotResult(
                year_month=year_month,
                personal_income=personal_income,
                business_income=business_income,
                essential_expenses=essential_expenses,
                discretionary_expenses=discretionary_expenses,
                business_expenses=business_expenses,
                debt_service=debt_service,
                opening_balance=opening_balance,
                minimum_balance=minimum_balance,
                closing_balance=closing_balance,
                net_cash_flow=net_cash_flow,
            )
        )
    return snapshots


def _sum(
    rows: list[TwinTransactionInput],
    *,
    direction: DirEnum,
    category: CategoryEnum,
    context: TransactionContextEnum,
) -> int:
    return sum(
        r.amount
        for r in rows
        if r.direction is direction and r.category is category and r.transaction_context is context
    )


def _sum_any_context(
    rows: list[TwinTransactionInput],
    *,
    direction: DirEnum,
    category: CategoryEnum,
    contexts: tuple[TransactionContextEnum, ...],
) -> int:
    return sum(
        r.amount
        for r in rows
        if r.direction is direction and r.category is category and r.transaction_context in contexts
    )


def _mean_int(values: Iterable[int]) -> int:
    values_list = list(values)
    return round(statistics.fmean(values_list)) if values_list else 0


def _coefficient_of_variation(values: list[int]) -> Decimal:
    if len(values) < 2:
        return Decimal(0)
    mean = statistics.fmean(values)
    if mean <= 0:
        return Decimal(0)
    stdev = statistics.pstdev(values)
    return (Decimal(str(stdev)) / Decimal(str(mean))).quantize(_RATIO_Q, rounding=ROUND_HALF_UP)


_SOURCE_TYPE_BY_SUBCATEGORY: dict[str, IncomeSourceEnum] = {
    "SALARY": IncomeSourceEnum.SALARY,
    "QRIS_SETTLEMENT": IncomeSourceEnum.QRIS_SETTLEMENT,
    "MARKETPLACE_SETTLEMENT": IncomeSourceEnum.MARKETPLACE_SETTLEMENT,
}


def _build_income_sources(rows: list[TwinTransactionInput]) -> list[IncomeSourceResult]:
    income_rows = [
        r for r in rows if r.direction is DirEnum.CREDIT and r.category is CategoryEnum.INCOME
    ]
    if not income_rows:
        return []

    by_merchant: dict[str, list[TwinTransactionInput]] = {}
    for row in income_rows:
        by_merchant.setdefault(row.normalized_merchant, []).append(row)

    total_income = sum(r.amount for r in income_rows)
    sources: list[IncomeSourceResult] = []
    for merchant, members in by_merchant.items():
        ordered = sorted(members, key=lambda r: r.transaction_date)
        amounts = [m.amount for m in ordered]
        average_amount = round(statistics.fmean(amounts))
        volatility = _coefficient_of_variation(amounts)
        concentration_ratio = (
            (Decimal(sum(amounts)) / Decimal(total_income)).quantize(
                _RATIO_Q, rounding=ROUND_HALF_UP
            )
            if total_income
            else Decimal(0)
        )
        frequency, dominant_day = _infer_frequency(ordered)
        confidence = min(Decimal(1), Decimal(len(ordered)) / Decimal(3)).quantize(
            _RATIO_Q, rounding=ROUND_HALF_UP
        )
        source_type = _SOURCE_TYPE_BY_SUBCATEGORY.get(ordered[0].subcategory or "", None)
        if source_type is None:
            source_type = (
                IncomeSourceEnum.BUSINESS_REVENUE
                if ordered[0].transaction_context is TransactionContextEnum.BUSINESS
                else IncomeSourceEnum.OTHER
            )

        sources.append(
            IncomeSourceResult(
                source_name=merchant,
                source_type=source_type,
                average_amount=average_amount,
                frequency=frequency,
                volatility=volatility,
                concentration_ratio=concentration_ratio,
                dominant_arrival_day=dominant_day,
                confidence=confidence,
            )
        )
    return sorted(sources, key=lambda s: s.concentration_ratio, reverse=True)


def _infer_frequency(ordered: list[TwinTransactionInput]) -> tuple[FreqEnum, int | None]:
    if len(ordered) < 2:
        return FreqEnum.MONTHLY, ordered[0].transaction_date.day if ordered else None

    intervals = [
        (b.transaction_date - a.transaction_date).days
        for a, b in zip(ordered, ordered[1:], strict=False)
    ]
    mean_interval = statistics.fmean(intervals)
    if mean_interval <= 10:
        frequency = FreqEnum.WEEKLY
    elif mean_interval <= 20:
        frequency = FreqEnum.BIWEEKLY
    else:
        frequency = FreqEnum.MONTHLY

    dominant_day = (
        statistics.mode([m.transaction_date.day for m in ordered])
        if frequency is FreqEnum.MONTHLY
        else None
    )
    return frequency, dominant_day


def _build_cash_flow_events(
    rows: list[TwinTransactionInput], income_sources: list[IncomeSourceResult]
) -> list[CashFlowEventResult]:
    events: list[CashFlowEventResult] = [
        CashFlowEventResult(
            expected_day_of_month=source.dominant_arrival_day,
            amount=source.average_amount,
            direction=DirEnum.CREDIT,
            event_type=CashEventEnum.INCOME,
            confidence=source.confidence,
        )
        for source in income_sources
        if source.dominant_arrival_day is not None
    ]

    essential_rows = [
        r
        for r in rows
        if r.direction is DirEnum.DEBIT
        and r.category is CategoryEnum.ESSENTIAL_EXPENSE
        and r.transaction_context is TransactionContextEnum.PERSONAL
    ]
    by_merchant: dict[str, list[TwinTransactionInput]] = {}
    for row in essential_rows:
        by_merchant.setdefault(row.normalized_merchant, []).append(row)
    for members in by_merchant.values():
        if len(members) < 2:
            continue
        ordered = sorted(members, key=lambda r: r.transaction_date)
        events.append(
            CashFlowEventResult(
                expected_day_of_month=statistics.mode([m.transaction_date.day for m in ordered]),
                amount=round(statistics.fmean(m.amount for m in ordered)),
                direction=DirEnum.DEBIT,
                event_type=CashEventEnum.ESSENTIAL_EXPENSE,
                confidence=min(Decimal(1), Decimal(len(ordered)) / Decimal(3)).quantize(
                    _RATIO_Q, rounding=ROUND_HALF_UP
                ),
            )
        )
    return events
