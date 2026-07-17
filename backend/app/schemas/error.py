"""OpenAPI representation of PLAN §10.3's stable error envelope."""

from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any]
    correlation_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


STANDARD_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorEnvelope, "description": "Authentication required or invalid"},
    403: {"model": ErrorEnvelope, "description": "Permission denied"},
    404: {"model": ErrorEnvelope, "description": "Resource not found"},
    409: {"model": ErrorEnvelope, "description": "Conflict or reassessment required"},
    422: {"model": ErrorEnvelope, "description": "Stable validation error envelope"},
    429: {"model": ErrorEnvelope, "description": "Rate limit exceeded"},
}
