"""Provider-neutral explanation integration with deterministic fallback."""

from app.integrations.explainer.port import (
    ExplainerPort,
    ExplanationInput,
    ExplanationOutput,
    ReasonInput,
    explain_with_fallback,
)

__all__ = [
    "ExplanationInput",
    "ExplanationOutput",
    "ExplainerPort",
    "ReasonInput",
    "explain_with_fallback",
]
