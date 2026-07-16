"""Deterministic redaction for any text forwarded to the local Kimi runtime
(CLAUDE.md §5.3: "Apply deterministic redaction where raw identifiers are
not needed").

PLAN §16.3 already scopes Kimi's input to rendered page-region images plus a
deterministic forensic-feature dict (`DocumentAnomalyRequest`) rather than
raw transaction text, so this is defense-in-depth for any free-text
evidence values that end up in that feature dict (e.g. an OCR'd header
snippet) rather than the primary control.
"""

import re

_NIK_RE = re.compile(r"\b\d{16}\b")
_ACCOUNT_NUMBER_RE = re.compile(r"\b\d{8,20}\b")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")


def redact_text(text: str) -> str:
    redacted = _NIK_RE.sub("[REDACTED_ID]", text)
    redacted = _ACCOUNT_NUMBER_RE.sub("[REDACTED_NUMBER]", redacted)
    redacted = _EMAIL_RE.sub("[REDACTED_EMAIL]", redacted)
    return redacted


def redact_forensic_features(features: dict[str, str]) -> dict[str, str]:
    return {key: redact_text(value) for key, value in features.items()}
