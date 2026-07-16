"""Settings validation and fail-fast behaviour (PLAN §17.4).

Tests construct ``Settings`` with explicit keyword values and delete the
relevant OS env var first — pydantic-settings resolves missing constructor
kwargs from the environment at the field level (not just in ``__init__``),
so a stray env var would otherwise mask a "required field missing" case.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _base_env() -> dict[str, str]:
    return {
        "app_env": "local",
        "db_host": "localhost",
        "db_name": "crediwise_test",
        "db_user": "crediwise",
        "db_password": "secret",
        "redis_host": "localhost",
        "storage_endpoint_url": "http://localhost:9000",
        "storage_bucket": "crediwise-test",
        "storage_access_key": "crediwise",
        "storage_secret_key": "secret",
    }


def _make_settings(**kwargs: str) -> Settings:
    return Settings(**kwargs)  # type: ignore[arg-type]


def test_settings_loads_with_all_required_fields() -> None:
    settings = _make_settings(**_base_env())
    assert settings.app_env == "local"
    assert settings.db_port == 5432
    assert settings.redis_db == 0


def test_settings_computes_sqlalchemy_database_uri() -> None:
    settings = _make_settings(**_base_env())
    assert settings.sqlalchemy_database_uri == (
        "postgresql+psycopg://crediwise:secret@localhost:5432/crediwise_test"
    )


def test_settings_computes_redis_url() -> None:
    settings = _make_settings(**_base_env())
    assert settings.redis_url == "redis://localhost:6379/0"


def test_settings_fails_fast_on_missing_required_field(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    env = _base_env()
    del env["db_password"]
    with pytest.raises(ValidationError, match="db_password"):
        _make_settings(**env)


def test_settings_rejects_unknown_app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    env = _base_env()
    env["app_env"] = "not-a-real-env"
    with pytest.raises(ValidationError, match="app_env"):
        _make_settings(**env)
