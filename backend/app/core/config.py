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

    # SECURITY_* (RS256 JWT signing — PLAN §18.1)
    security_jwt_private_key: str = Field(...)
    security_jwt_public_key: str = Field(...)
    security_jwt_kid: str = "local-dev-1"
    security_access_token_ttl_minutes: int = 15
    security_refresh_token_ttl_days: int = 30

    # Upload file-security limits (PLAN §7.2, FR-3 AC2/AC5). `max_upload_mb`
    # is the PLAN-named `MAX_UPLOAD_MB` knob; the page/pixel caps are Sprint 2
    # implementation choices for the decompression-bomb/page-count limits
    # FR-3 AC5 requires but does not size (PLAN §24.11 gap-fill).
    max_upload_mb: int = 15
    max_pdf_pages: int = 60
    max_image_pixels: int = 25_000_000

    @property
    def sqlalchemy_database_uri(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def jwt_private_key_pem(self) -> str:
        """PEM keys are stored as single-line env vars with literal ``\\n``."""
        return self.security_jwt_private_key.replace("\\n", "\n")

    @property
    def jwt_public_key_pem(self) -> str:
        return self.security_jwt_public_key.replace("\\n", "\n")


@lru_cache
def get_settings() -> Settings:
    """Process-wide cached settings singleton (env is read once per process)."""
    return Settings()  # type: ignore[call-arg]
