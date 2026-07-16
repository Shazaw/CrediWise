"""Structured JSON logging: correlation-id propagation and PII redaction
(PLAN §20.3, CLAUDE.md §15.1)."""

import json
import logging

from app.core.logging import _JsonFormatter, set_correlation_id


def _make_record(msg: str, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_format_emits_valid_json_with_expected_fields() -> None:
    set_correlation_id(None)
    payload = json.loads(_JsonFormatter().format(_make_record("hello")))
    assert payload["message"] == "hello"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.logger"
    assert "timestamp" in payload


def test_format_includes_active_correlation_id() -> None:
    set_correlation_id("corr-abc-123")
    payload = json.loads(_JsonFormatter().format(_make_record("hello")))
    assert payload["correlation_id"] == "corr-abc-123"
    set_correlation_id(None)


def test_format_redacts_sensitive_extra_fields() -> None:
    set_correlation_id(None)
    record = _make_record(
        "login attempt", password="hunter2", authorization="Bearer xyz", user_id="u-1"
    )
    payload = json.loads(_JsonFormatter().format(record))
    assert payload["password"] == "[REDACTED]"
    assert payload["authorization"] == "[REDACTED]"
    assert payload["user_id"] == "u-1"
