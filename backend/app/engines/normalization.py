"""`NormalizationEngine` — categorization, context, internal-transfer, and
recurring detection (PLAN §5.1 rule inventory, §15.1; FR-6).

Pure per PLAN §10.1: no DB, network, filesystem, clock, or RNG. Takes the
full set of a user's transactions the service layer decides are in scope
(`normalization_service.run_normalization` passes every active transaction
across the user's financial accounts, not just the triggering document's
rows) so internal-transfer and recurring detection see the whole,
multi-account picture FR-6 AC5 requires. Re-running with an unchanged input
set is idempotent (NFR-3) — this engine only *derives* fields
(`category`/`transaction_context`/`is_internal_transfer`/`is_recurring`/
`normalized_merchant`), it never touches raw evidence (PLAN §6.4,
`app/models/transaction.py`'s docstring).
"""

import re
import statistics
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.engines.config import model_config as cfg
from app.models.enums import CategoryEnum, DirEnum, RecurringTypeEnum, TransactionContextEnum

_REFERENCE_NUMBER_RE = re.compile(r"\d{2,}")
_NON_ALPHA_RE = re.compile(r"[^A-Za-z\s]")
_WHITESPACE_RE = re.compile(r"\s+")

_MATCHED_CONFIDENCE = Decimal("1.0")
_UNMATCHED_CONFIDENCE = Decimal("0.0")


@dataclass(frozen=True)
class NormalizationTransactionInput:
    transaction_id: uuid.UUID
    financial_account_id: uuid.UUID
    transaction_date: date
    amount: int
    direction: DirEnum
    raw_description: str


@dataclass(frozen=True)
class ReasonCode:
    code: str
    description: str


@dataclass(frozen=True)
class NormalizationConfig:
    category_rules: list[dict[str, object]]
    internal_transfer_date_window_days: int
    recurring_min_occurrences: int
    recurring_amount_variance_ratio: Decimal
    recurring_interval_stddev_days_max: int


@dataclass(frozen=True)
class TransactionUpdate:
    transaction_id: uuid.UUID
    category: CategoryEnum
    subcategory: str | None
    transaction_context: TransactionContextEnum
    normalized_merchant: str
    is_internal_transfer: bool
    is_recurring: bool
    category_confidence: Decimal


@dataclass(frozen=True)
class DetectedRecurringSeries:
    financial_account_id: uuid.UUID
    series_type: RecurringTypeEnum
    normalized_counterparty: str
    median_amount: int
    expected_interval_days: int
    expected_day_of_month: int | None
    regularity_score: Decimal
    confidence: Decimal
    transaction_ids: list[uuid.UUID] = field(default_factory=list)


@dataclass(frozen=True)
class NormalizationResult:
    updates: list[TransactionUpdate]
    recurring_series: list[DetectedRecurringSeries]
    reason_codes: list[ReasonCode] = field(default_factory=list)


def default_config() -> NormalizationConfig:
    raw = cfg.CONFIG["normalization"]
    assert isinstance(raw, dict)  # noqa: S101 - internal invariant, not user input
    return NormalizationConfig(
        category_rules=raw["category_rules"],
        internal_transfer_date_window_days=raw["internal_transfer"]["date_window_days"],
        recurring_min_occurrences=raw["recurring"]["min_occurrences"],
        recurring_amount_variance_ratio=raw["recurring"]["amount_variance_ratio"],
        recurring_interval_stddev_days_max=raw["recurring"]["interval_stddev_days_max"],
    )


DEFAULT_CONFIG = default_config()


def run(
    rows: list[NormalizationTransactionInput], config: NormalizationConfig = DEFAULT_CONFIG
) -> NormalizationResult:
    categorized = {row.transaction_id: _categorize(row, config) for row in rows}

    internal_transfer_ids = _detect_internal_transfers(rows, config)

    recurring_series = _detect_recurring(rows, categorized, config)
    recurring_ids = {tx_id for series in recurring_series for tx_id in series.transaction_ids}

    updates: list[TransactionUpdate] = []
    for row in rows:
        category, context, subcategory, confidence = categorized[row.transaction_id]
        is_internal = row.transaction_id in internal_transfer_ids
        updates.append(
            TransactionUpdate(
                transaction_id=row.transaction_id,
                category=CategoryEnum.INTERNAL_TRANSFER if is_internal else category,
                subcategory=subcategory,
                transaction_context=context,
                normalized_merchant=_normalize_merchant(row.raw_description),
                is_internal_transfer=is_internal,
                is_recurring=row.transaction_id in recurring_ids,
                category_confidence=confidence,
            )
        )

    reason_codes = [
        ReasonCode(
            code="NORMALIZATION_CATEGORIZED",
            description=f"Categorized {len(updates)} transaction(s)",
        )
    ]
    if internal_transfer_ids:
        reason_codes.append(
            ReasonCode(
                code="NORMALIZATION_INTERNAL_TRANSFERS_DETECTED",
                description=(
                    f"Detected {len(internal_transfer_ids) // 2} internal-transfer pair(s), "
                    "excluded from income/expense aggregates"
                ),
            )
        )
    if recurring_series:
        reason_codes.append(
            ReasonCode(
                code="NORMALIZATION_RECURRING_SERIES_DETECTED",
                description=f"Detected {len(recurring_series)} recurring series",
            )
        )

    return NormalizationResult(
        updates=updates, recurring_series=recurring_series, reason_codes=reason_codes
    )


