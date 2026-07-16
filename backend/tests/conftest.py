"""Shared pytest fixtures.

Gate tests must be local, reproducible, and free of public network
dependencies (CLAUDE.md §7.1) — required Settings values are set here
directly rather than relying on a real `.env` or reachable Postgres/Redis.
"""

import os
from collections.abc import Iterator

import pytest
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


@pytest.fixture
def client() -> Iterator[TestClient]:
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
