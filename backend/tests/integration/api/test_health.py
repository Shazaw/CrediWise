"""Liveness/readiness endpoint tests (PLAN §20.3, Sprint 0 exit criteria)."""

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_response_carries_correlation_id_header(client: TestClient) -> None:
    response = client.get("/health")
    assert "X-Correlation-Id" in response.headers


def test_health_echoes_supplied_correlation_id(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Correlation-Id": "test-corr-id"})
    assert response.headers["X-Correlation-Id"] == "test-corr-id"


def test_ready_reports_ok_when_dependencies_reachable(client: TestClient) -> None:
    with (
        patch("app.main._check_db", return_value=True),
        patch("app.main._check_redis", return_value=True),
    ):
        response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "checks": {"db": True, "redis": True}}


def test_ready_reports_unavailable_when_db_unreachable(client: TestClient) -> None:
    with (
        patch("app.main._check_db", return_value=False),
        patch("app.main._check_redis", return_value=True),
    ):
        response = client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["checks"] == {"db": False, "redis": True}
