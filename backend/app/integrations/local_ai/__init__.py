"""Process-wide `DocumentAnomalyPort` singleton (PLAN §16.1).

Mirrors `app.integrations.storage`/`app.integrations.ocr`'s
`get_*_port`/`set_*_port` seam. Unlike storage, there is no safe "always
construct a real client" default here — a `LocalKimiClient` needs a
configured `KIMI_BASE_URL` (PLAN §16.3), and Kimi anomaly scoring is
disabled by default (`trust_layer.kimi_anomaly_scoring_enabled` in
`app/engines/config/model_config.py`, PLAN §15.6). `get_document_anomaly_port`
returns `None` when no `KIMI_BASE_URL` is configured — callers must already
treat "no port" and "port call failed" the same way (`AI_SIGNAL_UNAVAILABLE`).
"""

from app.core.config import get_settings
from app.integrations.local_ai.client import DocumentAnomalyPort, LocalKimiClient

__all__ = ["DocumentAnomalyPort", "get_document_anomaly_port", "set_document_anomaly_port"]

_document_anomaly_port: DocumentAnomalyPort | None = None
_override_set = False


def get_document_anomaly_port() -> DocumentAnomalyPort | None:
    global _document_anomaly_port
    if _override_set:
        return _document_anomaly_port
    settings = get_settings()
    if not settings.kimi_base_url:
        return None
    if _document_anomaly_port is None:
        _document_anomaly_port = LocalKimiClient(
            base_url=settings.kimi_base_url,
            model=settings.kimi_model,
            timeout_seconds=settings.kimi_timeout_seconds,
        )
    return _document_anomaly_port


def set_document_anomaly_port(port: DocumentAnomalyPort | None) -> None:
    """Test hook — inject a fake `DocumentAnomalyPort`. Passing `None`
    clears the override and reverts to the settings-based lookup above
    (which itself returns `None` — i.e. unavailable — unless `KIMI_BASE_URL`
    is configured)."""
    global _document_anomaly_port, _override_set
    _document_anomaly_port = port
    _override_set = port is not None
