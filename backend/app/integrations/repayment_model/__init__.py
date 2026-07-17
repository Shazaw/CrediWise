"""Safe runtime for the CrediWise-owned repayment research artifact."""

from app.integrations.repayment_model.client import (
    ARTIFACT_FILENAME,
    MODEL_NAME,
    MODEL_VERSION,
    artifact_sha256,
    predict,
)

__all__ = [
    "ARTIFACT_FILENAME",
    "MODEL_NAME",
    "MODEL_VERSION",
    "artifact_sha256",
    "predict",
]
