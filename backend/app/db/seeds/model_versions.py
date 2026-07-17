"""Idempotently activates the exact current immutable model configuration."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.config.model_config import MODEL_NAME, MODEL_VERSION, config_hash
from app.integrations.repayment_model import (
    ARTIFACT_FILENAME,
    artifact_sha256,
)
from app.integrations.repayment_model import (
    MODEL_NAME as REPAYMENT_MODEL_NAME,
)
from app.integrations.repayment_model import (
    MODEL_VERSION as REPAYMENT_MODEL_VERSION,
)
from app.integrations.repayment_model.client import load_artifact
from app.models.enums import ModelStatusEnum
from app.models.model_version import ModelVersion


def run(session: Session) -> None:
    now = datetime.now(UTC)
    _activate(
        session,
        now=now,
        model_name=MODEL_NAME,
        version=MODEL_VERSION,
        current_hash=config_hash(),
    )
    artifact = load_artifact()
    _activate(
        session,
        now=now,
        model_name=REPAYMENT_MODEL_NAME,
        version=REPAYMENT_MODEL_VERSION,
        current_hash=artifact_sha256(),
        training_data_reference=(
            "Berka/PKDD'99 Financial via CTU Relational Repository; "
            f"dataset_sha256={artifact.training_dataset_sha256}"
        ),
        validation_metrics_json=artifact.model_dump(mode="json")["metrics"],
        artifact_uri=f"app/integrations/repayment_model/artifacts/{ARTIFACT_FILENAME}",
        artifact_sha256_value=artifact_sha256(),
        artifact_format=artifact.artifact_format,
        feature_schema_version=artifact.feature_schema_version,
        feature_schema_hash=artifact.feature_schema_sha256,
        target_version=artifact.target_version,
        runtime_contract_version="crediwise.linear_probability.v1",
        model_card_uri="backend/ml/repayment/model_cards/crediwise_cashflow_risk_v1.md",
    )


def _activate(
    session: Session,
    *,
    now: datetime,
    model_name: str,
    version: str,
    current_hash: str,
    training_data_reference: str | None = None,
    validation_metrics_json: dict[str, object] | None = None,
    artifact_uri: str | None = None,
    artifact_sha256_value: str | None = None,
    artifact_format: str | None = None,
    feature_schema_version: str | None = None,
    feature_schema_hash: str | None = None,
    target_version: str | None = None,
    runtime_contract_version: str | None = None,
    model_card_uri: str | None = None,
) -> None:
    rows = list(
        session.execute(
            select(ModelVersion).where(
                ModelVersion.model_name == model_name,
                ModelVersion.deleted_at.is_(None),
            )
        ).scalars()
    )
    exact = next(
        (row for row in rows if row.version == version and row.config_hash == current_hash),
        None,
    )
    for row in rows:
        if row.status == ModelStatusEnum.ACTIVE and row is not exact:
            row.status = ModelStatusEnum.RETIRED
            row.retired_at = now
    # The partial unique index permits one ACTIVE row per model name. Flush
    # retirement before inserting/activating the exact current configuration.
    session.flush()
    if exact is None:
        exact = ModelVersion(
            model_name=model_name,
            version=version,
            status=ModelStatusEnum.DRAFT,
            config_hash=current_hash,
            released_at=now,
        )
        session.add(exact)
    exact.status = ModelStatusEnum.ACTIVE
    exact.retired_at = None
    exact.training_data_reference = training_data_reference
    exact.validation_metrics_json = validation_metrics_json
    exact.artifact_uri = artifact_uri
    exact.artifact_sha256 = artifact_sha256_value
    exact.artifact_format = artifact_format
    exact.feature_schema_version = feature_schema_version
    exact.feature_schema_hash = feature_schema_hash
    exact.target_version = target_version
    exact.runtime_contract_version = runtime_contract_version
    exact.model_card_uri = model_card_uri
