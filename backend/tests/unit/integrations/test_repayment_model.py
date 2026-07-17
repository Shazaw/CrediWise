from decimal import Decimal

from pydantic import ValidationError

from app.engines.repayment_features import (
    FEATURE_ORDER,
    FEATURE_SCHEMA_VERSION,
    RepaymentFeatureVector,
)
from app.integrations.repayment_model.client import artifact_sha256, load_artifact, predict
from app.integrations.repayment_model.schemas import RepaymentArtifact


def _feature_vector(value: Decimal = Decimal("0.5")) -> RepaymentFeatureVector:
    return RepaymentFeatureVector(
        schema_version=FEATURE_SCHEMA_VERSION,
        values={name: value for name in FEATURE_ORDER},
        feature_hash="0" * 64,
    )


def test_packaged_repayment_model_is_valid_and_prediction_is_deterministic() -> None:
    artifact = load_artifact()

    first = predict(_feature_vector())
    second = predict(_feature_vector())

    assert artifact.model_name == "crediwise-cashflow-risk"
    assert artifact.model_version == "v1-research"
    assert artifact_sha256() == "57c4230f02f7f261da1eb1bdcea22ccfe9ea4688b705b5c2c41b9aba0977a267"
    assert first == second
    assert Decimal(0) <= first.calibrated_probability <= Decimal(1)
    assert len(first.contributions) == 3


def test_repayment_model_reports_out_of_domain_features() -> None:
    output = predict(_feature_vector(Decimal("1000000")))

    assert set(output.out_of_domain_features) == set(FEATURE_ORDER)


def test_repayment_artifact_rejects_misaligned_coefficients() -> None:
    payload = load_artifact().model_dump(mode="json")
    payload["linear_model"]["coefficients"] = []

    try:
        RepaymentArtifact.model_validate(payload)
    except ValidationError:
        pass
    else:
        raise AssertionError("Misaligned artifact should be rejected")
