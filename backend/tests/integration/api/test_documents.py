"""`/api/v1/documents` integration tests (PLAN §12.2, §21.1; FR-3/FR-4; T2.7).

Exercises the Sprint 2 exit criterion end to end: "uploading a fixture PDF
stores it, dedups on re-upload, advances to EXTRACTING" (PLAN §25 Sprint 2).

Since Sprint 3, `tests/integration/conftest.py`'s autouse
`_inline_document_processing` fixture runs the *entire* pipeline
(`SECURITY_CHECK -> EXTRACTING -> VERIFYING -> REVIEW_PENDING`, or
`-> UNSUPPORTED_FORMAT`) synchronously within the same request, not just the
Sprint 2 `SECURITY_CHECK -> EXTRACTING` edge — so most fixtures here (a
content-less blank PDF) now resolve to `UNSUPPORTED_FORMAT`, which is the
*correct* new terminal status for a document with no recognizable statement
layout (FR-4 EC), not a regression. Only
`test_clean_bca_pdf_upload_progresses_to_review_pending` uses a real
BCA-style fixture (`tests/support/pdf_builder.py`) to exercise the full
happy path; the rest intentionally test upload/dedup/ownership/auth
semantics that are orthogonal to extraction quality.
"""

import io

from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter
from sqlalchemy.orm import Session
from tests.support.pdf_builder import bca_style_statement_lines, build_pdf

from app.models.enums import AccountTypeEnum, ConnectionTypeEnum
from app.models.financial_account import FinancialAccount
from app.models.user import User

_EMAIL = "sari@example.com"
_PASSWORD = "amanpassword1"


def _register_and_login(client: TestClient) -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": _EMAIL, "password": _PASSWORD})
    tokens = client.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _clean_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _malicious_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_js('app.alert("hi");')
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _encrypted_pdf_bytes(password: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt(user_password=password, owner_password=None)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format="PNG")
    return buf.getvalue()


def test_upload_requires_authentication(authed_client: TestClient) -> None:
    response = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", _clean_pdf_bytes(), "application/pdf")},
        data={"source_type": "ORIGINAL_PDF"},
    )
    assert response.status_code == 401


def test_blank_pdf_upload_is_unsupported_format(authed_client: TestClient) -> None:
    """A content-less PDF passes file-security but has no recognizable
    statement layout (FR-4 EC) — Sprint 3's pipeline runs synchronously in
    tests, so the response already reflects the final terminal status."""
    headers = _register_and_login(authed_client)

    response = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", _clean_pdf_bytes(), "application/pdf")},
        data={"source_type": "ORIGINAL_PDF"},
        headers=headers,
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "UNSUPPORTED_FORMAT"
    assert body["duplicate"] is False
    assert body["poll"] == f"/api/v1/documents/{body['document_id']}/status"

    status_response = authed_client.get(body["poll"], headers=headers)
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["status"] == "UNSUPPORTED_FORMAT"
    assert status_body["file_name"] == "statement.pdf"
    assert status_body["mime_type"] == "application/pdf"
    assert status_body["page_count"] == 1


def test_clean_bca_pdf_upload_progresses_to_review_pending(authed_client: TestClient) -> None:
    """PLAN §25 Sprint 3 exit criterion: "clean fixture -> HIGH confidence
    with reasons" — this exercises the same happy path end to end via the
    real API/pipeline wiring (engine-level HIGH-band assertions live in
    `tests/unit/engines/test_trust_layer.py`). A HIGH band needs a profile
    name matching the statement (ownership) and >=6 months of coverage
    (completeness, §5.2) — a single-month statement with no declared name
    is deliberately MEDIUM at most (FR-5 EC), covered separately by
    `test_single_month_pdf_without_profile_name_scores_medium`.
    """
    headers = _register_and_login(authed_client)
    authed_client.patch("/api/v1/me/profile", json={"full_name": "Budi Santoso"}, headers=headers)
    data = build_pdf(bca_style_statement_lines(period_start="01/01/2026", period_end="30/06/2026"))

    response = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", data, "application/pdf")},
        data={"source_type": "ORIGINAL_PDF"},
        headers=headers,
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "REVIEW_PENDING"

    verification = authed_client.get(
        f"/api/v1/documents/{body['document_id']}/verification", headers=headers
    )
    assert verification.status_code == 200
    assert verification.json()["band"] == "HIGH"
    assert verification.json()["model_version_id"]
    assert verification.json()["ai_signal"] == "DISABLED"

    transactions = authed_client.get(
        f"/api/v1/documents/{body['document_id']}/transactions", headers=headers
    )
    assert transactions.status_code == 200
    assert len(transactions.json()["items"]) == 4  # excludes the Rp0 opening-balance row
    assert transactions.json()["items"][0]["normalized_description"]
    assert transactions.json()["items"][0]["is_duplicate"] is False


def test_single_month_pdf_without_profile_name_scores_medium(authed_client: TestClient) -> None:
    """No profile name set (ownership unverifiable) + a single-month
    statement (low completeness) keeps the band below HIGH, with a
    recommendation and a non-empty reason-code list (FR-5 AC4)."""
    headers = _register_and_login(authed_client)
    data = build_pdf(bca_style_statement_lines())

    response = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", data, "application/pdf")},
        data={"source_type": "ORIGINAL_PDF"},
        headers=headers,
    )
    assert response.json()["status"] == "REVIEW_PENDING"

    verification = authed_client.get(
        f"/api/v1/documents/{response.json()['document_id']}/verification", headers=headers
    )
    body = verification.json()
    assert body["band"] != "HIGH"
    assert body["recommendation"] is not None
    assert len(body["reason_codes"]) >= 3


