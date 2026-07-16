"""Domain error hierarchy and default HTTP mapping (PLAN §10.3)."""

import pytest

from app.core.errors import (
    AuthError,
    ConflictError,
    CrediWiseError,
    IntegrationError,
    NotFoundError,
    PermissionError,
    PipelineError,
    ValidationError,
)


@pytest.mark.parametrize(
    ("error_cls", "expected_code", "expected_status"),
    [
        (CrediWiseError, "INTERNAL_ERROR", 500),
        (NotFoundError, "NOT_FOUND", 404),
        (ValidationError, "VALIDATION_ERROR", 422),
        (AuthError, "AUTH_ERROR", 401),
        (PermissionError, "PERMISSION_DENIED", 403),
        (ConflictError, "CONFLICT", 409),
        (PipelineError, "PIPELINE_ERROR", 422),
        (IntegrationError, "INTEGRATION_ERROR", 502),
    ],
)
def test_error_default_code_and_status(
    error_cls: type[CrediWiseError], expected_code: str, expected_status: int
) -> None:
    err = error_cls("something went wrong")
    assert err.code == expected_code
    assert err.http_status == expected_status
    assert err.message == "something went wrong"
    assert err.details == {}


def test_error_carries_details() -> None:
    err = ConflictError("duplicate resource", details={"consent_id": "abc-123"})
    assert err.details == {"consent_id": "abc-123"}