def _categorize(
    row: NormalizationTransactionInput, config: NormalizationConfig
) -> tuple[CategoryEnum, TransactionContextEnum, str | None, Decimal]:
    description = row.raw_description.upper()
    for rule in config.category_rules:
        keywords = rule["keywords"]
        assert isinstance(keywords, tuple)  # noqa: S101 - internal invariant, not user input
        rule_direction = rule.get("direction")
        if rule_direction is not None and rule_direction != row.direction.value:
            continue
        if any(keyword in description for keyword in keywords):
            return (
                CategoryEnum(str(rule["category"])),
                TransactionContextEnum(str(rule["context"])),
                str(rule["subcategory"]) if rule.get("subcategory") else None,
                _MATCHED_CONFIDENCE,
            )
    return CategoryEnum.UNKNOWN, TransactionContextEnum.UNKNOWN, None, _UNMATCHED_CONFIDENCE


def _normalize_merchant(raw_description: str) -> str:
    text = _REFERENCE_NUMBER_RE.sub(" ", raw_description)
    text = _NON_ALPHA_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip().upper()
    return text or raw_description.strip().upper()


def _detect_internal_transfers(
    rows: list[NormalizationTransactionInput], config: NormalizationConfig
) -> set[uuid.UUID]:
    """FR-6 AC2/AC5: a CREDIT and a DEBIT of equal amount on *different*
    accounts, close in time, are treated as the same money moving between
    the user's own accounts rather than as income and an expense."""
    window = config.internal_transfer_date_window_days
    ordered = sorted(rows, key=lambda r: (r.transaction_date, r.amount, str(r.transaction_id)))
    debits = [r for r in ordered if r.direction is DirEnum.DEBIT]
    credits = [r for r in ordered if r.direction is DirEnum.CREDIT]
    matched_credit_ids: set[uuid.UUID] = set()
    internal_ids: set[uuid.UUID] = set()

    for debit in debits:
        for credit in credits:
            if credit.transaction_id in matched_credit_ids:
                continue
            if credit.financial_account_id == debit.financial_account_id:
                continue
            if credit.amount != debit.amount:
                continue
            if abs((credit.transaction_date - debit.transaction_date).days) > window:
                continue
            matched_credit_ids.add(credit.transaction_id)
            internal_ids.add(debit.transaction_id)
            internal_ids.add(credit.transaction_id)
            break

    return internal_ids


def _detect_recurring(
    rows: list[NormalizationTransactionInput],
    categorized: dict[uuid.UUID, tuple[CategoryEnum, TransactionContextEnum, str | None, Decimal]],
    config: NormalizationConfig,
) -> list[DetectedRecurringSeries]:
    groups: dict[tuple[uuid.UUID, str, DirEnum], list[NormalizationTransactionInput]] = {}
    for row in rows:
        key = (row.financial_account_id, _normalize_merchant(row.raw_description), row.direction)
        groups.setdefault(key, []).append(row)

    series: list[DetectedRecurringSeries] = []
    for (account_id, counterparty, direction), members in groups.items():
        if len(members) < config.recurring_min_occurrences:
            continue
        ordered_members = sorted(members, key=lambda r: r.transaction_date)
        amounts = [m.amount for m in ordered_members]
        median_amount = int(statistics.median(amounts))
        if median_amount == 0:
            continue
        variance_ratio = Decimal(max(amounts) - min(amounts)) / Decimal(median_amount)
        if variance_ratio > config.recurring_amount_variance_ratio:
            continue

        intervals = [
            (b.transaction_date - a.transaction_date).days
            for a, b in zip(ordered_members, ordered_members[1:], strict=False)
        ]
        interval_stddev = Decimal(str(statistics.pstdev(intervals))) if len(intervals) > 1 else Decimal(0)
        if interval_stddev > config.recurring_interval_stddev_days_max:
            continue

        mean_interval = round(statistics.fmean(intervals)) if intervals else 0
        day_of_month = _mode_day_of_month(ordered_members) if mean_interval >= 25 else None
        regularity_score = max(
            Decimal(0),
            Decimal(1) - (interval_stddev / Decimal(config.recurring_interval_stddev_days_max or 1)),
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        confidence = min(
            Decimal(1), Decimal(len(members)) / Decimal(config.recurring_min_occurrences * 2)
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        series_type = (
            RecurringTypeEnum.INCOME if direction is DirEnum.CREDIT else RecurringTypeEnum.EXPENSE
        )
        if direction is DirEnum.DEBIT and _is_debt_like(categorized, ordered_members):
            series_type = RecurringTypeEnum.DEBT_PAYMENT

        series.append(
            DetectedRecurringSeries(
                financial_account_id=account_id,
                series_type=series_type,
                normalized_counterparty=counterparty,
                median_amount=median_amount,
                expected_interval_days=mean_interval,
                expected_day_of_month=day_of_month,
                regularity_score=regularity_score,
                confidence=confidence,
                transaction_ids=[m.transaction_id for m in ordered_members],
            )
        )

    return series


def _is_debt_like(
    categorized: dict[uuid.UUID, tuple[CategoryEnum, TransactionContextEnum, str | None, Decimal]],
    members: list[NormalizationTransactionInput],
) -> bool:
    return any(
        categorized[m.transaction_id][0] is CategoryEnum.FINANCIAL_OBLIGATION for m in members
    )


def _mode_day_of_month(members: list[NormalizationTransactionInput]) -> int:
    days = [m.transaction_date.day for m in members]
    return statistics.mode(days)
