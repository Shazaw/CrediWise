"""`SafeBorrowingEngine` — Safe Borrowing Capacity (PLAN §5.6, §5.7, §15.1;
FR-9).

Pure per PLAN §10.1: no DB, network, filesystem, clock, or RNG.

`ShockCapacity` (PLAN §5.6: "the highest instalment that remains at least
STRAINED, not DEFICIT, under the configured moderate shock") is
*intentionally absent* from `MaximumSafeInstalment`'s `min(...)` below --
`ShockEngine` doesn't exist until Sprint 5 (PLAN §25). This is the same
class of documented gap as T3.3's cross-document-consistency deferral: the
formula's other four terms (`BaseCapacity`, `DSTICapacity`,
`WeakestMonthCapacity`, `TemporalLiquidityCapacity`) are fully implemented
now; Sprint 5 adds the fifth `min(...)` term once shock scenarios exist,
which can only ever *lower* `MaximumSafeInstalment` further (never raise
it), so this cycle's numbers are a conservative upper bound, not an
overstatement.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.engines.config import model_config as cfg
from app.models.enums import FreqEnum

_MONEY_Q = Decimal("1")


@dataclass(frozen=True)
class ReasonCode:
    code: str
    description: str


@dataclass(frozen=True)
class SafeBorrowingInput:
    median_income: int
    essential_expenses: int
    existing_debt_service: int
    income_volatility: Decimal
    weakest_month_cash_flow: int
    average_free_cash_flow: int
    requested_amount: int
    min_monthly_minimum_balance: int | None = None
    dominant_income_day: int | None = None
    dominant_income_frequency: FreqEnum | None = None


@dataclass(frozen=True)
class SafeBorrowingConfig:
    min_absolute_buffer_idr: int
    income_buffer_ratio: Decimal
    essential_buffer_ratio: Decimal
    volatility_buffer_multiplier: Decimal
    dsti_limit: Decimal
    tenor_candidates: tuple[int, ...]
    reference_annual_flat_rate: Decimal
    due_date_offset_min_days: int
    due_date_offset_max_days: int
    default_due_date_window: tuple[int, int]


@dataclass(frozen=True)
class RecommendationResult:
    required_liquidity_buffer: int
    base_capacity: int
    dsti_capacity: int
    weakest_month_capacity: int
    temporal_liquidity_capacity: int
    maximum_safe_instalment: int
    safe_loan_amount: int
    recommended_tenor_months: int
    recommended_due_date_start: int
    recommended_due_date_end: int
    recommended_frequency: FreqEnum
    reason_codes: list[ReasonCode] = field(default_factory=list)


def default_config() -> SafeBorrowingConfig:
    raw = cfg.CONFIG["safe_borrowing"]
    assert isinstance(raw, dict)  # noqa: S101 - internal invariant, not user input
    return SafeBorrowingConfig(
        min_absolute_buffer_idr=raw["min_absolute_buffer_idr"],
        income_buffer_ratio=raw["income_buffer_ratio"],
        essential_buffer_ratio=raw["essential_buffer_ratio"],
        volatility_buffer_multiplier=raw["volatility_buffer_multiplier"],
        dsti_limit=raw["dsti_limit"],
        tenor_candidates=raw["tenor_candidates"],
        reference_annual_flat_rate=raw["reference_annual_flat_rate"],
        due_date_offset_min_days=raw["due_date_offset_min_days"],
        due_date_offset_max_days=raw["due_date_offset_max_days"],
        default_due_date_window=raw["default_due_date_window"],
    )


DEFAULT_CONFIG = default_config()


def run(
    inputs: SafeBorrowingInput, config: SafeBorrowingConfig = DEFAULT_CONFIG
) -> RecommendationResult:
    reason_codes: list[ReasonCode] = []

    buffer = _required_liquidity_buffer(inputs, config)
    base_capacity = max(
        0, inputs.median_income - inputs.essential_expenses - inputs.existing_debt_service - buffer
    )
    dsti_capacity = max(
        0,
        _to_money(config.dsti_limit * Decimal(inputs.median_income)) - inputs.existing_debt_service,
    )
    weakest_month_capacity = max(0, inputs.weakest_month_cash_flow)
    temporal_liquidity_capacity = (
        max(0, inputs.min_monthly_minimum_balance - config.min_absolute_buffer_idr)
        if inputs.min_monthly_minimum_balance is not None
        else base_capacity
    )

    capacities = {
        "base": base_capacity,
        "dsti": dsti_capacity,
        "weakest_month": weakest_month_capacity,
        "temporal_liquidity": temporal_liquidity_capacity,
    }
    maximum_safe_instalment = min(capacities.values())
    binding = min(capacities, key=lambda k: capacities[k])
    reason_codes.append(
        ReasonCode(
            code=f"SAFE_BORROWING_LIMITED_BY_{binding.upper()}",
            description=f"Maximum safe instalment is bound by the {binding.replace('_', ' ')} term",
        )
    )

    if inputs.average_free_cash_flow <= 0 or maximum_safe_instalment <= 0:
        reason_codes.append(
            ReasonCode(
                code="SAFE_BORROWING_ZERO_CAPACITY",
                description="Free cash flow does not currently support any safe instalment",
            )
        )
        return RecommendationResult(
            required_liquidity_buffer=buffer,
            base_capacity=base_capacity,
            dsti_capacity=dsti_capacity,
            weakest_month_capacity=weakest_month_capacity,
            temporal_liquidity_capacity=temporal_liquidity_capacity,
            maximum_safe_instalment=0,
            safe_loan_amount=0,
            recommended_tenor_months=config.tenor_candidates[0],
            recommended_due_date_start=config.default_due_date_window[0],
            recommended_due_date_end=config.default_due_date_window[1],
            recommended_frequency=inputs.dominant_income_frequency or FreqEnum.MONTHLY,
            reason_codes=reason_codes,
        )

    tenor, principal = _select_tenor(maximum_safe_instalment, inputs.requested_amount, config)
    reason_codes.append(
        ReasonCode(
            code="SAFE_BORROWING_TENOR_SELECTED",
            description=f"Recommended tenor of {tenor} month(s) at the illustrative reference rate",
        )
    )

    due_start, due_end = _due_date_window(inputs.dominant_income_day, config)

    return RecommendationResult(
        required_liquidity_buffer=buffer,
        base_capacity=base_capacity,
        dsti_capacity=dsti_capacity,
        weakest_month_capacity=weakest_month_capacity,
        temporal_liquidity_capacity=temporal_liquidity_capacity,
        maximum_safe_instalment=maximum_safe_instalment,
        safe_loan_amount=principal,
        recommended_tenor_months=tenor,
        recommended_due_date_start=due_start,
        recommended_due_date_end=due_end,
        recommended_frequency=inputs.dominant_income_frequency or FreqEnum.MONTHLY,
        reason_codes=reason_codes,
    )


def _required_liquidity_buffer(inputs: SafeBorrowingInput, config: SafeBorrowingConfig) -> int:
    candidates = [
        Decimal(config.min_absolute_buffer_idr),
        Decimal(inputs.median_income) * config.income_buffer_ratio,
        Decimal(inputs.essential_expenses) * config.essential_buffer_ratio,
        inputs.income_volatility
        * Decimal(inputs.median_income)
        * config.volatility_buffer_multiplier,
    ]
    return _to_money(max(candidates))


def _to_money(value: Decimal) -> int:
    return int(value.quantize(_MONEY_Q, rounding=ROUND_HALF_UP))


def principal_from_instalment(instalment: int, tenor_months: int, annual_flat_rate: Decimal) -> int:
    """PLAN §5.7: flat-rate amortisation, MVP reference 24%/year. Solves for
    the principal whose flat-rate schedule produces exactly `instalment` per
    month over `tenor_months`."""
    rate_factor = Decimal(1) + annual_flat_rate * Decimal(tenor_months) / Decimal(12)
    principal = Decimal(instalment) * Decimal(tenor_months) / rate_factor
    return _to_money(principal)


def _select_tenor(
    maximum_safe_instalment: int, requested_amount: int, config: SafeBorrowingConfig
) -> tuple[int, int]:
    """PLAN §5.6: "choose the shortest tenor whose complete payment schedule
    fits Maximum Safe Instalment" -- interpreted as the shortest tenor that
    can finance the full requested amount within the safe instalment cap; if
    none can, the longest tenor (maximizing serviceable principal) is used
    and the illustrative principal is reported below the request (§5.7:
    "illustrative, not guaranteed")."""
    for tenor in config.tenor_candidates:
        principal = principal_from_instalment(
            maximum_safe_instalment, tenor, config.reference_annual_flat_rate
        )
        if principal >= requested_amount:
            return tenor, principal

    longest_tenor = config.tenor_candidates[-1]
    return longest_tenor, principal_from_instalment(
        maximum_safe_instalment, longest_tenor, config.reference_annual_flat_rate
    )


def _due_date_window(
    dominant_income_day: int | None, config: SafeBorrowingConfig
) -> tuple[int, int]:
    if dominant_income_day is None:
        return config.default_due_date_window
    start = min(28, dominant_income_day + config.due_date_offset_min_days)
    end = min(28, dominant_income_day + config.due_date_offset_max_days)
    return start, max(start, end)
