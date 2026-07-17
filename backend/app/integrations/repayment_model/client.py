"""Validated, non-executable JSON artifact loader and inference runtime."""

from __future__ import annotations

import hashlib
import math
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path

from app.engines.repayment_features import FEATURE_ORDER, RepaymentFeatureVector
from app.integrations.repayment_model.schemas import (
    ModelContribution,
    RepaymentArtifact,
    RepaymentModelOutput,
)

MODEL_NAME = "crediwise-cashflow-risk"
MODEL_VERSION = "v1-research"
ARTIFACT_FILENAME = "crediwise_cashflow_risk_v1.json"
_ARTIFACT_PATH = Path(__file__).with_name("artifacts") / ARTIFACT_FILENAME
_PROBABILITY_QUANTUM = Decimal("0.000001")
_CONTRIBUTION_QUANTUM = Decimal("0.000001")

_REASON_CODES = {
    "months_observed": "ML_DATA_COVERAGE",
    "income_cv": "ML_INCOME_VOLATILITY",
    "positive_net_flow_ratio": "ML_POSITIVE_CASH_FLOW",
    "debt_service_ratio": "ML_DEBT_SERVICE_LOAD",
    "free_cash_flow_margin": "ML_FREE_CASH_FLOW_MARGIN",
    "weakest_month_margin": "ML_WEAKEST_MONTH",
    "minimum_balance_ratio": "ML_MINIMUM_BALANCE",
    "balance_buffer_ratio": "ML_LIQUIDITY_BUFFER",
    "average_closing_balance_ratio": "ML_AVERAGE_BALANCE",
    "negative_balance_month_ratio": "ML_NEGATIVE_BALANCE_MONTHS",
    "net_flow_volatility_ratio": "ML_CASH_FLOW_VOLATILITY",
    "monthly_balance_trend_ratio": "ML_BALANCE_TREND",
}


def artifact_sha256() -> str:
    return hashlib.sha256(_ARTIFACT_PATH.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def load_artifact() -> RepaymentArtifact:
    if _ARTIFACT_PATH.stat().st_size > 256 * 1024:
        raise ValueError("Repayment artifact exceeds size limit")
    artifact = RepaymentArtifact.model_validate_json(_ARTIFACT_PATH.read_text(encoding="utf-8"))
    if artifact.model_name != MODEL_NAME or artifact.model_version != MODEL_VERSION:
        raise ValueError("Repayment artifact identity mismatch")
    if tuple(artifact.preprocessing.feature_order) != FEATURE_ORDER:
        raise ValueError("Repayment artifact feature schema mismatch")
    return artifact


def _sigmoid(value: float) -> float:
    if value >= 0:
        exponent = math.exp(-min(value, 700.0))
        return 1.0 / (1.0 + exponent)
    exponent = math.exp(max(value, -700.0))
    return exponent / (1.0 + exponent)


def predict(features: RepaymentFeatureVector) -> RepaymentModelOutput:
    artifact = load_artifact()
    if features.schema_version != artifact.feature_schema_version:
        raise ValueError("Repayment feature schema version mismatch")
    transformed: list[float] = []
    out_of_domain: list[str] = []
    for index, name in enumerate(artifact.preprocessing.feature_order):
        value = features.values[name]
        lower = artifact.preprocessing.clip_lower[index]
        upper = artifact.preprocessing.clip_upper[index]
        if value < lower or value > upper:
            out_of_domain.append(name)
        clipped = min(max(value, lower), upper)
        transformed.append(
            float(
                (clipped - artifact.preprocessing.centers[index])
                / artifact.preprocessing.scales[index]
            )
        )
    coefficients = [float(value) for value in artifact.linear_model.coefficients]
    contributions = [
        coefficient * value for coefficient, value in zip(coefficients, transformed, strict=True)
    ]
    raw_logit = float(artifact.linear_model.intercept) + sum(contributions)
    raw_probability = _sigmoid(raw_logit)
    calibrated_probability = _sigmoid(
        float(artifact.calibration.intercept) + float(artifact.calibration.slope) * raw_logit
    )
    ranked = sorted(
        zip(artifact.preprocessing.feature_order, contributions, strict=True),
        key=lambda item: abs(item[1]),
        reverse=True,
    )[:3]
    return RepaymentModelOutput(
        raw_probability=Decimal(str(raw_probability)).quantize(
            _PROBABILITY_QUANTUM, rounding=ROUND_HALF_UP
        ),
        calibrated_probability=Decimal(str(calibrated_probability)).quantize(
            _PROBABILITY_QUANTUM, rounding=ROUND_HALF_UP
        ),
        contributions=[
            ModelContribution(
                feature=name,
                contribution=Decimal(str(contribution)).quantize(
                    _CONTRIBUTION_QUANTUM, rounding=ROUND_HALF_UP
                ),
                reason_code=_REASON_CODES[name],
            )
            for name, contribution in ranked
        ],
        out_of_domain_features=out_of_domain,
    )
