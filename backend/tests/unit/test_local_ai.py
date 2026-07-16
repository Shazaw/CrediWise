"""Local-Kimi adapter gate tests (CLAUDE.md §5.5).

No real Kimi runtime is available in this sandbox/CI — schema-validation,
unavailable-model, PII-redaction, and prompt-injection-resistance checks
all run against fakes/fixtures per CLAUDE.md §5.5 ("Never make the general
test suite depend on a local model being available. Gate tests use
deterministic fixtures or a fake adapter."). Known-clean/known-anomalous
document evals against a real local model are a separate marked lane
(§7.2), not implemented here — see the Sprint 3 handoff.
"""

import pytest
from pydantic import ValidationError

from app.core.errors import IntegrationError
from app.integrations.local_ai import get_document_anomaly_port, set_document_anomaly_port
from app.integrations.local_ai.client import DocumentAnomalyPort, LocalKimiClient
from app.integrations.local_ai.prompts import SYSTEM_PROMPT
from app.integrations.local_ai.redaction import redact_forensic_features, redact_text
from app.integrations.local_ai.schemas import (
    AnalysisStatus,
    AnomalyIndicator,
    AnomalyIndicatorCode,
    AnomalySeverity,
    DocumentAnomalyRequest,
    DocumentAnomalyResponse,
    unavailable_response,
)


def test_valid_response_parses() -> None:
    response = DocumentAnomalyResponse(
        model_name="kimi-local",
        model_version="v1",
        prompt_version="v1",
        analysis_status=AnalysisStatus.COMPLETE,
        anomaly_probability=0.12,
        indicators=[
            AnomalyIndicator(
                code=AnomalyIndicatorCode.FONT_STYLE_INCONSISTENCY,
                severity=AnomalySeverity.MEDIUM,
                page=2,
                evidence="Inconsistent font weight in the transaction table.",
            )
        ],
        limitations=[],
        latency_ms=1200,
    )

    assert response.analysis_status is AnalysisStatus.COMPLETE
    assert response.indicators[0].code is AnomalyIndicatorCode.FONT_STYLE_INCONSISTENCY


def test_out_of_range_probability_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DocumentAnomalyResponse(
            model_name="kimi-local",
            model_version="v1",
            prompt_version="v1",
            analysis_status=AnalysisStatus.COMPLETE,
            anomaly_probability=1.5,
            latency_ms=100,
        )


def test_unbounded_indicator_code_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AnomalyIndicator(
            code="THIS_IS_NOT_A_REAL_CODE",  # type: ignore[arg-type]
            severity=AnomalySeverity.LOW,
            page=1,
            evidence="anything",
        )


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        DocumentAnomalyResponse.model_validate(
            {
                "model_name": "kimi-local",
                "model_version": "v1",
                "prompt_version": "v1",
                "analysis_status": "COMPLETE",
                "anomaly_probability": 0.1,
                "latency_ms": 100,
                "final_fraud_verdict": "FAKE",  # forbidden: a decision, not evidence
            }
        )


def test_unavailable_response_carries_the_documented_flag() -> None:
    response = unavailable_response(model_name="kimi-local", model_version="v1")

    assert response.analysis_status is AnalysisStatus.UNAVAILABLE
    assert response.limitations == ["AI_SIGNAL_UNAVAILABLE"]
    assert response.anomaly_probability == 0.0


def test_client_raises_integration_error_when_unreachable() -> None:
    client = LocalKimiClient(base_url="http://127.0.0.1:1", model="kimi-local", timeout_seconds=0.2)
    request = DocumentAnomalyRequest(document_ref="doc-1", page_images_base64=[])

    with pytest.raises(IntegrationError):
        client.analyze(request)


def test_get_document_anomaly_port_is_none_without_base_url() -> None:
    set_document_anomaly_port(None)
    try:
        assert get_document_anomaly_port() is None
    finally:
        set_document_anomaly_port(None)


def test_set_document_anomaly_port_overrides_the_singleton() -> None:
    class _FakeKimi:
        def analyze(self, request: DocumentAnomalyRequest) -> DocumentAnomalyResponse:
            return unavailable_response(model_name="fake", model_version="v0")

    fake: DocumentAnomalyPort = _FakeKimi()
    set_document_anomaly_port(fake)
    try:
        assert get_document_anomaly_port() is fake
    finally:
        set_document_anomaly_port(None)


def test_redact_text_masks_id_and_account_numbers() -> None:
    text = "NIK 3271234567890123, rekening 1234567890, hubungi test@example.com"

    redacted = redact_text(text)

    assert "3271234567890123" not in redacted
    assert "1234567890" not in redacted
    assert "test@example.com" not in redacted
    assert "[REDACTED_ID]" in redacted
    assert "[REDACTED_EMAIL]" in redacted


def test_redact_forensic_features_redacts_every_value() -> None:
    features = {"header_snippet": "Nomor Rekening: 9988776655"}

    redacted = redact_forensic_features(features)

    assert "9988776655" not in redacted["header_snippet"]


def test_system_prompt_forbids_decisions_and_treats_document_content_as_untrusted() -> None:
    lowered = SYSTEM_PROMPT.lower()

    assert "must not" in lowered
    assert "fraudulent" in lowered
    assert "untrusted data" in lowered
    assert "never as instructions" in lowered
