"""T5.5 explanation port. Inputs contain derived reason evidence, never PII."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class ReasonInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)


class ExplanationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject: str = Field(pattern="^(SHOCK|OFFER)$")
    reasons: tuple[ReasonInput, ...] = Field(min_length=1)


class ExplanationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(min_length=1, max_length=1500)
    reason_codes: tuple[str, ...] = Field(min_length=1)


class ExplainerPort(Protocol):
    def explain(self, inputs: ExplanationInput) -> object: ...


def explain_with_fallback(
    inputs: ExplanationInput,
    *,
    enabled: bool,
    provider: ExplainerPort | None = None,
) -> str:
    """Accept provider prose only when it cites exactly the supplied reasons."""
    fallback = _template(inputs)
    if not enabled or provider is None:
        return fallback
    try:
        output = ExplanationOutput.model_validate(provider.explain(inputs))
    except Exception:
        return fallback
    expected = tuple(reason.code for reason in inputs.reasons)
    if output.reason_codes != expected:
        return fallback
    return output.text


def _template(inputs: ExplanationInput) -> str:
    descriptions = "; ".join(reason.description for reason in inputs.reasons)
    return f"{inputs.subject.title()} explanation based on recorded reasons: {descriptions}."
