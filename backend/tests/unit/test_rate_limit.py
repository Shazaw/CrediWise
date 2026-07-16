"""Rate-limit dependency unit tests (PLAN §12.1) — `fakeredis`, no FastAPI DI."""

from collections.abc import Iterator

import fakeredis
import pytest
from fastapi import Request

from app.core import rate_limit
from app.core.errors import RateLimitError


@pytest.fixture(autouse=True)
def _isolated_fake_redis() -> Iterator[None]:
    rate_limit.set_redis_client(fakeredis.FakeRedis())
    yield
    rate_limit.set_redis_client(None)


def _fake_request(ip: str = "203.0.113.1") -> Request:
    scope = {"type": "http", "client": (ip, 12345)}
    return Request(scope)


def test_rate_limit_rejects_unknown_tier() -> None:
    with pytest.raises(ValueError):
        rate_limit.rate_limit("not-a-real-tier")


def test_rate_limit_allows_requests_within_the_limit() -> None:
    dependency = rate_limit.rate_limit("auth")
    request = _fake_request()
    for _ in range(10):
        dependency(request)  # 10/min tier — should not raise


def test_rate_limit_blocks_requests_over_the_limit() -> None:
    dependency = rate_limit.rate_limit("auth")
    request = _fake_request()
    for _ in range(10):
        dependency(request)
    with pytest.raises(RateLimitError) as exc_info:
        dependency(request)
    assert exc_info.value.details["retry_after"] >= 1
    assert exc_info.value.details["tier"] == "auth"


def test_rate_limit_tracks_separate_buckets_per_client_ip() -> None:
    dependency = rate_limit.rate_limit("auth")
    client_a = _fake_request("203.0.113.1")
    client_b = _fake_request("203.0.113.2")
    for _ in range(10):
        dependency(client_a)
    dependency(client_b)  # different IP — its own bucket, should not raise


def test_rate_limit_tracks_separate_buckets_per_tier() -> None:
    auth_dependency = rate_limit.rate_limit("auth")
    general_dependency = rate_limit.rate_limit("general")
    request = _fake_request()
    for _ in range(10):
        auth_dependency(request)
    general_dependency(request)  # different tier — its own bucket, should not raise
