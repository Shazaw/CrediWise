"""Typed local-Kimi request/response contract (CLAUDE.md §5.2/§5.3; PLAN §16.3).

Every field is bounded (enums, length caps, numeric ranges) so a malformed
or adversarial model response fails Pydantic validation instead of silently
entering the Trust Layer (CLAUDE.md §5.3: "Reject malformed or incomplete
output... Use bounded enums for indicator codes and severity").
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AnomalySeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AnomalyIndicatorCode(StrEnum):
    """Bounded evidence classes only — never a fraud/authenticity verdict
    (CLAUDE.md §5.3, PLAN §15.6 forbidden outputs)."""

    FONT_STYLE_INCONSISTENCY = "FONT_STYLE_INCONSISTENCY"
    TEXT_IMAGE_OVERLAY = "TEXT_IMAGE_OVERLAY"
    DUPLICATE_REGION = "DUPLICATE_REGION"
    ALIGNMENT_ANOMALY = "ALIGNMENT_ANOMALY"
    DATE_FORMAT_INCONSISTENCY = "DATE_FORMAT_INCONSISTENCY"
    CURRENCY_FORMAT_INCONSISTENCY = "CURRENCY_FORMAT_INCONSISTENCY"


class AnalysisStatus(StrEnum):
    COMPLETE = "COMPLETE"
    UNAVAILABLE = "UNAVAILABLE"


class AnomalyIndicator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: AnomalyIndicatorCode
    severity: AnomalySeverity
    page: int = Field(ge=1)
    evidence: str = Field(max_length=500)


class DocumentAnomalyRequest(BaseModel):
    """Bounded inputs only (PLAN §16.3): locally rendered page-region images
    plus deterministic forensic features — never raw statement bytes, raw
    transaction text, account numbers, or PDF/banking passwords."""

    model_config = ConfigDict(extra="forbid")

    document_ref: str = Field(max_length=100)
    page_images_base64: list[str] = Field(max_length=10)
    forensic_features: dict[str, str] = Field(default_factory=dict, max_length=30)


class DocumentAnomalyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str
    model_version: str
    prompt_version: str
    analysis_status: AnalysisStatus
    anomaly_probability: float = Field(ge=0.0, le=1.0)
    indicators: list[AnomalyIndicator] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=20)
    latency_ms: int = Field(ge=0)


def unavailable_response(*, model_name: str, model_version: str) -> DocumentAnomalyResponse:
    """The deterministic-fallback value used whenever the local runtime is
    unreachable or returns invalid output (PLAN §15.6: "Model unavailable →
    deterministic pipeline continues with AI_SIGNAL_UNAVAILABLE")."""
    return DocumentAnomalyResponse(
        model_name=model_name,
        model_version=model_version,
        prompt_version="unavailable",
        analysis_status=AnalysisStatus.UNAVAILABLE,
        anomaly_probability=0.0,
        indicators=[],
        limitations=["AI_SIGNAL_UNAVAILABLE"],
        latency_ms=0,
    )
