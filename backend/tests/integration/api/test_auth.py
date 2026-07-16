"""`/api/v1/auth/*` integration tests (PLAN §12.2, §21.1; FR-1)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

_EMAIL = "ibu.sari@example.com"
_PASSWORD = "amanpassword1"


def _register(client: TestClient, email: str = _EMAIL, password: str = _PASSWORD):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password})


def _login(client: TestClient, email: str = _EMAIL, password: str = _PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_register_creates_user_with_pending_identity_status(authed_client: TestClient) -> None:
    response = _register(authed_client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == _EMAIL
    assert body["role"] == "USER"
    assert body["identity_status"] == "UNVERIFIED"


def test_register_duplicate_email_returns_409(authed_client: TestClient) -> None:
    _register(authed_client)
    response = _register(authed_client)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_register_short_password_returns_422(authed_client: TestClient) -> None:
    response = _register(authed_client, password="short1")
    assert response.status_code == 422


def test_register_password_without_digit_returns_422(authed_client: TestClient) -> None:
    response = _register(authed_client, password="onlyletters")
    assert response.status_code == 422


def test_register_password_without_letter_returns_422(authed_client: TestClient) -> None:
    response = _register(authed_client, password="1234567890")
    assert response.status_code == 422


def test_login_returns_token_pair(authed_client: TestClient) -> None:
    _register(authed_client)
    response = _login(authed_client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 15 * 60
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_invalid_credentials_returns_401(authed_client: TestClient) -> None:
    _register(authed_client)
    response = _login(authed_client, password="wrongpassword1")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_ERROR"


def test_login_unknown_email_returns_401(authed_client: TestClient) -> None:
    response = _login(authed_client, email="nobody@example.com")
    assert response.status_code == 401


def test_refresh_rotates_token(authed_client: TestClient) -> None:
    _register(authed_client)
    tokens = _login(authed_client).json()

    response = authed_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    assert new_tokens["access_token"] != tokens["access_token"]


def test_refresh_with_already_used_token_returns_401(authed_client: TestClient) -> None:
    _register(authed_client)
    tokens = _login(authed_client).json()

    first = authed_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert first.status_code == 200

    replay = authed_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "AUTH_ERROR"


def test_refresh_with_garbage_token_returns_401(authed_client: TestClient) -> None:
    response = authed_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"}
    )
    assert response.status_code == 401


def test_logout_revokes_refresh_token(authed_client: TestClient) -> None:
    _register(authed_client)
    tokens = _login(authed_client).json()

    logout = authed_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert logout.status_code == 204

    replay = authed_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert replay.status_code == 401


def test_logout_requires_authentication(authed_client: TestClient) -> None:
    response = authed_client.post("/api/v1/auth/logout", json={"refresh_token": "whatever"})
    assert response.status_code == 401


def test_login_writes_audit_log_entry(authed_client: TestClient, db_session: Session) -> None:
    register_response = _register(authed_client)
    user_id = register_response.json()["id"]
    _login(authed_client)

    rows = (
        db_session.execute(
            select(AuditLog).where(AuditLog.entity_id == user_id).order_by(AuditLog.created_at)
        )
        .scalars()
        .all()
    )
    actions = [row.action for row in rows]
    assert actions == ["user.registered", "user.logged_in"]
