"""`/api/v1/assessments` routes (PLAN §12.2; FR-8, FR-9, FR-12, FR-18).
Thin: parse/validate, call one service method, map to response DTO — no
business logic (PLAN §10.1). Sprint 4, T4.6.

Ownership follows `documents.py`'s pattern: a mismatched `user_id` raises
`NotFoundError` (404), never `PermissionError` (403) — PLAN §18.4 BOLA/IDOR.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import require
from app.core.errors import NotFoundError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.assessment import Assessment
from app.models.assessment_input_snapshot import AssessmentInputSnapshot
from app.models.assessment_reason_code import AssessmentReasonCode
from app.models.enums import ReasonTypeEnum, RoleEnum
from app.models.user import User
from app.schemas.assessment import (
    AssessmentCreateResponse,
    AssessmentResponse,
    CashFlowEventResponse,
    CreateAssessmentRequest,
    DashboardResponse,
    DataConfidenceSummary,
    IncomeSourceResponse,
    LineageResponse,
    MonthlySnapshotResponse,
    RecommendationResponse,
    RiskBandSummary,
    SafeBorrowingSummary,
    TwinResponse,
    TwinSummary,
)
from app.schemas.document import ReasonCodeResponse
from app.services.assessment_service import AssessmentService, TwinView, band_from_score

router = APIRouter(prefix="/assessments", tags=["assessments"])


def _to_assessment_response(assessment: Assessment) -> AssessmentResponse:
    return AssessmentResponse(
        assessment_id=assessment.id,
        status=assessment.status,
        data_confidence_score=assessment.data_confidence_score,
        data_confidence_band=(
            band_from_score(assessment.data_confidence_score)
            if assessment.data_confidence_score is not None
            else None
        ),
        indicative_risk_band=assessment.indicative_risk_band,
        model_confidence=assessment.model_confidence,
        shock_resilience_score=assessment.shock_resilience_score,
        safe_loan_amount=assessment.safe_loan_amount,
        maximum_safe_instalment=assessment.maximum_safe_instalment,
        recommended_tenor_months=assessment.recommended_tenor_months,
        recommended_due_date_start=assessment.recommended_due_date_start,
        recommended_due_date_end=assessment.recommended_due_date_end,
        recommended_frequency=assessment.recommended_frequency,
    )


def _to_twin_response(assessment_id: uuid.UUID, twin: TwinView) -> TwinResponse:
    return TwinResponse(
        assessment_id=assessment_id,
        average_income=twin.profile.average_income,
        median_income=twin.profile.median_income,
        income_volatility=twin.profile.income_volatility,
        essential_expenses=twin.profile.essential_expenses,
        discretionary_expenses=twin.profile.discretionary_expenses,
        existing_debt=twin.profile.existing_debt,
        average_free_cash_flow=twin.profile.average_free_cash_flow,
        minimum_balance=twin.profile.minimum_balance,
        positive_cash_flow_ratio=twin.profile.positive_cash_flow_ratio,
        weakest_month_cash_flow=twin.profile.weakest_month_cash_flow,
        savings_buffer=twin.profile.savings_buffer,
        months_covered=twin.profile.months_covered,
        coverage_flag=twin.profile.coverage_flag,
        monthly_snapshots=[
            MonthlySnapshotResponse(
                year_month=m.year_month,
                personal_income=m.personal_income,
                business_income=m.business_income,
                essential_expenses=m.essential_expenses,
                discretionary_expenses=m.discretionary_expenses,
                business_expenses=m.business_expenses,
                debt_service=m.debt_service,
                opening_balance=m.opening_balance,
                minimum_balance=m.minimum_balance,
                closing_balance=m.closing_balance,
                net_cash_flow=m.net_cash_flow,
            )
            for m in twin.monthly_snapshots
        ],
        income_sources=[
            IncomeSourceResponse(
                source_name=s.source_name,
                source_type=s.source_type,
                average_amount=s.average_amount,
                frequency=s.frequency,
                volatility=s.volatility,
                concentration_ratio=s.concentration_ratio,
                dominant_arrival_day=s.dominant_arrival_day,
                confidence=s.confidence,
            )
            for s in twin.income_sources
        ],
        cash_flow_events=[
            CashFlowEventResponse(
                expected_day_of_month=e.expected_day_of_month,
                amount=e.amount,
                direction=e.direction,
                event_type=e.event_type,
                confidence=e.confidence,
            )
            for e in twin.cash_flow_events
        ],
    )


def _to_reason_code_responses(codes: list[AssessmentReasonCode]) -> list[ReasonCodeResponse]:
    return [ReasonCodeResponse(code=c.reason_code, description=c.description) for c in codes]


def _to_lineage_response(
    assessment_id: uuid.UUID, snapshot: AssessmentInputSnapshot
) -> LineageResponse:
    return LineageResponse(
        assessment_id=assessment_id,
        snapshot_hash=snapshot.snapshot_hash,
        document_ids=[uuid.UUID(d) for d in snapshot.document_refs_json.get("document_ids", [])],
        transaction_ids=[
            uuid.UUID(t) for t in snapshot.transaction_refs_json.get("transaction_ids", [])
        ],
        parser_versions=snapshot.parser_versions_json,
        categorizer_version=snapshot.categorizer_version,
        engine_config_hash=snapshot.engine_config_hash,
    )


@router.post(
    "",
    response_model=AssessmentCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit("general"))],
)
def create_assessment(
    body: CreateAssessmentRequest,
    current_user: User = Depends(require(RoleEnum.USER)),
    db: Session = Depends(get_db),
) -> AssessmentCreateResponse:
    assessment = AssessmentService(db).create(
        user=current_user,
        financing_need_id=body.financing_need_id,
        source_document_ids=body.source_document_ids,
    )
    return AssessmentCreateResponse(
        assessment_id=assessment.id,
        status=assessment.status,
        poll=f"/api/v1/assessments/{assessment.id}",
    )


@router.get(
    "/{assessment_id}",
    response_model=AssessmentResponse,
    dependencies=[Depends(rate_limit("general"))],
)
def get_assessment(
    assessment_id: uuid.UUID,
    current_user: User = Depends(require(RoleEnum.USER)),
    db: Session = Depends(get_db),
) -> AssessmentResponse:
    assessment = AssessmentService(db).get(current_user, assessment_id)
    return _to_assessment_response(assessment)


@router.get(
    "/{assessment_id}/twin",
    response_model=TwinResponse,
    dependencies=[Depends(rate_limit("general"))],
)
def get_assessment_twin(
    assessment_id: uuid.UUID,
    current_user: User = Depends(require(RoleEnum.USER)),
    db: Session = Depends(get_db),
) -> TwinResponse:
    twin = AssessmentService(db).get_twin(current_user, assessment_id)
    return _to_twin_response(assessment_id, twin)


@router.get(
    "/{assessment_id}/recommendation",
    response_model=RecommendationResponse,
    dependencies=[Depends(rate_limit("general"))],
)
def get_assessment_recommendation(
    assessment_id: uuid.UUID,
    current_user: User = Depends(require(RoleEnum.USER)),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    service = AssessmentService(db)
    assessment = service.get(current_user, assessment_id)
    reason_codes = service.get_reason_codes(current_user, assessment_id)
    return RecommendationResponse(
        assessment_id=assessment.id,
        safe_loan_amount=assessment.safe_loan_amount,
        maximum_safe_instalment=assessment.maximum_safe_instalment,
        recommended_tenor_months=assessment.recommended_tenor_months,
        recommended_due_date_start=assessment.recommended_due_date_start,
        recommended_due_date_end=assessment.recommended_due_date_end,
        recommended_frequency=assessment.recommended_frequency,
        reason_codes=_to_reason_code_responses(
            [c for c in reason_codes if c.reason_code.startswith("SAFE_BORROWING_")]
        ),
    )


@router.get(
    "/{assessment_id}/dashboard",
    response_model=DashboardResponse,
    dependencies=[Depends(rate_limit("general"))],
)
def get_assessment_dashboard(
    assessment_id: uuid.UUID,
    current_user: User = Depends(require(RoleEnum.USER)),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    """FR-12: composite read for the 4-headline-card dashboard (§7.11).
    `twin` is `None` until the async analysis stage completes (PLAN §8.3)."""
    service = AssessmentService(db)
    assessment = service.get(current_user, assessment_id)
    reason_codes = service.get_reason_codes(current_user, assessment_id)

    positive = [c.description for c in reason_codes if c.reason_type is ReasonTypeEnum.POSITIVE]
    risk_reasons = [c.description for c in reason_codes if c.reason_type is ReasonTypeEnum.RISK]
    data_quality_reasons = [
        c.description for c in reason_codes if c.reason_type is ReasonTypeEnum.DATA_QUALITY
    ]

    try:
        twin = service.get_twin(current_user, assessment_id)
        twin_summary = TwinSummary(
            median_income=twin.profile.median_income,
            essential_expenses=twin.profile.essential_expenses,
            existing_debt=twin.profile.existing_debt,
            average_free_cash_flow=twin.profile.average_free_cash_flow,
            weakest_month_cash_flow=twin.profile.weakest_month_cash_flow,
        )
    except NotFoundError:
        twin_summary = None  # not ready yet -- assessment still PENDING/ANALYZING

    due_date_window = (
        (assessment.recommended_due_date_start, assessment.recommended_due_date_end)
        if assessment.recommended_due_date_start is not None
        and assessment.recommended_due_date_end is not None
        else None
    )

    return DashboardResponse(
        assessment_id=assessment.id,
        status=assessment.status,
        data_confidence=DataConfidenceSummary(
            score=assessment.data_confidence_score,
            band=(
                band_from_score(assessment.data_confidence_score)
                if assessment.data_confidence_score is not None
                else None
            ),
            reasons=data_quality_reasons,
        ),
        risk_band=RiskBandSummary(
            band=assessment.indicative_risk_band,
            model_confidence=assessment.model_confidence,
            positive=positive,
            risk=risk_reasons,
        ),
        safe_borrowing=SafeBorrowingSummary(
            amount=assessment.safe_loan_amount,
            max_instalment=assessment.maximum_safe_instalment,
            tenor_months=assessment.recommended_tenor_months,
            due_date_window=due_date_window,
            frequency=assessment.recommended_frequency,
        ),
        twin=twin_summary,
    )


@router.get(
    "/{assessment_id}/lineage",
    response_model=LineageResponse,
    dependencies=[Depends(rate_limit("general"))],
)
def get_assessment_lineage(
    assessment_id: uuid.UUID,
    current_user: User = Depends(require(RoleEnum.USER)),
    db: Session = Depends(get_db),
) -> LineageResponse:
    snapshot = AssessmentService(db).get_lineage(current_user, assessment_id)
    return _to_lineage_response(assessment_id, snapshot)
