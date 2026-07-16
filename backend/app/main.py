"""FastAPI application factory (PLAN §8.4, Sprint 0).

Wires: structured logging, correlation-id middleware, the domain-error
exception handler, and the liveness/readiness endpoints. Versioned business
routers (``app/api/v1``) are mounted starting Sprint 1 — this module stays
thin per the layering rule in PLAN §10.1.
"""

import logging
import uuid
from collections.abc import Awaitable, Callable

import redis
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.errors import CrediWiseError
from app.core.logging import configure_logging, get_correlation_id, set_correlation_id
from app.db.session import engine

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(logging.DEBUG if settings.app_debug else logging.INFO)

    app = FastAPI(title=settings.app_name, docs_url="/docs", redoc_url="/redoc")

    @app.middleware("http")
    async def correlation_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlation_id = request.headers.get(settings.app_correlation_header) or str(uuid.uuid4())
        set_correlation_id(correlation_id)
        response = await call_next(request)
        response.headers[settings.app_correlation_header] = correlation_id
        return response

    @app.exception_handler(CrediWiseError)
    async def crediwise_error_handler(request: Request, exc: CrediWiseError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "correlation_id": get_correlation_id(),
                }
            },
        )

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        """Liveness: process is up. No dependency checks (PLAN §20.3)."""
        return {"status": "ok"}

    @app.get("/ready", tags=["ops"])
    async def ready() -> JSONResponse:
        """Readiness: DB and Redis are reachable (PLAN §20.3)."""
        checks = {"db": _check_db(), "redis": _check_redis(settings)}
        healthy = all(checks.values())
        return JSONResponse(
            status_code=200 if healthy else 503,
            content={"status": "ok" if healthy else "unavailable", "checks": checks},
        )

    return app


def _check_db() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("readiness DB check failed")
        return False


def _check_redis(settings: Settings) -> bool:
    try:
        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        return bool(client.ping())
    except Exception:
        logger.exception("readiness Redis check failed")
        return False


app = create_app()
