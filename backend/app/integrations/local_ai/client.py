"""Local-Kimi client (CLAUDE.md §5.2 dedicated adapter; PLAN §16.3).

Calls a private, self-hosted OpenAI-compatible endpoint only — never a
public-cloud fallback (CLAUDE.md §15.1, PLAN §16.3). Bounded timeout + one
retry; a `ValidationError` on the response (malformed/incomplete output) is
treated the same as a network failure — CLAUDE.md §5.3: "Reject malformed
or incomplete output."

No service may call the local runtime's HTTP endpoint directly — only this
adapter (CLAUDE.md §5.2). Callers depend on the `DocumentAnomalyPort`
protocol, never on `LocalKimiClient` concretely (PLAN §10.1 integrations
pattern), so `TrustLayerService` can inject a fake in gate tests without a
real Kimi runtime (CLAUDE.md §5.5).
"""

from typing import Protocol

import httpx
from pydantic import ValidationError

from app.core.errors import IntegrationError
from app.integrations.local_ai.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt
from app.integrations.local_ai.redaction import redact_forensic_features
from app.integrations.local_ai.schemas import DocumentAnomalyRequest, DocumentAnomalyResponse

_CHAT_COMPLETIONS_PATH = "/v1/chat/completions"
_MAX_ATTEMPTS = 2


class DocumentAnomalyPort(Protocol):
    def analyze(self, request: DocumentAnomalyRequest) -> DocumentAnomalyResponse:
        """Raises `IntegrationError` if the local runtime is unreachable or
        returns output that fails schema validation after all retries."""
        ...


class LocalKimiClient:
    def __init__(self, *, base_url: str, model: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    def analyze(self, request: DocumentAnomalyRequest) -> DocumentAnomalyResponse:
        payload = self._build_payload(request)
        last_error: Exception | None = None

        for _attempt in range(_MAX_ATTEMPTS):
            try:
                response = httpx.post(
                    f"{self._base_url}{_CHAT_COMPLETIONS_PATH}",
                    json=payload,
                    timeout=self._timeout_seconds,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return DocumentAnomalyResponse.model_validate_json(content)
            except (httpx.HTTPError, KeyError, IndexError, ValueError, ValidationError) as exc:
                last_error = exc
                continue

        raise IntegrationError("Local Kimi anomaly analysis failed") from last_error

    def _build_payload(self, request: DocumentAnomalyRequest) -> dict[str, object]:
        redacted_features = redact_forensic_features(request.forensic_features)
        content: list[dict[str, object]] = [
            {"type": "text", "text": build_user_prompt(redacted_features)}
        ]
        for image_b64 in request.page_images_base64:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                }
            )
        return {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            "response_format": {"type": "json_object"},
        }


__all__ = ["DocumentAnomalyPort", "LocalKimiClient", "PROMPT_VERSION"]
