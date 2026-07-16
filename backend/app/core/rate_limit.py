"""Redis-backed rate limiting for the auth/upload/general tiers (PLAN §12.1).

A fixed-window counter per ``{tier}:{client_ip}`` bucket — the simplest
correct implementation of the documented per-minute/per-hour tiers. Backed
by any Redis-protocol client so tests can inject ``fakeredis`` via
``set_redis_client`` instead of requiring a live Redis (PLAN §21.1).
"""

from collections.abc import Callable

import redis
from fastapi import Request

from app.core.config import get_settings
from app.core.errors import RateLimitError

#: (max requests, window seconds) per PLAN §12.1 defaults.
_TIERS: dict[str, tuple[int, int]] = {
    "auth": (10, 60),
    "upload": (20, 3600),
    "general": (120, 60),
}

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.Redis.from_url(settings.redis_url)
    return _redis_client


def set_redis_client(client: redis.Redis | None) -> None:
    """Test hook — inject a ``fakeredis`` client instead of a real connection."""
    global _redis_client
    _redis_client = client


def rate_limit(tier: str) -> Callable[[Request], None]:
    if tier not in _TIERS:
        raise ValueError(f"Unknown rate-limit tier: {tier}")
    limit, window_seconds = _TIERS[tier]

    def _dependency(request: Request) -> None:
        client_key = request.client.host if request.client else "unknown"
        bucket_key = f"ratelimit:{tier}:{client_key}"
        client = get_redis_client()
        current = client.incr(bucket_key)
        if current == 1:
            client.expire(bucket_key, window_seconds)
        if current > limit:
            retry_after = client.ttl(bucket_key)
            raise RateLimitError(
                "Rate limit exceeded",
                details={"retry_after": max(retry_after, 1), "tier": tier},
            )

    return _dependency
