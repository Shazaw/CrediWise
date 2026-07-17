"""Leakage-safe Berka-to-CrediWise canonical cash-flow feature mapping."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

FEATURE_NAMES = (
    "months_observed",
    "income_cv",
    "positive_net_flow_ratio",
    "debt_service_ratio",
    "free_cash_flow_margin",
    "weakest_month_margin",
    "minimum_balance_ratio",
    "balance_buffer_ratio",
    "average_closing_balance_ratio",
    "negative_balance_month_ratio",
    "net_flow_volatility_ratio",
    "monthly_balance_trend_ratio",
)


@dataclass(frozen=True)
class TrainingSample:
    loan_id: int
    account_id: int
    index_date: date
    target: int
    features: tuple[float, ...]


@dataclass
class _Month:
    inflow: float = 0.0
    outflow: float = 0.0
    debt_service: float = 0.0
    minimum_balance: float = math.inf
    closing_balance: float = 0.0


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else 0.0


def _features(rows: list[dict[str, str]]) -> tuple[float, ...]:
    months: dict[str, _Month] = defaultdict(_Month)
    minimum_balance = math.inf
    for row in rows:
        month = row["transaction_date"][:7]
        amount = float(row["amount"])
        if row["type"] == "PRIJEM":
            months[month].inflow += amount
        else:
            months[month].outflow += amount
            if row["k_symbol"] == "UVER":
                months[month].debt_service += amount
        balance = float(row["balance"])
        months[month].minimum_balance = min(months[month].minimum_balance, balance)
        months[month].closing_balance = balance
        minimum_balance = min(minimum_balance, balance)

    ordered = [months[key] for key in sorted(months)]
    incomes = [month.inflow for month in ordered]
    net_flows = [month.inflow - month.outflow for month in ordered]
    median_income = statistics.median(incomes) if incomes else 0.0
    mean_income = statistics.fmean(incomes) if incomes else 0.0
    income_cv = _ratio(statistics.pstdev(incomes), mean_income) if len(incomes) > 1 else 0.0
    average_debt = statistics.fmean(month.debt_service for month in ordered) if ordered else 0.0
    average_net = statistics.fmean(net_flows) if net_flows else 0.0
    weakest_net = min(net_flows, default=0.0)
    positive_ratio = _ratio(sum(value > 0 for value in net_flows), len(net_flows))
    if math.isinf(minimum_balance):
        minimum_balance = 0.0
    closing_balances = [month.closing_balance for month in ordered]
    negative_balance_ratio = _ratio(
        sum(month.minimum_balance < 0 for month in ordered), len(ordered)
    )
    net_flow_volatility = statistics.pstdev(net_flows) if len(net_flows) > 1 else 0.0
    balance_trend = (
        (closing_balances[-1] - closing_balances[0]) / max(1, len(closing_balances) - 1)
        if len(closing_balances) > 1
        else 0.0
    )

    return (
        float(len(ordered)),
        income_cv,
        positive_ratio,
        _ratio(average_debt, median_income),
        _ratio(average_net, median_income),
        _ratio(weakest_net, median_income),
        _ratio(minimum_balance, median_income),
        _ratio(max(0.0, minimum_balance), median_income),
        _ratio(statistics.fmean(closing_balances), median_income) if closing_balances else 0.0,
        negative_balance_ratio,
        _ratio(net_flow_volatility, median_income),
        _ratio(balance_trend, median_income),
    )


def load_berka_samples(raw_directory: Path, *, minimum_months: int) -> list[TrainingSample]:
    loans: dict[int, dict[str, str]] = {}
    with (raw_directory / "berka_finished_loans.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            loans[int(row["loan_id"])] = row

    transactions: dict[int, list[dict[str, str]]] = defaultdict(list)
    with (raw_directory / "berka_preloan_transactions.csv").open(
        encoding="utf-8", newline=""
    ) as source:
        for row in csv.DictReader(source):
            loan_id = int(row["loan_id"])
            loan = loans[loan_id]
            if row["transaction_date"] >= loan["loan_date"]:
                raise ValueError(f"Post-index transaction detected for loan {loan_id}")
            transactions[loan_id].append(row)

    samples = []
    for loan_id, loan in loans.items():
        vector = _features(transactions[loan_id])
        if vector[0] < minimum_months:
            continue
        if not all(math.isfinite(value) for value in vector):
            raise ValueError(f"Non-finite feature detected for loan {loan_id}")
        samples.append(
            TrainingSample(
                loan_id=loan_id,
                account_id=int(loan["account_id"]),
                index_date=date.fromisoformat(loan["loan_date"]),
                target=1 if loan["status"] == "B" else 0,
                features=vector,
            )
        )
    return sorted(samples, key=lambda sample: (sample.index_date, sample.loan_id))


def dataset_hash(samples: list[TrainingSample]) -> str:
    canonical = [
        {
            "loan_id": sample.loan_id,
            "account_id": sample.account_id,
            "index_date": sample.index_date.isoformat(),
            "target": sample.target,
            "features": [format(value, ".12g") for value in sample.features],
        }
        for sample in samples
    ]
    payload = json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()
