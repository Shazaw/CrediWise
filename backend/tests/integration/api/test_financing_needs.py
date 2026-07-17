"""`POST/GET /financing-needs` integration tests (PLAN §12.2; FR-2; T4.6)."""

from fastapi.testclient import TestClient

_EMAIL = "financing-need-user@example.com"
_PASSWORD = "amanpassword1"


def _register_and_login(client: TestClient) -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": _EMAIL, "password": _PASSWORD})
    tokens = client.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_create_and_list_financing_need(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)

    response = authed_client.post(
        "/api/v1/financing-needs",
        json={
            "requested_amount": 3_500_000,
            "purpose": "MEDICAL",
            "preferred_tenor_months": 12,
            "urgency": "HIGH",
            "notes": "Emergency medical expense",
        },
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["requested_amount"] == 3_500_000
    assert body["purpose"] == "MEDICAL"
    assert body["urgency"] == "HIGH"

    listing = authed_client.get("/api/v1/financing-needs", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()["items"]) == 1
    assert listing.json()["items"][0]["financing_need_id"] == body["financing_need_id"]


def test_requested_amount_out_of_range_is_rejected(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)

    response = authed_client.post(
        "/api/v1/financing-needs",
        json={
            "requested_amount": 2_000_000_000,
            "purpose": "MEDICAL",
            "preferred_tenor_months": 12,
            "urgency": "HIGH",
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_tenor_out_of_range_is_rejected(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)

    response = authed_client.post(
        "/api/v1/financing-needs",
        json={
            "requested_amount": 1_000_000,
            "purpose": "MEDICAL",
            "preferred_tenor_months": 48,
            "urgency": "HIGH",
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_list_is_scoped_to_the_authenticated_user(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)
    authed_client.post(
        "/api/v1/financing-needs",
        json={
            "requested_amount": 1_000_000,
            "purpose": "MEDICAL",
            "preferred_tenor_months": 6,
            "urgency": "LOW",
        },
        headers=headers,
    )

    authed_client.post(
        "/api/v1/auth/register",
        json={"email": "other-financing-user@example.com", "password": _PASSWORD},
    )
    other_tokens = authed_client.post(
        "/api/v1/auth/login",
        json={"email": "other-financing-user@example.com", "password": _PASSWORD},
    ).json()
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}

    listing = authed_client.get("/api/v1/financing-needs", headers=other_headers)
    assert listing.json()["items"] == []
