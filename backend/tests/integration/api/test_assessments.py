"""`POST/GET /assessments[...]` integration tests (PLAN §12.2, §8.3; FR-8,
FR-9, FR-12, FR-18; T4.6).

`_inline_normalization_and_analysis` (`tests/integration/conftest.py`) runs
the `NORMALIZATION` and `ANALYSIS` pipeline stages synchronously within the
same request/session, so by the time `POST /documents/{id}/confirm` and
`POST /assessments` return, the document is already `ANALYZING`/`COMPLETE`
and the assessment is already `COMPLETE` -- no polling needed in tests.
"""

from fastapi.testclient import TestClient
from tests.support.pdf_builder import bca_style_statement_lines, build_pdf

_EMAIL = "assessment-user@example.com"
_PASSWORD = "amanpassword1"

_TWO_MONTH_ROWS = [
    "01/05/2026|08:00|Saldo Awal|CR|0|4000000",
    "05/05/2026|09:15|TRSF E-BANKING CR GAJI|CR|3000000|7000000",
    "10/05/2026|12:30|LISTRIK PLN BULANAN|DB|300000|6700000",
    "05/06/2026|09:15|TRSF E-BANKING CR GAJI|CR|3000000|9700000",
    "10/06/2026|12:30|LISTRIK PLN BULANAN|DB|300000|9400000",
]

_ZERO_CASH_FLOW_ROWS = [
    "01/06/2026|08:00|Saldo Awal|CR|0|1000000",
    "05/06/2026|09:15|TRSF E-BANKING CR GAJI|CR|1000000|2000000",
    "10/06/2026|12:30|LISTRIK PLN BULANAN|DB|1200000|800000",
]


def _register_and_login(client: TestClient, email: str = _EMAIL) -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": email, "password": _PASSWORD})
    tokens = client.post("/api/v1/auth/login", json={"email": email, "password": _PASSWORD}).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _create_financing_need(
    client: TestClient, headers: dict[str, str], *, amount: int = 3_500_000
) -> str:
    response = client.post(
        "/api/v1/financing-needs",
        json={
            "requested_amount": amount,
            "purpose": "MEDICAL",
            "preferred_tenor_months": 12,
            "urgency": "HIGH",
        },
        headers=headers,
    )
    return str(response.json()["financing_need_id"])


def _upload_and_confirm_document(
    client: TestClient,
    headers: dict[str, str],
    *,
    rows: list[str],
    holder_name: str = "BUDI SANTOSO",
) -> str:
    data = build_pdf(
        bca_style_statement_lines(
            holder_name=holder_name, period_start="01/05/2026", period_end="30/06/2026", rows=rows
        )
    )
    upload = client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", data, "application/pdf")},
        data={"source_type": "ORIGINAL_PDF"},
        headers=headers,
    )
    assert upload.json()["status"] == "REVIEW_PENDING"
    document_id = str(upload.json()["document_id"])

    confirm = client.post(f"/api/v1/documents/{document_id}/confirm", headers=headers)
    assert confirm.json()["status"] == "ANALYZING"
    return document_id


def test_full_pipeline_produces_complete_assessment_with_twin_risk_safe_borrowing(
    authed_client: TestClient,
) -> None:
    headers = _register_and_login(authed_client)
    financing_need_id = _create_financing_need(authed_client, headers)
    document_id = _upload_and_confirm_document(authed_client, headers, rows=_TWO_MONTH_ROWS)

    create_response = authed_client.post(
        "/api/v1/assessments",
        json={"financing_need_id": financing_need_id, "source_document_ids": [document_id]},
        headers=headers,
    )
    assert create_response.status_code == 202
    assessment_id = create_response.json()["assessment_id"]
    assert create_response.json()["status"] == "COMPLETE"

    detail = authed_client.get(f"/api/v1/assessments/{assessment_id}", headers=headers).json()
    assert detail["status"] == "COMPLETE"
    assert detail["indicative_risk_band"] in {"A", "B", "C", "D"}
    assert detail["model_confidence"] in {"HIGH", "MEDIUM", "LOW"}
    assert detail["safe_loan_amount"] > 0
    assert detail["maximum_safe_instalment"] > 0
    assert detail["required_liquidity_buffer"] > 0
    assert detail["recommended_tenor_months"] in {6, 9, 12}

    twin = authed_client.get(f"/api/v1/assessments/{assessment_id}/twin", headers=headers).json()
    assert twin["median_income"] == 3_000_000
    assert twin["essential_expenses"] == 300_000
    assert twin["months_covered"] == 2
    assert twin["coverage_flag"] == "SUFFICIENT"
    assert len(twin["monthly_snapshots"]) == 2
    assert len(twin["income_sources"]) == 1

    recommendation = authed_client.get(
        f"/api/v1/assessments/{assessment_id}/recommendation", headers=headers
    ).json()
    assert recommendation["safe_loan_amount"] > 0
    assert recommendation["required_liquidity_buffer"] > 0
    assert any(r["code"].startswith("SAFE_BORROWING_") for r in recommendation["reason_codes"])

    dashboard = authed_client.get(
        f"/api/v1/assessments/{assessment_id}/dashboard", headers=headers
    ).json()
    assert dashboard["positioning_notice"].startswith("Estimated financial-risk")
    assert dashboard["twin"] is not None
    assert dashboard["twin"]["median_income"] == 3_000_000
    assert dashboard["safe_borrowing"]["amount"] > 0
    assert dashboard["safe_borrowing"]["required_liquidity_buffer"] > 0
    assert dashboard["data_confidence"]["score"] is not None
    assert dashboard["model_version_id"]
    dashboard_codes = (
        dashboard["data_confidence"]["reason_codes"]
        + dashboard["risk_band"]["positive_reason_codes"]
        + dashboard["risk_band"]["risk_reason_codes"]
    )
    assert any(reason["code"].startswith("RISK_") for reason in dashboard_codes)
    assert any(reason["code"].startswith("SAFE_BORROWING_") for reason in dashboard_codes)

    lineage = authed_client.get(
        f"/api/v1/assessments/{assessment_id}/lineage", headers=headers
    ).json()
    assert lineage["document_ids"] == [document_id]
    assert len(lineage["transaction_ids"]) == 4  # GAJI + LISTRIK per month, 2 months
    assert lineage["engine_config_hash"]

    # Document included in a completed assessment is marked COMPLETE (PLAN §8.2).
    status_response = authed_client.get(f"/api/v1/documents/{document_id}/status", headers=headers)
    assert status_response.json()["status"] == "COMPLETE"


