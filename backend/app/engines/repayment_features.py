"""Pure canonical feature construction for the experimental repayment model."""

from __future__ import annotations

import hashlib
import json
import statistics
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

FEATURE_SCHEMA_VERSION = "crediwise-cashflow-v1"
FEATURE_ORDER = (
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
_RATIO_QUANTUM = Decimal("0.000001")


@dataclass(frozen=True)
class RepaymentMonthlyInput:
    minimum_balance: int
    closing_balance: int
    net_cash_flow: int


@dataclass(frozen=True)
class RepaymentFeatureInput:
    months_covered: int
    median_income: int
    income_volatility: Decimal
    positive_cash_flow_ratio: Decimal
    existing_debt: int
    average_free_cash_flow: int
    weakest_month_cash_flow: int
    minimum_balance: int
    savings_buffer: int
    monthly_snapshots: tuple[RepaymentMonthlyInput, ...]


@dataclass(frozen=True)
class RepaymentFeatureVector:
    schema_version: str
    values: dict[str, Decimal]
    feature_hash: str


def _ratio(numerator: int | Decimal, denominator: int) -> Decimal:
    if denominator <= 0:
        return Decimal(0)
    return (Decimal(numerator) / Decimal(denominator)).quantize(
        _RATIO_QUANTUM, rounding=ROUND_HALF_UP
    )


def build(inputs: RepaymentFeatureInput) -> RepaymentFeatureVector:
    snapshots = inputs.monthly_snapshots
    closing_balances = [snapshot.closing_balance for snapshot in snapshots]
    net_cash_flows = [snapshot.net_cash_flow for snapshot in snapshots]
    average_closing_balance = round(statistics.fmean(closing_balances)) if closing_balances else 0
    negative_balance_months = sum(snapshot.minimum_balance < 0 for snapshot in snapshots)
    negative_balance_month_ratio = (
        _ratio(negative_balance_months, len(snapshots)) if snapshots else Decimal(0)
    )
    net_flow_volatility = (
        Decimal(str(statistics.pstdev(net_cash_flows))) if len(net_cash_flows) > 1 else Decimal(0)
    )
    balance_trend = (
        Decimal(closing_balances[-1] - closing_balances[0]) / Decimal(len(closing_balances) - 1)
        if len(closing_balances) > 1
        else Decimal(0)
    )
    values = {
        "months_observed": Decimal(inputs.months_covered),
        "income_cv": inputs.income_volatility.quantize(_RATIO_QUANTUM, rounding=ROUND_HALF_UP),
        "positive_net_flow_ratio": inputs.positive_cash_flow_ratio.quantize(
            _RATIO_QUANTUM, rounding=ROUND_HALF_UP
        ),
        "debt_service_ratio": _ratio(inputs.existing_debt, inputs.median_income),
        "free_cash_flow_margin": _ratio(inputs.average_free_cash_flow, inputs.median_income),
        "weakest_month_margin": _ratio(inputs.weakest_month_cash_flow, inputs.median_income),
        "minimum_balance_ratio": _ratio(inputs.minimum_balance, inputs.median_income),
        "balance_buffer_ratio": _ratio(inputs.savings_buffer, inputs.median_income),
        "average_closing_balance_ratio": _ratio(average_closing_balance, inputs.median_income),
        "negative_balance_month_ratio": negative_balance_month_ratio,
        "net_flow_volatility_ratio": _ratio(net_flow_volatility, inputs.median_income),
        "monthly_balance_trend_ratio": _ratio(balance_trend, inputs.median_income),
    }
    canonical = json.dumps(
        {name: format(values[name], "f") for name in FEATURE_ORDER},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return RepaymentFeatureVector(
        schema_version=FEATURE_SCHEMA_VERSION,
        values=values,
        feature_hash=hashlib.sha256(canonical).hexdigest(),
    )
