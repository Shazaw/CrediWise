"""Typed application settings loaded from environment variables (PLAN §17.4).

All configuration is 12-factor: environment variables only, validated at boot
by this Pydantic ``Settings`` object. Missing required variables fail fast on
import rather than surfacing as a runtime error deep in a request.

Model weights/thresholds are NOT configured here — those live in
``app/engines/config/model_config.py`` as versioned code (PLAN §17.4, §19.2).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # APP_*
    app_name: str = "crediwise-backend"
    app_env: Literal["local", "staging", "production", "test"] = "local"
    app_debug: bool = False
    app_correlation_header: str = "X-Correlation-Id"

    # DB_*
    db_host: str = Field(...)
    db_port: int = 5432
    db_name: str = Field(...)
    db_user: str = Field(...)
    db_password: str = Field(...)
    db_pool_size: int = 5

    # REDIS_*
    redis_host: str = Field(...)
    redis_port: int = 6379
    redis_db: int = 0

    # STORAGE_* (S3-compatible; MinIO locally — PLAN §16.1, §17.3)
    storage_endpoint_url: str = Field(...)
    storage_region: str = "us-east-1"
    storage_bucket: str = Field(...)
    storage_access_key: str = Field(...)
    storage_secret_key: str = Field(...)
    storage_use_ssl: bool = False

    @property
    def sqlalchemy_database_uri(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    """Process-wide cached settings singleton (env is read once per process)."""
    return Settings()  # type: ignore[call-arg]