def test_reupload_same_bytes_dedups_to_existing_document(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)
    data = _clean_pdf_bytes()

    first = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", data, "application/pdf")},
        data={"source_type": "ORIGINAL_PDF"},
        headers=headers,
    )
    second = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement-renamed.pdf", data, "application/pdf")},
        data={"source_type": "ORIGINAL_PDF"},
        headers=headers,
    )

    assert second.status_code == 202
    assert second.json()["duplicate"] is True
    assert second.json()["document_id"] == first.json()["document_id"]


def test_malicious_pdf_is_rejected_security(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)

    response = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", _malicious_pdf_bytes(), "application/pdf")},
        data={"source_type": "ORIGINAL_PDF"},
        headers=headers,
    )

    assert response.status_code == 202
    assert response.json()["status"] == "REJECTED_SECURITY"


def test_oversized_upload_is_validation_failed(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)
    oversized = _clean_pdf_bytes() + (b"0" * 20 * 1024 * 1024)

    response = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", oversized, "application/pdf")},
        data={"source_type": "ORIGINAL_PDF"},
        headers=headers,
    )

    assert response.status_code == 202
    assert response.json()["status"] == "VALIDATION_FAILED"


def test_unsupported_mime_is_rejected_with_415(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)

    response = authed_client.post(
        "/api/v1/documents",
        files={"file": ("script.exe", b"not a real exe", "application/x-msdownload")},
        data={"source_type": "ORIGINAL_PDF"},
        headers=headers,
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_encrypted_pdf_without_password_prompts_422(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)

    response = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", _encrypted_pdf_bytes("rahasia123"), "application/pdf")},
        data={"source_type": "ORIGINAL_PDF"},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PDF_PASSWORD_REQUIRED"


def test_encrypted_pdf_with_wrong_password_422(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)

    response = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", _encrypted_pdf_bytes("rahasia123"), "application/pdf")},
        data={"source_type": "ORIGINAL_PDF", "pdf_password": "wrong"},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PDF_PASSWORD"


def test_encrypted_pdf_with_correct_password_succeeds(authed_client: TestClient) -> None:
    """The password/decryption path succeeds (202, not a 422) — the blank
    decrypted content then has no recognizable statement layout, same as
    `test_blank_pdf_upload_is_unsupported_format`."""
    headers = _register_and_login(authed_client)

    response = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", _encrypted_pdf_bytes("rahasia123"), "application/pdf")},
        data={"source_type": "ORIGINAL_PDF", "pdf_password": "rahasia123"},
        headers=headers,
    )

    assert response.status_code == 202
    assert response.json()["status"] == "UNSUPPORTED_FORMAT"


def test_png_upload_succeeds(authed_client: TestClient) -> None:
    """The upload itself succeeds (202) — no Tesseract binary is installed
    in this sandbox/CI (see `docs/handoffs/`), so OCR degrades to
    `UNSUPPORTED_FORMAT` rather than a crash (FR-4 EC), which is itself the
    behavior under test here."""
    headers = _register_and_login(authed_client)

    response = authed_client.post(
        "/api/v1/documents",
        files={"file": ("screenshot.png", _png_bytes(), "image/png")},
        data={"source_type": "SCREENSHOT"},
        headers=headers,
    )

    assert response.status_code == 202
    assert response.json()["status"] == "UNSUPPORTED_FORMAT"


def test_upload_with_owned_financial_account_succeeds(
    authed_client: TestClient, db_session: Session
) -> None:
    headers = _register_and_login(authed_client)
    user = db_session.query(User).filter(User.email == _EMAIL).one()
    account = FinancialAccount(
        user_id=user.id,
        account_type=AccountTypeEnum.BANK,
        connection_type=ConnectionTypeEnum.UPLOAD,
    )
    db_session.add(account)
    db_session.commit()

    response = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", _clean_pdf_bytes(), "application/pdf")},
        data={"source_type": "ORIGINAL_PDF", "financial_account_id": str(account.id)},
        headers=headers,
    )

    assert response.status_code == 202
    assert response.json()["status"] == "UNSUPPORTED_FORMAT"


def test_upload_with_unowned_financial_account_is_404(
    authed_client: TestClient, db_session: Session
) -> None:
    headers = _register_and_login(authed_client)
    other_user = User(email="not-me@example.com", password_hash="x")
    db_session.add(other_user)
    db_session.flush()
    account = FinancialAccount(
        user_id=other_user.id,
        account_type=AccountTypeEnum.BANK,
        connection_type=ConnectionTypeEnum.UPLOAD,
    )
    db_session.add(account)
    db_session.commit()

    response = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", _clean_pdf_bytes(), "application/pdf")},
        data={"source_type": "ORIGINAL_PDF", "financial_account_id": str(account.id)},
        headers=headers,
    )

    assert response.status_code == 404


def test_status_for_unknown_document_is_404(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)
    response = authed_client.get(
        "/api/v1/documents/00000000-0000-0000-0000-000000000000/status", headers=headers
    )
    assert response.status_code == 404


def test_status_for_another_users_document_is_404(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client)
    upload = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", _clean_pdf_bytes(), "application/pdf")},
        data={"source_type": "ORIGINAL_PDF"},
        headers=headers,
    )
    document_id = upload.json()["document_id"]

    authed_client.post(
        "/api/v1/auth/register", json={"email": "other@example.com", "password": _PASSWORD}
    )
    other_tokens = authed_client.post(
        "/api/v1/auth/login", json={"email": "other@example.com", "password": _PASSWORD}
    ).json()
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}

    response = authed_client.get(f"/api/v1/documents/{document_id}/status", headers=other_headers)
    assert response.status_code == 404
