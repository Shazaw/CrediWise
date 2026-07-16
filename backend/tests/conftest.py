"""Shared pytest fixtures.

Gate tests must be local, reproducible, and free of public network
dependencies (CLAUDE.md §7.1) — required Settings values are set here
directly rather than relying on a real `.env` or reachable Postgres/Redis.
"""

import os
from collections.abc import Iterator

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_NAME", "crediwise_test")
os.environ.setdefault("DB_USER", "crediwise")
os.environ.setdefault("DB_PASSWORD", "crediwise_test")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("STORAGE_ENDPOINT_URL", "http://localhost:9000")
os.environ.setdefault("STORAGE_BUCKET", "crediwise-test")
os.environ.setdefault("STORAGE_ACCESS_KEY", "crediwise")
os.environ.setdefault("STORAGE_SECRET_KEY", "crediwise_test")

# An ephemeral RS256 keypair generated once per test run (PLAN §18.1) — never
# a real/shared key, so no secret ever needs to exist on disk for tests.
_test_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
os.environ.setdefault(
    "SECURITY_JWT_PRIVATE_KEY",
    _test_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode(),
)
os.environ.setdefault(
    "SECURITY_JWT_PUBLIC_KEY",
    _test_key.public_key()
    .public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    .decode(),
)
os.environ.setdefault("SECURITY_JWT_KID", "test-key-1")


@pytest.fixture(autouse=True)
def _fake_redis() -> Iterator[None]:
    """Every rate-limited route uses this in place of a real Redis (PLAN §21.1)."""
    import fakeredis

    from app.core import rate_limit

    rate_limit.set_redis_client(fakeredis.FakeRedis())
    yield
    rate_limit.set_redis_client(None)


@pytest.fixture
def client() -> Iterator[TestClient]:
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
