"""`RiskEngine` — Indicative Credit Risk Band + Model Confidence (PLAN §5.3,
§5.5, §15.1; FR-8).

Pure per PLAN §10.1: no DB, network, filesystem, clock, or RNG. Consumes the
`CashFlowTwinEngine`'s `FinancialProfileResult` fields (passed in as plain
scalars by the service layer) plus the assessment's aggregated Data
Confidence signals. Model confidence is computed *separately* from the risk
band (§5.5) — a thin-data low-risk result must never be labelled
"high confidence" (FR-8 AC2).
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.engines.config import model_config as cfg
from app.models.enums import BandEnum, RiskBandEnum

_SCORE_Q = Decimal("0.01")


@dataclass(frozen=True)
class ReasonCode:
    code: str
    description: str


@dataclass(frozen=True)
class RiskInput:
    median_income: int
    essential_expenses: int
    discretionary_expenses: int
    existing_debt_service: int
    positive_cash_flow_ratio: Decimal
    income_volatility: Decimal
    months_covered: int
    data_confidence_band: BandEnum | None
    income_concentration_ratio: Decimal | None
    ocr_score: Decimal | None = None
    ownership_score: Decimal | None = None
    completeness_score: Decimal | None = None


@dataclass(frozen=True)
class RiskConfig:
    weights: dict[str, Decimal]
    dsti_thresholds: dict[str, Decimal]
    dsti_scores: dict[str, int]
    cash_flow_ratio_thresholds: dict[str, Decimal]
    income_concentration_flag_threshold: Decimal
    volatility_scale: Decimal
    behaviour_discretionary_scale: Decimal
    band_thresholds: dict[str, int]
    model_confidence_min_months_for_high: int
    model_confidence_min_months_for_medium: int
    trust_layer_band_thresholds: dict[str, int]


@dataclass(frozen=True)
class RiskResult:
    income_stability_score: Decimal
    cash_flow_health_score: Decimal
    obligation_load_score: Decimal
    behaviour_score: Decimal
    composite_score: Decimal
    band: RiskBandEnum
    model_confidence: BandEnum
    reason_codes: list[ReasonCode] = field(default_factory=list)


def default_config() -> RiskConfig:
    raw = cfg.CONFIG["risk"]
    assert isinstance(raw, dict)  # noqa: S101 - internal invariant, not user input
    trust_layer_raw = cfg.CONFIG["trust_layer"]
    assert isinstance(trust_layer_raw, dict)  # noqa: S101 - internal invariant, not user input
    return RiskConfig(
        weights=raw["weights"],
        dsti_thresholds=raw["dsti_thresholds"],
        dsti_scores=raw["dsti_scores"],
        cash_flow_ratio_thresholds=raw["cash_flow_ratio_thresholds"],
        income_concentration_flag_threshold=raw["income_concentration_flag_threshold"],
        volatility_scale=raw["volatility_scale"],
        behaviour_discretionary_scale=raw["behaviour_discretionary_scale"],
        band_thresholds=raw["band_thresholds"],
        model_confidence_min_months_for_high=raw["model_confidence_months"]["min_months_for_high"],
        model_confidence_min_months_for_medium=raw["model_confidence_months"][
            "min_months_for_medium"
        ],
        trust_layer_band_thresholds=trust_layer_raw["band_thresholds"],
    )


DEFAULT_CONFIG = default_config()


def run(inputs: RiskInput, config: RiskConfig = DEFAULT_CONFIG) -> RiskResult:
    reason_codes: list[ReasonCode] = []

    income_stability_score, income_reasons = _score_income_stability(inputs, config)
    cash_flow_health_score, cash_flow_reasons = _score_cash_flow_health(inputs, config)
    obligation_load_score, obligation_reasons, dsti = _score_obligation_load(inputs, config)
    behaviour_score, behaviour_reasons = _score_behaviour(inputs, config)

    reason_codes.extend(income_reasons)
    reason_codes.extend(cash_flow_reasons)
    reason_codes.extend(obligation_reasons)
    reason_codes.extend(behaviour_reasons)

    sub_scores = {
        "income_stability": income_stability_score,
        "cash_flow_health": cash_flow_health_score,
        "obligation_load": obligation_load_score,
        "behaviour": behaviour_score,
    }
    composite = sum(
        (config.weights[name] * score for name, score in sub_scores.items()), start=Decimal("0")
    ).quantize(_SCORE_Q, rounding=ROUND_HALF_UP)

    insufficient_data = inputs.data_confidence_band is BandEnum.LOW or inputs.months_covered < 2
    if insufficient_data:
        band = RiskBandEnum.INSUFFICIENT_DATA
        reason_codes.append(
            ReasonCode(
                code="RISK_INSUFFICIENT_DATA",
                description="Data Confidence is LOW or fewer than 2 months are covered",
            )
        )
    else:
        band = _band_for(composite, config)

    model_confidence = _model_confidence(inputs, config)

    return RiskResult(
        income_stability_score=income_stability_score,
        cash_flow_health_score=cash_flow_health_score,
        obligation_load_score=obligation_load_score,
        behaviour_score=behaviour_score,
        composite_score=composite,
        band=band,
        model_confidence=model_confidence,
        reason_codes=reason_codes,
    )


def _band_for(score: Decimal, config: RiskConfig) -> RiskBandEnum:
    if score >= config.band_thresholds["a"]:
        return RiskBandEnum.A
    if score >= config.band_thresholds["b"]:
        return RiskBandEnum.B
    if score >= config.band_thresholds["c"]:
        return RiskBandEnum.C
    return RiskBandEnum.D


def _score_income_stability(
    inputs: RiskInput, config: RiskConfig
) -> tuple[Decimal, list[ReasonCode]]:
    penalty = inputs.income_volatility * config.volatility_scale
    score = max(Decimal(0), min(Decimal(100), Decimal(100) - penalty)).quantize(
        _SCORE_Q, rounding=ROUND_HALF_UP
    )
    reasons = [
        ReasonCode(
            code="RISK_INCOME_VOLATILITY",
            description=f"Income volatility ratio: {inputs.income_volatility}",
        )
    ]
    if (
        inputs.income_concentration_ratio is not None
        and inputs.income_concentration_ratio > config.income_concentration_flag_threshold
    ):
        # PLAN §5.3: flagged, never auto-penalised (fairness §19.4) -- the
        # score above already excludes this signal.
        reasons.append(
            ReasonCode(
                code="RISK_INCOME_CONCENTRATION",
                description="Single income source accounts for over 80% of income",
            )
        )
    return score, reasons


def _score_cash_flow_health(
    inputs: RiskInput, config: RiskConfig
) -> tuple[Decimal, list[ReasonCode]]:
    ratio = inputs.positive_cash_flow_ratio
    strong = config.cash_flow_ratio_thresholds["strong"]
    ok = config.cash_flow_ratio_thresholds["ok"]
    if ratio >= strong:
        score = Decimal(100)
        reason = ReasonCode(
            code="RISK_CASH_FLOW_STRONG", description="Positive cash flow in most months"
        )
    elif ratio >= ok:
        score = Decimal(70) + (ratio - ok) / (strong - ok) * Decimal(30)
        reason = ReasonCode(
            code="RISK_CASH_FLOW_OK", description="Positive cash flow in a majority of months"
        )
    else:
        score = ratio / ok * Decimal(70) if ok else Decimal(0)
        reason = ReasonCode(
            code="RISK_CASH_FLOW_WEAK", description="Positive cash flow in fewer months than ideal"
        )
    return score.quantize(_SCORE_Q, rounding=ROUND_HALF_UP), [reason]


def _score_obligation_load(
    inputs: RiskInput, config: RiskConfig
) -> tuple[Decimal, list[ReasonCode], Decimal]:
    dsti = (
        Decimal(inputs.existing_debt_service) / Decimal(inputs.median_income)
        if inputs.median_income > 0
        else Decimal(0)
    )
    thresholds = config.dsti_thresholds
    if dsti <= thresholds["excellent"]:
        tier = "excellent"
    elif dsti <= thresholds["good"]:
        tier = "good"
    elif dsti <= thresholds["caution"]:
        tier = "caution"
    else:
        tier = "high"
    score = Decimal(config.dsti_scores[tier])
    reason = ReasonCode(
        code=f"RISK_DSTI_{tier.upper()}",
        description=f"Debt-service-to-income ratio: {(dsti * 100).quantize(_SCORE_Q)}%",
    )
    return score, [reason], dsti


def _score_behaviour(inputs: RiskInput, config: RiskConfig) -> tuple[Decimal, list[ReasonCode]]:
    if inputs.median_income <= 0:
        return Decimal(0), [
            ReasonCode(
                code="RISK_BEHAVIOUR_NO_INCOME_DATA",
                description="No positive income to evaluate discretionary spending discipline",
            )
        ]
    discretionary_ratio = Decimal(inputs.discretionary_expenses) / Decimal(inputs.median_income)
    penalty = discretionary_ratio * config.behaviour_discretionary_scale
    score = max(Decimal(0), min(Decimal(100), Decimal(100) - penalty)).quantize(
        _SCORE_Q, rounding=ROUND_HALF_UP
    )
    reason = ReasonCode(
        code="RISK_DISCRETIONARY_SPENDING",
        description=f"Discretionary spending is {(discretionary_ratio * 100).quantize(_SCORE_Q)}% of income",
    )
    return score, [reason]


def _model_confidence(inputs: RiskInput, config: RiskConfig) -> BandEnum:
    components = [
        c
        for c in (inputs.ocr_score, inputs.ownership_score, inputs.completeness_score)
        if c is not None
    ]
    average = sum(components, start=Decimal(0)) / len(components) if components else Decimal(50)

    high = config.trust_layer_band_thresholds["high"]
    medium = config.trust_layer_band_thresholds["medium"]
    if average >= high:
        band = BandEnum.HIGH
    elif average >= medium:
        band = BandEnum.MEDIUM
    else:
        band = BandEnum.LOW

    if inputs.months_covered < config.model_confidence_min_months_for_medium:
        return BandEnum.LOW
    if (
        inputs.months_covered < config.model_confidence_min_months_for_high
        and band is BandEnum.HIGH
    ):
        return BandEnum.MEDIUM
    return band
