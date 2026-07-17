"""Orchestrates optional shadow inference without affecting deterministic outputs."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.engines import repayment_features
from app.engines.cash_flow_twin import FinancialProfileResult
from app.integrations.repayment_model import MODEL_NAME, MODEL_VERSION, artifact_sha256, predict
from app.integrations.repayment_model.client import load_artifact
from app.models.assessment import Assessment
from app.models.enums import (
    BandEnum,
    RepaymentModelModeEnum,
    RepaymentPredictionStatusEnum,
)
from app.models.repayment_model_prediction import RepaymentModelPrediction
from app.repositories.model_version_repository import ModelVersionRepository
from app.repositories.repayment_model_prediction_repository import (
    RepaymentModelPredictionRepository,
)


def run_shadow_prediction(
    db: Session,
    assessment: Assessment,
    profile: FinancialProfileResult,
) -> RepaymentModelPrediction | None:
    model_hash = artifact_sha256()
    model_version = ModelVersionRepository(db).get_active_exact(
        MODEL_NAME, MODEL_VERSION, model_hash
    )
    if model_version is None:
        return None
    predictions = RepaymentModelPredictionRepository(db)
    existing = predictions.get_exact(assessment.id, model_version.id)
    if existing is not None:
        return existing

    feature_vector = repayment_features.build(
        repayment_features.RepaymentFeatureInput(
            months_covered=profile.months_covered,
            median_income=profile.median_income,
            income_volatility=profile.income_volatility,
            positive_cash_flow_ratio=profile.positive_cash_flow_ratio,
            existing_debt=profile.existing_debt,
            average_free_cash_flow=profile.average_free_cash_flow,
            weakest_month_cash_flow=profile.weakest_month_cash_flow,
            minimum_balance=profile.minimum_balance,
            savings_buffer=profile.savings_buffer,
            monthly_snapshots=tuple(
                repayment_features.RepaymentMonthlyInput(
                    minimum_balance=snapshot.minimum_balance,
                    closing_balance=snapshot.closing_balance,
                    net_cash_flow=snapshot.net_cash_flow,
                )
                for snapshot in profile.monthly_snapshots
            ),
        )
    )
    values: dict[str, Any] = {
        name: format(feature_vector.values[name], "f") for name in repayment_features.FEATURE_ORDER
    }
    base = {
        "id": uuid.uuid4(),
        "assessment_id": assessment.id,
        "model_version_id": model_version.id,
        "mode": RepaymentModelModeEnum.SHADOW_RESEARCH,
        "feature_schema_version": feature_vector.schema_version,
        "feature_hash": feature_vector.feature_hash,
        "feature_vector_json": values,
        "artifact_sha256": model_hash,
    }
    artifact = load_artifact()
    if profile.months_covered < artifact.support.minimum_months or profile.median_income <= 0:
        return predictions.add(
            RepaymentModelPrediction(
                **base,
                status=RepaymentPredictionStatusEnum.INELIGIBLE,
                raw_probability=None,
                calibrated_probability=None,
                model_confidence=None,
                reason_codes_json=[{"code": "ML_INSUFFICIENT_CASH_FLOW_HISTORY"}],
                out_of_domain_features_json=[],
                failure_code=None,
            )
        )

    try:
        output = predict(feature_vector)
    except (OSError, ValueError) as exc:
        return predictions.add(
            RepaymentModelPrediction(
                **base,
                status=RepaymentPredictionStatusEnum.UNAVAILABLE,
                raw_probability=None,
                calibrated_probability=None,
                model_confidence=None,
                reason_codes_json=[{"code": "ML_ARTIFACT_UNAVAILABLE"}],
                out_of_domain_features_json=[],
                failure_code=type(exc).__name__,
            )
        )

    return predictions.add(
        RepaymentModelPrediction(
            **base,
            status=RepaymentPredictionStatusEnum.COMPLETE,
            raw_probability=output.raw_probability,
            calibrated_probability=output.calibrated_probability,
            model_confidence=BandEnum.LOW,
            reason_codes_json=[
                contribution.model_dump(mode="json") for contribution in output.contributions
            ],
            out_of_domain_features_json=output.out_of_domain_features,
            failure_code=None,
        )
    )
