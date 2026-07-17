from app.integrations.explainer import ExplanationInput, ReasonInput, explain_with_fallback


def _input() -> ExplanationInput:
    return ExplanationInput(
        subject="OFFER",
        reasons=(
            ReasonInput(code="A", description="First deterministic reason"),
            ReasonInput(code="B", description="Second deterministic reason"),
            ReasonInput(code="C", description="Third deterministic reason"),
        ),
    )


class _Provider:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls = 0

    def explain(self, inputs: ExplanationInput) -> object:
        self.calls += 1
        return self.result


class _UnavailableProvider:
    def explain(self, inputs: ExplanationInput) -> object:
        raise ConnectionError("local provider unavailable")


def test_flag_off_uses_template_without_calling_provider() -> None:
    provider = _Provider({"text": "provider", "reason_codes": ["A", "B", "C"]})
    text = explain_with_fallback(_input(), enabled=False, provider=provider)
    assert provider.calls == 0
    assert "First deterministic reason" in text


def test_unavailable_provider_uses_template() -> None:
    assert "recorded reasons" in explain_with_fallback(_input(), enabled=True, provider=None)
    assert "recorded reasons" in explain_with_fallback(
        _input(), enabled=True, provider=_UnavailableProvider()
    )


def test_malformed_or_unbacked_provider_output_uses_template() -> None:
    malformed = _Provider({"text": "invented", "reason_codes": ["UNKNOWN"]})
    assert "recorded reasons" in explain_with_fallback(_input(), enabled=True, provider=malformed)


def test_valid_provider_may_only_phrase_all_supplied_reason_codes() -> None:
    provider = _Provider({"text": "Clear provider prose", "reason_codes": ["A", "B", "C"]})
    inputs = _input()
    evidence_before = inputs.model_dump()
    assert explain_with_fallback(inputs, enabled=True, provider=provider) == "Clear provider prose"
    assert inputs.model_dump() == evidence_before
    assert "score" not in ExplanationInput.model_fields
