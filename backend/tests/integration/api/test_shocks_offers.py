"""`/assessments/{id}/simulate|shocks|offers` + `/offers/{id}/safety`
integration tests (PLAN §12.2, §8.3; FR-10, FR-11; T5.2/T5.4).

Reuses the `_inline_normalization_and_analysis` autouse fixture
(`tests/integration/conftest.py`) so by the time `POST /assessments` returns,
the assessment is already `COMPLETE` with `shock_scenarios` persisted -- no
polling needed in tests (same pattern as `test_assessments.py`).
"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.support.pdf_builder import bca_style_statement_lines, build_pdf

from app.core.errors import ReassessmentRequiredError
from app.models.assessment import Assessment
from app.models.cash_flow_event import CashFlowEvent
from app.models.enums import AssessmentStatusEnum, DirEnum, ModelStatusEnum
from app.models.lender_offer import LenderOffer
from app.models.model_version import ModelVersion
from app.repositories.financial_profile_repository import FinancialProfileRepository
from app.services.assessment_service import run_assessment_analysis

_PASSWORD = "amanpassword1"

_TWO_MONTH_ROWS = [
    "01/05/2026|08:00|Saldo Awal|CR|0|4000000",
    "05/05/2026|09:15|TRSF E-BANKING CR GAJI|CR|3000000|7000000",
    "10/05/2026|12:30|LISTRIK PLN BULANAN|DB|300000|6700000",
    "05/06/2026|09:15|TRSF E-BANKING CR GAJI|CR|3000000|9700000",
    "10/06/2026|12:30|LISTRIK PLN BULANAN|DB|300000|9400000",
]


def _register_and_login(client: TestClient, email: str) -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": email, "password": _PASSWORD})
    tokens = client.post("/api/v1/auth/login", json={"email": email, "password": _PASSWORD}).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _create_financing_need(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/v1/financing-needs",
        json={
            "requested_amount": 3_500_000,
            "purpose": "MEDICAL",
            "preferred_tenor_months": 12,
            "urgency": "HIGH",
        },
        headers=headers,
    )
    return str(response.json()["financing_need_id"])


def _upload_and_confirm_document(client: TestClient, headers: dict[str, str]) -> str:
    data = build_pdf(
        bca_style_statement_lines(
            holder_name="BUDI SANTOSO",
            period_start="01/05/2026",
            period_end="30/06/2026",
            rows=_TWO_MONTH_ROWS,
        )
    )
    upload = client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", data, "application/pdf")},
        data={"source_type": "ORIGINAL_PDF"},
        headers=headers,
    )
    document_id = str(upload.json()["document_id"])
    client.post(f"/api/v1/documents/{document_id}/confirm", headers=headers)
    return document_id


def _create_complete_assessment(client: TestClient, email: str) -> tuple[dict[str, str], str]:
    headers = _register_and_login(client, email)
    financing_need_id = _create_financing_need(client, headers)
    document_id = _upload_and_confirm_document(client, headers)
    create_response = client.post(
        "/api/v1/assessments",
        json={"financing_need_id": financing_need_id, "source_document_ids": [document_id]},
        headers=headers,
    )
    assessment_id = create_response.json()["assessment_id"]
    assert create_response.json()["status"] == "COMPLETE"
    return headers, assessment_id


def _mark_assessment_historical(db_session: Session, assessment_id: str) -> Assessment:
    historical_model = ModelVersion(
        model_name="crediwise-core",
        version="v1",
        status=ModelStatusEnum.RETIRED,
        config_hash="1" * 64,
        released_at=datetime.now(UTC),
    )
    db_session.add(historical_model)
    db_session.flush()
    assessment = db_session.get(Assessment, assessment_id)
    assert assessment is not None
    assessment.model_version_id = historical_model.id
    db_session.flush()
    return assessment


def test_shocks_endpoint_returns_seven_scenarios_and_resilience_score(
    authed_client: TestClient,
) -> None:
    headers, assessment_id = _create_complete_assessment(authed_client, "shocks-user@example.com")

    response = authed_client.get(f"/api/v1/assessments/{assessment_id}/shocks", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["resilience_score"] is not None
    assert body["resilience_score_scope"] == "CANONICAL_BATTERY"
    assert body["band"] in {"STRONG", "MODERATE", "FRAGILE"}
    assert len(body["scenarios"]) == 7
    scenario_types = {s["scenario_type"] for s in body["scenarios"]}
    assert scenario_types == {
        "INCOME_DROP_10",
        "INCOME_DROP_20",
        "INCOME_DROP_30",
        "DELAYED_INCOME",
        "EMERGENCY_EXPENSE",
        "INCOME_SOURCE_LOSS",
        "WEAKEST_MONTH_REPLAY",
    }
    for scenario in body["scenarios"]:
        assert scenario["affordability_status"] in {"SURVIVABLE", "STRAINED", "DEFICIT"}
        assert isinstance(scenario["required_buffer_breached"], bool)
        assert scenario["required_liquidity_buffer"] == body["required_liquidity_buffer"]
        assert [p["sequence"] for p in scenario["projection_points"]] == list(
            range(len(scenario["projection_points"]))
        )
    assert len(body["reason_codes"]) >= 3
    assert body["model_version"]
    assert len(body["config_hash"]) == 64
    assert body["explanation"]


def test_dashboard_shock_resilience_card_matches_shocks_endpoint(authed_client: TestClient) -> None:
    headers, assessment_id = _create_complete_assessment(
        authed_client, "dashboard-shock-user@example.com"
    )

    dashboard = authed_client.get(
        f"/api/v1/assessments/{assessment_id}/dashboard", headers=headers
    ).json()
    shocks = authed_client.get(
        f"/api/v1/assessments/{assessment_id}/shocks", headers=headers
    ).json()

    assert dashboard["shock_resilience"]["score"] == shocks["resilience_score"]
    assert dashboard["shock_resilience"]["band"] == shocks["band"]
    # Shock reason codes belong to their own card, not the Risk Band card.
    risk_codes = {
        c["code"]
        for c in (
            dashboard["risk_band"]["positive_reason_codes"]
            + dashboard["risk_band"]["risk_reason_codes"]
        )
    }
    assert not any(code.startswith("SHOCK_") for code in risk_codes)


def test_simulate_shock_is_not_persisted(authed_client: TestClient) -> None:
    headers, assessment_id = _create_complete_assessment(authed_client, "simulate-user@example.com")
    before = authed_client.get(
        f"/api/v1/assessments/{assessment_id}/shocks", headers=headers
    ).json()

    response = authed_client.post(
        f"/api/v1/assessments/{assessment_id}/simulate",
        json={
            "income_drop_pct": 50,
            "emergency_expense": 2_000_000,
            "proposed_instalment": 200_000,
        },
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert any(s["scenario_type"] == "CUSTOM" for s in body["scenarios"])
    assert body["proposed_instalment"] == 200_000
    assert body["resilience_score_scope"] == "CANONICAL_BATTERY"
    assert any(r["code"] == "SHOCK_CUSTOM_STANDALONE" for r in body["reason_codes"])

    after = authed_client.get(f"/api/v1/assessments/{assessment_id}/shocks", headers=headers).json()
    assert after == before  # /simulate never mutates the persisted battery


def test_simulate_shock_rejects_out_of_range_income_drop(authed_client: TestClient) -> None:
    headers, assessment_id = _create_complete_assessment(
        authed_client, "simulate-invalid-user@example.com"
    )

    response = authed_client.post(
        f"/api/v1/assessments/{assessment_id}/simulate",
        json={"income_drop_pct": 150},
        headers=headers,
    )

    assert response.status_code == 422


def test_simulate_shock_rejects_negative_emergency_expense(authed_client: TestClient) -> None:
    headers, assessment_id = _create_complete_assessment(
        authed_client, "simulate-negative-user@example.com"
    )

    response = authed_client.post(
        f"/api/v1/assessments/{assessment_id}/simulate",
        json={"emergency_expense": -1},
        headers=headers,
    )

    assert response.status_code == 422


def test_create_offers_seeds_three_ranked_offers(authed_client: TestClient) -> None:
    headers, assessment_id = _create_complete_assessment(authed_client, "offers-user@example.com")

    response = authed_client.post(f"/api/v1/assessments/{assessment_id}/offers", headers=headers)

    assert response.status_code == 201
    body = response.json()
    offers = body["offers"]
    assert len(offers) == 3
    ranks = [o["rank"] for o in offers]
    assert ranks == sorted(ranks)
    scores = [float(o["safe_offer_score"]) for o in offers]
    assert scores == sorted(scores, reverse=True)
    for o in offers:
        assert o["offer_source"] == "SIMULATED"
        assert o["simulation_notice"].startswith("SIMULATED")
        assert o["lender"]["regulatory_status"] == "SIMULATED_REGULATED_PROVIDER"
        assert o["safety_band"] in {"SAFE", "CAUTION", "UNSAFE"}
        assert o["payment_schedule"]
        assert o["payment_schedule"][-1]["remaining_balance"] == 0
        assert o["nominal_rate_basis"] == "ANNUAL_NOMINAL"
        assert isinstance(o["refinancing_dependency"], bool)
        assert set(o["remaining_essential_expense_coverage"]) == {"amount", "ratio"}
        assert len(o["reason_codes"]) >= 3
        assert o["model_version"]
        assert len(o["config_hash"]) == 64
        if o["late_penalty_terms"] is not None:
            assert set(o["late_penalty_terms"]) == {
                "trigger_days",
                "rate",
                "amount",
                "basis",
            }

    # The EXTENDED_TENOR template principal exceeds the requested amount and
    # omits late-penalty disclosure -- exercises FR-11 EC's dangerous-offer
    # warning path.
    assert any(o["warning_flags"] for o in offers)


def test_get_offers_returns_the_same_ranking_after_seeding(authed_client: TestClient) -> None:
    headers, assessment_id = _create_complete_assessment(
        authed_client, "offers-get-user@example.com"
    )
    authed_client.post(f"/api/v1/assessments/{assessment_id}/offers", headers=headers)

    response = authed_client.get(f"/api/v1/assessments/{assessment_id}/offers", headers=headers)

    assert response.status_code == 200
    offers = response.json()["offers"]
    assert len(offers) == 3
    assert [o["rank"] for o in offers] == [1, 2, 3]


def test_create_offers_is_idempotent_and_returns_same_rows(authed_client: TestClient) -> None:
    headers, assessment_id = _create_complete_assessment(
        authed_client, "offers-idempotent-user@example.com"
    )
    first = authed_client.post(
        f"/api/v1/assessments/{assessment_id}/offers", headers=headers
    ).json()["offers"]
    second = authed_client.post(
        f"/api/v1/assessments/{assessment_id}/offers", headers=headers
    ).json()["offers"]
    persisted = authed_client.get(
        f"/api/v1/assessments/{assessment_id}/offers", headers=headers
    ).json()["offers"]

    assert [offer["offer_id"] for offer in second] == [offer["offer_id"] for offer in first]
    assert [offer["offer_id"] for offer in persisted] == [offer["offer_id"] for offer in first]
    assert len(persisted) == 3
    ranking = [(offer["safe_offer_score"], offer["effective_annual_rate"]) for offer in persisted]
    assert ranking == sorted(
        ranking,
        key=lambda value: (
            -float(value[0]),
            float(value[1]) if value[1] is not None else float("inf"),
        ),
    )


def test_legacy_keyless_offer_batch_is_preserved_but_replaced_for_api_use(
    authed_client: TestClient, db_session: Session
) -> None:
    headers, assessment_id = _create_complete_assessment(
        authed_client, "offers-legacy-user@example.com"
    )
    first = authed_client.post(
        f"/api/v1/assessments/{assessment_id}/offers", headers=headers
    ).json()["offers"]
    rows = list(
        db_session.execute(
            select(LenderOffer).where(LenderOffer.assessment_id == assessment_id)
        ).scalars()
    )
    for row in rows:
        row.canonical_template_key = None
    db_session.flush()

    second_response = authed_client.post(
        f"/api/v1/assessments/{assessment_id}/offers", headers=headers
    )

    assert second_response.status_code == 201
    second = second_response.json()["offers"]
    assert len(second) == 3
    assert {offer["offer_id"] for offer in first}.isdisjoint(
        {offer["offer_id"] for offer in second}
    )
    assert (
        len(
            list(
                db_session.execute(
                    select(LenderOffer).where(LenderOffer.assessment_id == assessment_id)
                ).scalars()
            )
        )
        == 6
    )


def test_partial_canonical_offer_set_requires_reassessment(
    authed_client: TestClient, db_session: Session
) -> None:
    headers, assessment_id = _create_complete_assessment(
        authed_client, "offers-partial-user@example.com"
    )
    authed_client.post(f"/api/v1/assessments/{assessment_id}/offers", headers=headers)
    row = db_session.execute(
        select(LenderOffer).where(LenderOffer.assessment_id == assessment_id).limit(1)
    ).scalar_one()
    row.canonical_template_key = None
    db_session.flush()

    response = authed_client.get(f"/api/v1/assessments/{assessment_id}/offers", headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "REASSESSMENT_REQUIRED"


def test_offer_creation_rejects_historical_model_lineage(
    authed_client: TestClient, db_session: Session
) -> None:
    headers, assessment_id = _create_complete_assessment(
        authed_client, "offers-old-model-user@example.com"
    )
    _mark_assessment_historical(db_session, assessment_id)

    response = authed_client.post(f"/api/v1/assessments/{assessment_id}/offers", headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "REASSESSMENT_REQUIRED"


def test_historical_completed_assessment_rejects_current_shock_config(
    authed_client: TestClient, db_session: Session
) -> None:
    headers, assessment_id = _create_complete_assessment(
        authed_client, "shocks-old-complete-user@example.com"
    )
    _mark_assessment_historical(db_session, assessment_id)

    stored = authed_client.get(f"/api/v1/assessments/{assessment_id}/shocks", headers=headers)
    simulated = authed_client.post(
        f"/api/v1/assessments/{assessment_id}/simulate",
        json={"proposed_instalment": 100_000},
        headers=headers,
    )

    assert stored.status_code == 409
    assert stored.json()["error"]["code"] == "REASSESSMENT_REQUIRED"
    assert simulated.status_code == 409
    assert simulated.json()["error"]["code"] == "REASSESSMENT_REQUIRED"


def test_historical_pending_assessment_never_runs_current_analysis_config(
    authed_client: TestClient, db_session: Session
) -> None:
    _, assessment_id = _create_complete_assessment(
        authed_client, "analysis-old-pending-user@example.com"
    )
    assessment = _mark_assessment_historical(db_session, assessment_id)
    original_safe_amount = assessment.safe_loan_amount
    assessment.status = AssessmentStatusEnum.PENDING
    db_session.flush()

    with pytest.raises(ReassessmentRequiredError) as exc_info:
        run_assessment_analysis(db_session, uuid.UUID(assessment_id))

    assert exc_info.value.code == "REASSESSMENT_REQUIRED"
    assert assessment.status is AssessmentStatusEnum.PENDING
    assert assessment.safe_loan_amount == original_safe_amount


def test_cash_flow_repository_orders_equal_day_debits_before_credits(
    authed_client: TestClient, db_session: Session
) -> None:
    _, assessment_id = _create_complete_assessment(
        authed_client, "cash-event-order-user@example.com"
    )
    events = list(
        db_session.execute(
            select(CashFlowEvent).where(CashFlowEvent.assessment_id == assessment_id).limit(2)
        ).scalars()
    )
    assert len(events) == 2
    events[0].expected_day_of_month = 15
    events[0].direction = DirEnum.CREDIT
    events[1].expected_day_of_month = 15
    events[1].direction = DirEnum.DEBIT
    db_session.flush()

    ordered = FinancialProfileRepository(db_session).get_cash_flow_events_for_assessment(
        uuid.UUID(assessment_id)
    )

    same_day = [event for event in ordered if event.expected_day_of_month == 15]
    assert [event.direction for event in same_day[:2]] == [DirEnum.DEBIT, DirEnum.CREDIT]


def test_offer_safety_detail_matches_list_entry(authed_client: TestClient) -> None:
    headers, assessment_id = _create_complete_assessment(
        authed_client, "offer-safety-user@example.com"
    )
    create_response = authed_client.post(
        f"/api/v1/assessments/{assessment_id}/offers", headers=headers
    )
    first_offer = create_response.json()["offers"][0]

    response = authed_client.get(
        f"/api/v1/offers/{first_offer['offer_id']}/safety", headers=headers
    )

    assert response.status_code == 200
    assert response.json()["safe_offer_score"] == first_offer["safe_offer_score"]
    assert response.json()["explanation"]


def test_offer_safety_for_another_users_offer_is_404(authed_client: TestClient) -> None:
    owner_headers, assessment_id = _create_complete_assessment(
        authed_client, "offer-owner@example.com"
    )
    create_response = authed_client.post(
        f"/api/v1/assessments/{assessment_id}/offers", headers=owner_headers
    )
    offer_id = create_response.json()["offers"][0]["offer_id"]

    intruder_headers = _register_and_login(authed_client, "offer-intruder@example.com")
    response = authed_client.get(f"/api/v1/offers/{offer_id}/safety", headers=intruder_headers)

    assert response.status_code == 404


def test_create_offers_before_assessment_complete_is_422(authed_client: TestClient) -> None:
    headers = _register_and_login(authed_client, "offers-not-ready-user@example.com")
    financing_need_id = _create_financing_need(authed_client, headers)
    data = build_pdf(bca_style_statement_lines())
    upload = authed_client.post(
        "/api/v1/documents",
        files={"file": ("statement.pdf", data, "application/pdf")},
        data={"source_type": "ORIGINAL_PDF"},
        headers=headers,
    )
    document_id = str(upload.json()["document_id"])  # still REVIEW_PENDING, not confirmed

    # Force an assessment straight through would 422 at creation already
    # (document not ANALYZING); this test targets the offers-specific guard
    # by attempting to seed offers for a nonexistent/incomplete assessment id.
    response = authed_client.post(
        "/api/v1/assessments",
        json={"financing_need_id": financing_need_id, "source_document_ids": [document_id]},
        headers=headers,
    )
    assert response.status_code == 422

    fake_assessment_id = "00000000-0000-0000-0000-000000000000"
    offers_response = authed_client.post(
        f"/api/v1/assessments/{fake_assessment_id}/offers", headers=headers
    )
    assert offers_response.status_code == 404
