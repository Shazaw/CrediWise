"""Central exception hierarchy and stable error envelope (PLAN §10.3).

Engines and services raise these domain errors; they never raise HTTP
exceptions directly. A single FastAPI exception handler (wired in
``app.main``) maps every ``CrediWiseError`` to the stable envelope:

    { "error": { "code", "message", "details", "correlation_id" } }
"""

from typing import Any


class CrediWiseError(Exception):
    """Base domain error. Subclasses set ``code`` and ``http_status``."""

    code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(CrediWiseError):
    code = "NOT_FOUND"
    http_status = 404


class ValidationError(CrediWiseError):
    code = "VALIDATION_ERROR"
    http_status = 422


class UnsupportedMediaTypeError(CrediWiseError):
    """FR-3 AC1: an upload whose declared Content-Type is outside
    `application/pdf, text/csv, image/png, image/jpeg` is rejected outright —
    no `source_documents` row is created (PLAN §7.2 EC)."""

    code = "UNSUPPORTED_MEDIA_TYPE"
    http_status = 415


class PdfPasswordRequiredError(ValidationError):
    """FR-3 AC4/EC: an encrypted PDF uploaded without a password is a
    same-request retry prompt, not a stored pipeline state."""

    code = "PDF_PASSWORD_REQUIRED"


class InvalidPdfPasswordError(ValidationError):
    """FR-3 AC4: the supplied password did not decrypt the PDF."""

    code = "INVALID_PDF_PASSWORD"


class AuthError(CrediWiseError):
    code = "AUTH_ERROR"
    http_status = 401


class PermissionError(CrediWiseError):  # noqa: A001 - PLAN §10.3 names it exactly this
    code = "PERMISSION_DENIED"
    http_status = 403


class ConflictError(CrediWiseError):
    code = "CONFLICT"
    http_status = 409


class PipelineError(CrediWiseError):
    code = "PIPELINE_ERROR"
    http_status = 422


class IntegrationError(CrediWiseError):
    code = "INTEGRATION_ERROR"
    http_status = 502


class RateLimitError(CrediWiseError):
    code = "RATE_LIMITED"
    http_status = 429
