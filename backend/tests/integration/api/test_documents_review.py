"""`POST /documents/{id}/review` and `/confirm` integration tests (PLAN
§12.2; FR-14; T3.6).
"""

from fastapi.testclient import TestClient
from tests.support.pdf_builder import bca_style_statement_lines, build_pdf

_EMAIL = "review-user@example.com"
_PASSWORD = "amanpassword1"


def _register_and_login(client: TestClient) -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": _EMAIL, "password": _PASSWORD})
    tokens = client.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _upload_reviewable_document(client: TestClient, headers: dict[str, str]) -> str:
    data = build_pdf(bca_style_statement_lines())
    response = client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", data, "application/pdf")},
        data={"source_type": "ORIGINAL_PDF"},
        headers=headers,
    )
    assert response.json()["status"] == "REVIEW_PENDING"
    return str(response.json()["document_id"])


def test_review_records_corrections_without_mutating_transactions(
    authed_client: TestClient,
) -> None:
    headers = _register_and_login(authed_client)
    document_id = _upload_reviewable_document(authed_client, headers)
    transactions_before = authed_client.get(
        f"/api/v1/documents/{document_id}/transactions", headers=headers
    ).json()["items"]
    flagged_transaction_id = transactions_before[0]["transaction_id"]

    response = authed_client.post(
        f"/api/v1/documents/{document_id}/review",
        json={
            "corrections": [
                {
                    "transaction_id": flagged_transaction_id,
                    "correction_type": "WRONG_CATEGORY",
                    "note": "This looks like a business expense, not personal.",
                },
                {"transaction_id": None, "correction_type": "MISSING_ROW", "note": None},
            ]
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["corrections_recorded"] == 2

    transactions_after = authed_client.get(
        f"/api/v1/documents/{document_id}/transactions", headers=headers
    ).json()["items"]
    assert transactions_after == transactions_before  # raw evidence untouched


def test_review_rejects_unbounded_correction_type(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)
    document_id = _upload_reviewable_document(authed_client, headers)

    response = authed_client.post(
        f"/api/v1/documents/{document_id}/review",
        json={"corrections": [{"transaction_id": None, "correction_type": "NOT_A_REAL_TYPE"}]},
        headers=headers,
    )

    assert response.status_code == 422


def test_review_before_review_pending_is_rejected(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)
    upload = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", b"%PDF-1.4\nnot a real pdf trailer", "application/pdf")},
        data={"source_type": "ORIGINAL_PDF"},
        headers=headers,
    )
    document_id = upload.json()["document_id"]
    assert upload.json()["status"] != "REVIEW_PENDING"

    response = authed_client.post(
        f"/api/v1/documents/{document_id}/review",
        json={"corrections": []},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_confirm_transitions_to_normalizing(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)
    document_id = _upload_reviewable_document(authed_client, headers)

    response = authed_client.post(f"/api/v1/documents/{document_id}/confirm", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "NORMALIZING"

    status_response = authed_client.get(f"/api/v1/documents/{document_id}/status", headers=headers)
    assert status_response.json()["status"] == "NORMALIZING"


def test_confirm_twice_is_rejected(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)
    document_id = _upload_reviewable_document(authed_client, headers)

    first = authed_client.post(f"/api/v1/documents/{document_id}/confirm", headers=headers)
    second = authed_client.post(f"/api/v1/documents/{document_id}/confirm", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 422


def test_review_for_another_users_document_is_404(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)
    document_id = _upload_reviewable_document(authed_client, headers)

    authed_client.post(
        "/api/v1/auth/register", json={"email": "other-reviewer@example.com", "password": _PASSWORD}
    )
    other_tokens = authed_client.post(
        "/api/v1/auth/login",
        json={"email": "other-reviewer@example.com", "password": _PASSWORD},
    ).json()
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}

    response = authed_client.post(f"/api/v1/documents/{document_id}/confirm", headers=other_headers)

    assert response.status_code == 404
