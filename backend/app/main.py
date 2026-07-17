"""FastAPI application factory (PLAN §8.4).

Wires: structured logging, correlation-id middleware, the domain-error
exception handler, the liveness/readiness endpoints, and the versioned
``/api/v1`` router. This module stays thin per the layering rule in
PLAN §10.1 — routers own their own logic.
"""

import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import redis
from fastapi import FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import router as api_v1_router
from app.core.config import Settings, get_settings
from app.core.errors import CrediWiseError, RateLimitError
from app.core.logging import configure_logging, get_correlation_id, set_correlation_id
from app.db.session import engine
from app.schemas.error import STANDARD_ERROR_RESPONSES

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
        response = JSONResponse(
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
        if isinstance(exc, RateLimitError) and "retry_after" in exc.details:
            response.headers["Retry-After"] = str(exc.details["retry_after"])
        return response

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": {"errors": jsonable_encoder(exc.errors())},
                    "correlation_id": get_correlation_id(),
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {401: "AUTH_ERROR", 403: "PERMISSION_DENIED", 404: "NOT_FOUND"}
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": codes.get(exc.status_code, "HTTP_ERROR"),
                    "message": str(exc.detail),
                    "details": {},
                    "correlation_id": get_correlation_id(),
                }
            },
            headers=exc.headers,
        )

    app.include_router(api_v1_router)

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

    def custom_openapi() -> dict[str, Any]:
        """Apply the runtime error envelope contract to every operation."""
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        for path_item in schema.get("paths", {}).values():
            for operation in path_item.values():
                if not isinstance(operation, dict) or "responses" not in operation:
                    continue
                for status_code, metadata in STANDARD_ERROR_RESPONSES.items():
                    operation["responses"][str(status_code)] = {
                        "description": metadata["description"],
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorEnvelope"}
                            }
                        },
                    }
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

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