def test_zero_free_cash_flow_yields_zero_safe_loan_amount(authed_client: TestClient) -> None:
    """FR-9 EC: "free cash flow <= 0 -> safe amount = Rp0"."""
    headers = _register_and_login(authed_client, email="zero-cash-flow-user@example.com")
    financing_need_id = _create_financing_need(authed_client, headers)
    document_id = _upload_and_confirm_document(authed_client, headers, rows=_ZERO_CASH_FLOW_ROWS)

    create_response = authed_client.post(
        "/api/v1/assessments",
        json={"financing_need_id": financing_need_id, "source_document_ids": [document_id]},
        headers=headers,
    )
    assessment_id = create_response.json()["assessment_id"]

    detail = authed_client.get(f"/api/v1/assessments/{assessment_id}", headers=headers).json()
    assert detail["safe_loan_amount"] == 0
    assert detail["maximum_safe_instalment"] == 0
    assert detail["required_liquidity_buffer"] > 0


def test_create_assessment_rejects_document_not_yet_analyzing(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client, email="not-ready-user@example.com")
    financing_need_id = _create_financing_need(authed_client, headers)
    data = build_pdf(bca_style_statement_lines())
    upload = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", data, "application/pdf")},
        data={"source_type": "ORIGINAL_PDF"},
        headers=headers,
    )
    document_id = str(upload.json()["document_id"])  # still REVIEW_PENDING, not confirmed

    response = authed_client.post(
        "/api/v1/assessments",
        json={"financing_need_id": financing_need_id, "source_document_ids": [document_id]},
        headers=headers,
    )

    assert response.status_code == 422


def test_create_assessment_with_unknown_financing_need_is_404(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client, email="unknown-need-user@example.com")
    document_id = _upload_and_confirm_document(authed_client, headers, rows=_TWO_MONTH_ROWS)

    response = authed_client.post(
        "/api/v1/assessments",
        json={
            "financing_need_id": "00000000-0000-0000-0000-000000000000",
            "source_document_ids": [document_id],
        },
        headers=headers,
    )

    assert response.status_code == 404


def test_create_assessment_rejects_another_users_document(authed_client: TestClient) -> None:
    owner_headers = _register_and_login(authed_client, email="doc-owner@example.com")
    document_id = _upload_and_confirm_document(authed_client, owner_headers, rows=_TWO_MONTH_ROWS)

    other_headers = _register_and_login(authed_client, email="doc-intruder@example.com")
    financing_need_id = _create_financing_need(authed_client, other_headers)

    response = authed_client.post(
        "/api/v1/assessments",
        json={"financing_need_id": financing_need_id, "source_document_ids": [document_id]},
        headers=other_headers,
    )

    assert response.status_code == 404


def test_get_assessment_for_another_user_is_404(authed_client: TestClient) -> None:
    owner_headers = _register_and_login(authed_client, email="assessment-owner@example.com")
    financing_need_id = _create_financing_need(authed_client, owner_headers)
    document_id = _upload_and_confirm_document(authed_client, owner_headers, rows=_TWO_MONTH_ROWS)
    create_response = authed_client.post(
        "/api/v1/assessments",
        json={"financing_need_id": financing_need_id, "source_document_ids": [document_id]},
        headers=owner_headers,
    )
    assessment_id = create_response.json()["assessment_id"]

    other_headers = _register_and_login(authed_client, email="assessment-intruder@example.com")
    response = authed_client.get(f"/api/v1/assessments/{assessment_id}", headers=other_headers)

    assert response.status_code == 404
