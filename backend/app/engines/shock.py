"""Pure dated-liquidity shock simulations and resilience score (FR-10).

Monthly projected cash flow and minimum temporal balance are deliberately
separate. The former uses the complete Twin aggregate; the latter replays the
Twin's dated/day-of-month recurring events, the proposed repayment, and a
deterministic month-end reconciliation point. Same-day debits are applied
before credits, a conservative ordering that makes due-date risk explicit.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.engines.config import model_config as cfg
from app.models.enums import (
    AffordEnum,
    CashEventEnum,
    DirEnum,
    ShockResilienceBandEnum,
    ShockTypeEnum,
)

_SCORE_Q = Decimal("0.01")
_MONEY_Q = Decimal("1")


@dataclass(frozen=True)
class ReasonCode:
    code: str
    description: str


@dataclass(frozen=True)
class CashFlowEventInput:
    day_of_month: int
    amount: int
    direction: DirEnum
    event_type: CashEventEnum


@dataclass(frozen=True)
class ProjectionPoint:
    sequence: int
    day_of_month: int
    event_type: str
    amount: int
    projected_balance: int


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
    cash_flow_events: tuple[CashFlowEventInput, ...] = ()
    proposed_instalment_day: int = 20
    #: `POST /assessments/{id}/simulate` overrides (PLAN §12.3) -- when
    #: either is set, an extra `CUSTOM` scenario is appended with weight 0
    #: (a what-if preview that never perturbs the canonical resilience score).
    custom_income_drop_pct: Decimal | None = None
    custom_emergency_expense: int | None = None
    include_custom_scenario: bool = False


@dataclass(frozen=True)
class ShockConfig:
    income_drop_scenarios: dict[str, Decimal]
    emergency_expense_amount: int
    scenario_weights: dict[str, Decimal]
    resilience_band_thresholds: dict[str, int]
    scenario_points: dict[str, int]
    delayed_income_days: int
    emergency_expense_day: int


@dataclass(frozen=True)
class ShockScenarioResult:
    scenario_type: ShockTypeEnum
    parameters: dict[str, object]
    projected_cash_flow: int
    minimum_projected_balance: int
    deficit_amount: int
    affordability_status: AffordEnum
    resilience_score_contribution: Decimal
    required_liquidity_buffer: int
    required_buffer_breached: bool
    projection_points: list[ProjectionPoint] = field(default_factory=list)


@dataclass(frozen=True)
class ShockResult:
    resilience_score: Decimal
    band: ShockResilienceBandEnum
    scenarios: list[ShockScenarioResult] = field(default_factory=list)
    reason_codes: list[ReasonCode] = field(default_factory=list)
    proposed_instalment: int = 0


def default_config() -> ShockConfig:
    raw = cfg.CONFIG["shock"]
    assert isinstance(raw, dict)  # noqa: S101 - internal invariant, not user input
    return ShockConfig(
        income_drop_scenarios=raw["income_drop_scenarios"],
        emergency_expense_amount=raw["emergency_expense_amount"],
        scenario_weights=raw["scenario_weights"],
        resilience_band_thresholds=raw["resilience_band_thresholds"],
        scenario_points=raw["scenario_points"],
        delayed_income_days=raw["delayed_income_days"],
        emergency_expense_day=raw["emergency_expense_day"],
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
    canonical_scenarios = [s for s in scenarios if s.scenario_type is not ShockTypeEnum.CUSTOM]
    breaches = sum(s.required_buffer_breached for s in canonical_scenarios)
    deficits = sum(s.affordability_status is AffordEnum.DEFICIT for s in canonical_scenarios)
    reason_codes[0:0] = [
        ReasonCode(
            code=f"SHOCK_RESILIENCE_{band.value}",
            description=(
                f"Canonical-battery shock resilience score is {total_score} ({band.value})"
            ),
        ),
        ReasonCode(
            code="SHOCK_REQUIRED_BUFFER_COVERAGE",
            description=(
                f"{breaches} of {len(canonical_scenarios)} canonical scenarios breach the "
                "required liquidity buffer"
            ),
        ),
        ReasonCode(
            code="SHOCK_TEMPORAL_LIQUIDITY",
            description=(f"{deficits} canonical scenarios create a temporary or month-end deficit"),
        ),
    ]
    if len(canonical_scenarios) != len(scenarios):
        reason_codes.append(
            ReasonCode(
                code="SHOCK_CUSTOM_STANDALONE",
                description=(
                    "Custom income and emergency parameters are standalone evidence with zero "
                    "aggregate contribution; the proposed instalment reruns the canonical battery"
                ),
            )
        )

    return ShockResult(
        resilience_score=total_score,
        band=band,
        scenarios=scenarios,
        reason_codes=reason_codes,
        proposed_instalment=inputs.proposed_instalment,
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
            inputs.average_free_cash_flow,
            {"delay_days": config.delayed_income_days},
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

    if (
        inputs.include_custom_scenario
        or inputs.custom_income_drop_pct is not None
        or inputs.custom_emergency_expense is not None
    ):
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
    projection_points = _project_timeline(
        inputs, config, scenario_type, projected_cash_flow, parameters
    )
    minimum_projected_balance = min(p.projected_balance for p in projection_points)
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
        required_liquidity_buffer=inputs.required_liquidity_buffer,
        required_buffer_breached=minimum_projected_balance < inputs.required_liquidity_buffer,
        projection_points=projection_points,
    )
    return result, contribution


def _project_timeline(
    inputs: ShockInput,
    config: ShockConfig,
    scenario_type: ShockTypeEnum,
    projected_cash_flow: int,
    parameters: dict[str, object],
) -> list[ProjectionPoint]:
    events: list[tuple[int, str, int, int]] = []
    dominant_income = max(
        (e for e in inputs.cash_flow_events if e.direction is DirEnum.CREDIT),
        key=lambda e: (e.amount, -e.day_of_month),
        default=None,
    )
    drop_pct = Decimal(str(parameters.get("income_drop_pct", "0")))
    lost_amount_raw = parameters.get("lost_income_amount", 0)
    lost_amount = lost_amount_raw if isinstance(lost_amount_raw, int) else 0

    for index, event in enumerate(inputs.cash_flow_events):
        amount = event.amount if event.direction is DirEnum.CREDIT else -event.amount
        day = event.day_of_month
        if (
            scenario_type
            in {
                ShockTypeEnum.INCOME_DROP_10,
                ShockTypeEnum.INCOME_DROP_20,
                ShockTypeEnum.INCOME_DROP_30,
                ShockTypeEnum.CUSTOM,
            }
            and amount > 0
        ):
            amount -= _to_money(Decimal(amount) * drop_pct)
        if scenario_type is ShockTypeEnum.DELAYED_INCOME and event is dominant_income:
            day = min(28, day + config.delayed_income_days)
        if scenario_type is ShockTypeEnum.INCOME_SOURCE_LOSS and amount > 0 and lost_amount > 0:
            reduction = min(amount, lost_amount)
            amount -= reduction
            lost_amount -= reduction
        if amount:
            # Debits sort before credits on the same day; source index is the stable tie-breaker.
            events.append((day, event.event_type.value, amount, index))

    events.append(
        (inputs.proposed_instalment_day, "PROPOSED_INSTALMENT", -inputs.proposed_instalment, -2)
    )
    if scenario_type in {ShockTypeEnum.EMERGENCY_EXPENSE, ShockTypeEnum.CUSTOM}:
        emergency_raw = parameters.get("emergency_expense", 0)
        emergency = emergency_raw if isinstance(emergency_raw, int) else 0
        if emergency:
            events.append((config.emergency_expense_day, "EMERGENCY_EXPENSE", -emergency, -1))

    represented = sum(amount for _, _, amount, _ in events)
    reconciliation = projected_cash_flow - represented
    if reconciliation:
        events.append((28, "MONTH_END_RECONCILIATION", reconciliation, 10_000))
    events.sort(key=lambda item: (item[0], item[2] > 0, item[3], item[1]))

    balance = inputs.savings_buffer
    points = [ProjectionPoint(0, 0, "OPENING_BALANCE", 0, balance)]
    for sequence, (day, event_type, amount, _) in enumerate(events, start=1):
        balance += amount
        points.append(ProjectionPoint(sequence, day, event_type, amount, balance))
    return points


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
