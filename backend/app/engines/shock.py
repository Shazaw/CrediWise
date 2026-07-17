"""`ShockEngine` — temporal liquidity shock simulations + Shock Resilience
Score (PLAN §5.8, §15.1; FR-10).

Pure per PLAN §10.1: no DB, network, filesystem, clock, or RNG. Consumes
plain scalars the service layer extracts from `CashFlowTwinEngine`'s
`FinancialProfileResult` and `SafeBorrowingEngine`'s `RecommendationResult`
(`required_liquidity_buffer`) -- this engine never calls another engine
directly (PLAN §10.1: "engines depend on nothing but their own inputs and
model_config, not on each other"), matching how `RiskEngine` consumes Twin
scalars rather than a `FinancialProfile` object.

**Scenario model (ADR-016 gap-fill, §24.11):** PLAN §5.8 names the required
scenario battery, per-scenario weights, and the SURVIVABLE/STRAINED/DEFICIT
outcome thresholds, but not the exact cash-flow formula each scenario
applies. Every scenario reduces to the same two-step evaluation:

    scenario_net_cash_flow = <scenario-specific adjustment to average free
                               cash flow, or a scenario-specific override>
    projected_cash_flow = scenario_net_cash_flow - proposed_instalment
    minimum_projected_balance = savings_buffer + projected_cash_flow

...then classified against `required_liquidity_buffer` per §5.8's outcome
definitions. The scenario-specific adjustments:

- `INCOME_DROP_{10,20,30}`: `average_free_cash_flow - median_income * pct`.
- `EMERGENCY_EXPENSE`: `average_free_cash_flow - emergency_expense_amount`
  (PLAN §5.8's own example, Rp1,000,000 default).
- `INCOME_SOURCE_LOSS`: `average_free_cash_flow - largest_income_source_amount`
  (the single largest-concentration income source stops arriving entirely).
- `DELAYED_INCOME`: `-essential_expenses` -- models the "dominant income
  arrives late" scenario as: essential expenses must still be covered from
  the existing buffer before that income shows up, but nothing is
  permanently lost (unlike `INCOME_SOURCE_LOSS`), so only the committed
  essential-expense outflow (not discretionary/debt, which can be deferred a
  few days) is charged against this month's contribution.
- `WEAKEST_MONTH_REPLAY`: the historical weakest month's net cash flow,
  replayed as-is.

`ShockCapacity` (PLAN §5.6's fifth `SafeBorrowingEngine` term) is *not*
computed here — see `app/engines/safe_borrowing.py`'s module docstring and
ADR-016: because `minimum_projected_balance` is linear in `proposed_instalment`,
"the highest instalment that keeps the moderate (20% income-drop) scenario at
or above zero" has a closed form that doesn't require calling this engine at
all, so `SafeBorrowingEngine` computes it independently from its own inputs.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.engines.config import model_config as cfg
from app.models.enums import AffordEnum, ShockResilienceBandEnum, ShockTypeEnum

_SCORE_Q = Decimal("0.01")
_MONEY_Q = Decimal("1")


@dataclass(frozen=True)
class ReasonCode:
    code: str
    description: str


@dataclass(frozen=True)
class ShockInput:
    median_income: int
    essential_expenses: int
    average_free_cash_flow: int
    weakest_month_cash_flow: int
    savings_buffer: int
    required_liquidity_buffer: int
    proposed_instalment: int
    largest_income_source_amount: int | None = None
    #: `POST /assessments/{id}/simulate` overrides (PLAN §12.3) -- when
    #: either is set, an extra `CUSTOM` scenario is appended with weight 0
    #: (a what-if preview that never perturbs the canonical resilience score).
    custom_income_drop_pct: Decimal | None = None
    custom_emergency_expense: int | None = None


@dataclass(frozen=True)
class ShockConfig:
    income_drop_scenarios: dict[str, Decimal]
    emergency_expense_amount: int
    scenario_weights: dict[str, Decimal]
    resilience_band_thresholds: dict[str, int]
    scenario_points: dict[str, int]


@dataclass(frozen=True)
class ShockScenarioResult:
    scenario_type: ShockTypeEnum
    parameters: dict[str, object]
    projected_cash_flow: int
    minimum_projected_balance: int
    deficit_amount: int
    affordability_status: AffordEnum
    resilience_score_contribution: Decimal


@dataclass(frozen=True)
class ShockResult:
    resilience_score: Decimal
    band: ShockResilienceBandEnum
    scenarios: list[ShockScenarioResult] = field(default_factory=list)
    reason_codes: list[ReasonCode] = field(default_factory=list)


def default_config() -> ShockConfig:
    raw = cfg.CONFIG["shock"]
    assert isinstance(raw, dict)  # noqa: S101 - internal invariant, not user input
    return ShockConfig(
        income_drop_scenarios=raw["income_drop_scenarios"],
        emergency_expense_amount=raw["emergency_expense_amount"],
        scenario_weights=raw["scenario_weights"],
        resilience_band_thresholds=raw["resilience_band_thresholds"],
        scenario_points=raw["scenario_points"],
    )


DEFAULT_CONFIG = default_config()


def run(inputs: ShockInput, config: ShockConfig = DEFAULT_CONFIG) -> ShockResult:
    scenarios: list[ShockScenarioResult] = []
    reason_codes: list[ReasonCode] = []
    total_score = Decimal(0)

    for scenario_type, weight, scenario_net_cash_flow, parameters in _scenario_definitions(
        inputs, config
    ):
        result, contribution = _evaluate_scenario(
            inputs, config, scenario_type, weight, scenario_net_cash_flow, parameters
        )
        scenarios.append(result)
        total_score += contribution
        if result.affordability_status is AffordEnum.DEFICIT:
            reason_codes.append(
                ReasonCode(
                    code=f"SHOCK_DEFICIT_{scenario_type.value}",
                    description=(
                        f"{scenario_type.value.replace('_', ' ').title()} results in a "
                        "projected deficit"
                    ),
                )
            )

    total_score = total_score.quantize(_SCORE_Q, rounding=ROUND_HALF_UP)
    band = _band_for(total_score, config)
    reason_codes.insert(
        0,
        ReasonCode(
            code=f"SHOCK_RESILIENCE_{band.value}",
            description=f"Shock resilience score is {total_score} ({band.value})",
        ),
    )

    return ShockResult(
        resilience_score=total_score, band=band, scenarios=scenarios, reason_codes=reason_codes
    )


def moderate_shock_capacity(
    *,
    savings_buffer: int,
    average_free_cash_flow: int,
    median_income: int,
    moderate_shock_income_drop_pct: Decimal,
) -> int:
    """The exact instalment ceiling (PLAN §5.6 `ShockCapacity`) that keeps
    the moderate (20% income-drop) scenario's `minimum_projected_balance` at
    or above zero -- see this module's docstring for the linear derivation.
    Duplicated as a standalone function (not called by `SafeBorrowingEngine`,
    which re-derives the same formula from its own inputs per PLAN §10.1) so
    the identical arithmetic is exercised and golden-tested once.
    """
    scenario_net_cash_flow = average_free_cash_flow - _to_money(
        Decimal(median_income) * moderate_shock_income_drop_pct
    )
    return max(0, savings_buffer + scenario_net_cash_flow)


def _scenario_definitions(
    inputs: ShockInput, config: ShockConfig
) -> list[tuple[ShockTypeEnum, Decimal, int, dict[str, object]]]:
    drop = config.income_drop_scenarios
    weights = config.scenario_weights
    lost_income = inputs.largest_income_source_amount or 0

    defs: list[tuple[ShockTypeEnum, Decimal, int, dict[str, object]]] = [
        (
            ShockTypeEnum.INCOME_DROP_10,
            weights["INCOME_DROP_10"],
            inputs.average_free_cash_flow - _to_money(Decimal(inputs.median_income) * drop["10"]),
            {"income_drop_pct": str(drop["10"])},
        ),
        (
            ShockTypeEnum.INCOME_DROP_20,
            weights["INCOME_DROP_20"],
            inputs.average_free_cash_flow - _to_money(Decimal(inputs.median_income) * drop["20"]),
            {"income_drop_pct": str(drop["20"])},
        ),
        (
            ShockTypeEnum.INCOME_DROP_30,
            weights["INCOME_DROP_30"],
            inputs.average_free_cash_flow - _to_money(Decimal(inputs.median_income) * drop["30"]),
            {"income_drop_pct": str(drop["30"])},
        ),
        (
            ShockTypeEnum.DELAYED_INCOME,
            weights["DELAYED_INCOME"],
            -inputs.essential_expenses,
            {},
        ),
        (
            ShockTypeEnum.EMERGENCY_EXPENSE,
            weights["EMERGENCY_EXPENSE"],
            inputs.average_free_cash_flow - config.emergency_expense_amount,
            {"emergency_expense": config.emergency_expense_amount},
        ),
        (
            ShockTypeEnum.INCOME_SOURCE_LOSS,
            weights["INCOME_SOURCE_LOSS"],
            inputs.average_free_cash_flow - lost_income,
            {"lost_income_amount": lost_income},
        ),
        (
            ShockTypeEnum.WEAKEST_MONTH_REPLAY,
            weights["WEAKEST_MONTH_REPLAY"],
            inputs.weakest_month_cash_flow,
            {},
        ),
    ]

    if inputs.custom_income_drop_pct is not None or inputs.custom_emergency_expense is not None:
        pct = inputs.custom_income_drop_pct or Decimal(0)
        emergency = inputs.custom_emergency_expense or 0
        custom_cash_flow = (
            inputs.average_free_cash_flow
            - _to_money(Decimal(inputs.median_income) * pct)
            - emergency
        )
        defs.append(
            (
                ShockTypeEnum.CUSTOM,
                Decimal(0),
                custom_cash_flow,
                {"income_drop_pct": str(pct), "emergency_expense": emergency},
            )
        )
    return defs


def _evaluate_scenario(
    inputs: ShockInput,
    config: ShockConfig,
    scenario_type: ShockTypeEnum,
    weight: Decimal,
    scenario_net_cash_flow: int,
    parameters: dict[str, object],
) -> tuple[ShockScenarioResult, Decimal]:
    projected_cash_flow = scenario_net_cash_flow - inputs.proposed_instalment
    minimum_projected_balance = inputs.savings_buffer + projected_cash_flow
    deficit_amount = max(0, -minimum_projected_balance)

    if minimum_projected_balance >= inputs.required_liquidity_buffer:
        status = AffordEnum.SURVIVABLE
        points = config.scenario_points["survivable"]
    elif minimum_projected_balance >= 0:
        status = AffordEnum.STRAINED
        points = config.scenario_points["strained"]
    else:
        status = AffordEnum.DEFICIT
        points = config.scenario_points["deficit"]

    contribution = (weight * Decimal(points)).quantize(_SCORE_Q, rounding=ROUND_HALF_UP)
    result = ShockScenarioResult(
        scenario_type=scenario_type,
        parameters=parameters,
        projected_cash_flow=projected_cash_flow,
        minimum_projected_balance=minimum_projected_balance,
        deficit_amount=deficit_amount,
        affordability_status=status,
        resilience_score_contribution=contribution,
    )
    return result, contribution


def band_from_score(
    score: Decimal, config: ShockConfig = DEFAULT_CONFIG
) -> ShockResilienceBandEnum:
    """Public wrapper for `GET /assessments/{id}/shocks`, which reads the
    already-persisted `resilience_score` back from `assessments` /
    `shock_scenarios` rows rather than re-running `run()` (same pattern as
    `assessment_service.band_from_score` for Data Confidence)."""
    return _band_for(score, config)


def _band_for(score: Decimal, config: ShockConfig) -> ShockResilienceBandEnum:
    if score >= config.resilience_band_thresholds["strong"]:
        return ShockResilienceBandEnum.STRONG
    if score >= config.resilience_band_thresholds["moderate"]:
        return ShockResilienceBandEnum.MODERATE
    return ShockResilienceBandEnum.FRAGILE


def _to_money(value: Decimal) -> int:
    return int(value.quantize(_MONEY_Q, rounding=ROUND_HALF_UP))
