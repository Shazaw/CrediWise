"""Local-Kimi reachability check (CLAUDE.md §5.3 "Provide a deterministic
fallback when local AI is unavailable"; PLAN §16.3).

Probes the OpenAI-compatible `/v1/models` introspection endpoint — every
OpenAI-compatible local runtime (vLLM, llama.cpp server, Ollama's compat
shim, ...) exposes it, so this doesn't assume a CrediWise-specific route on
infrastructure CrediWise doesn't own.
"""

from enum import StrEnum

import httpx


class KimiHealthStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


def check_health(base_url: str | None, *, timeout_seconds: float) -> KimiHealthStatus:
    if not base_url:
        return KimiHealthStatus.UNAVAILABLE
    try:
        response = httpx.get(f"{base_url}/v1/models", timeout=timeout_seconds)
        response.raise_for_status()
    except httpx.HTTPError:
        return KimiHealthStatus.UNAVAILABLE
    return KimiHealthStatus.AVAILABLE
