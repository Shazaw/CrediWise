"""`/api/v1/me` integration tests (PLAN §12.2, §21.1; FR-2)."""

from fastapi.testclient import TestClient

_EMAIL = "budi@example.com"
_PASSWORD = "amanpassword1"


def _register_and_login(client: TestClient) -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": _EMAIL, "password": _PASSWORD})
    tokens = client.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_me_requires_authentication(authed_client: TestClient) -> None:
    response = authed_client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_ERROR"


def test_me_rejects_malformed_authorization_header(authed_client: TestClient) -> None:
    response = authed_client.get("/api/v1/me", headers={"Authorization": "not-bearer x"})
    assert response.status_code == 401


def test_me_returns_current_user(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)
    response = authed_client.get("/api/v1/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == _EMAIL
    assert body["role"] == "USER"
    assert body["profile"] is None


def test_me_profile_patch_creates_and_updates_profile(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)

    first = authed_client.patch(
        "/api/v1/me/profile",
        json={"full_name": "Budi Santoso", "business_type": "Warung Kopi"},
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json()["full_name"] == "Budi Santoso"
    assert first.json()["business_type"] == "Warung Kopi"
    assert first.json()["locale"] == "id-ID"

    second = authed_client.patch(
        "/api/v1/me/profile", json={"full_name": "Budi S."}, headers=headers
    )
    assert second.status_code == 200
    assert second.json()["full_name"] == "Budi S."
    # Fields not sent on the second call are left untouched (partial update).
    assert second.json()["business_type"] == "Warung Kopi"

    me = authed_client.get("/api/v1/me", headers=headers)
    assert me.json()["profile"]["full_name"] == "Budi S."


def test_me_profile_patch_rejects_unknown_fields(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)
    response = authed_client.patch(
        "/api/v1/me/profile", json={"not_a_real_field": "x"}, headers=headers
    )
    assert response.status_code == 422
