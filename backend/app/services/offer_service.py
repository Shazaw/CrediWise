"""Offer seeding, scoring, and ranking (PLAN §10.1, §7.10; FR-11).
`POST/GET /assessments/{id}/offers`, `GET /offers/{id}/safety`.

`OfferService.create_or_simulate_offers` seeds deterministic simulated
offers from `model_config.OFFER_TEMPLATES` against the seeded `lenders`
catalog (PLAN §16.4: no live lender integration in MVP), computes each
offer's full loan-mathematics contract (`app/engines/loan_math.py`, PLAN
§5.7), reruns `ShockEngine` once per offer substituting that offer's own
instalment (the same composition pattern `assessment_service.py` uses for
Twin -> Risk -> SafeBorrowing -- PLAN §10.1: engines never call each other
directly), and scores each with `OfferEngine` (PLAN §5.9).

The canonical simulated set is idempotent: once persisted, repeated POSTs
return those same rows and never create a second batch.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError, ReassessmentRequiredError, ValidationError
from app.engines import loan_math, offer, shock
from app.engines.config import model_config as cfg
from app.engines.offer import OfferInput
from app.engines.shock import CashFlowEventInput, ShockInput
from app.integrations.explainer import (
    ExplainerPort,
    ExplanationInput,
    ReasonInput,
    explain_with_fallback,
)
from app.models.assessment import Assessment
from app.models.enums import (
    ActorTypeEnum,
    AmortizationEnum,
    AssessmentStatusEnum,
    FreqEnum,
    OfferSourceEnum,
)
from app.models.lender import Lender
from app.models.lender_offer import LenderOffer
from app.models.offer_assessment import OfferAssessment
from app.models.user import User
from app.repositories.assessment_repository import AssessmentRepository
from app.repositories.financial_profile_repository import FinancialProfileRepository
from app.repositories.financing_need_repository import FinancingNeedRepository
from app.repositories.lender_offer_repository import LenderOfferRepository
from app.repositories.lender_repository import LenderRepository
from app.repositories.model_version_repository import ModelVersionRepository
from app.repositories.offer_assessment_repository import OfferAssessmentRepository
from app.services import audit_service

_DEFAULT_TENOR_MONTHS = 12
_MONEY_Q = Decimal("1")


@dataclass(frozen=True)
class OfferView:
    lender: Lender
    offer: LenderOffer
    score: OfferAssessment
    model_version: str
    config_hash: str


class OfferService:
    def __init__(
        self,
        db: Session,
        *,
        explainer: ExplainerPort | None = None,
        ai_explanations: bool | None = None,
    ) -> None:
        self._db = db
        self._assessments = AssessmentRepository(db)
        self._financing_needs = FinancingNeedRepository(db)
        self._profiles = FinancialProfileRepository(db)
        self._lenders = LenderRepository(db)
        self._offers = LenderOfferRepository(db)
        self._offer_assessments = OfferAssessmentRepository(db)
        self._model_versions = ModelVersionRepository(db)
        self._explainer = explainer
        self._ai_explanations = (
            get_settings().ai_explanations if ai_explanations is None else ai_explanations
        )

    def create_or_simulate_offers(self, user: User, assessment_id: uuid.UUID) -> list[OfferView]:
        assessment = self._assessments.get_by_id_for_update(assessment_id)
        if assessment is None or assessment.user_id != user.id:
            raise NotFoundError("Assessment not found")
        if assessment.status != AssessmentStatusEnum.COMPLETE:
            raise ValidationError(
                "Assessment must be COMPLETE before offers can be seeded",
                details={"status": assessment.status.value},
            )
        self._require_current_lineage(assessment)
        existing = self.list_offers(user, assessment.id)
        if existing:
            return existing
        financing_need = self._financing_needs.get_by_id(assessment.financing_need_id)
        assert financing_need is not None  # noqa: S101 - FK guarantees existence
        profile = self._profiles.get_profile_for_assessment(assessment.id)
        if profile is None:
            raise NotFoundError("Twin not available yet")
        income_sources = self._profiles.get_income_sources_for_assessment(assessment.id)
        cash_flow_events = self._profiles.get_cash_flow_events_for_assessment(assessment.id)
        dominant_source = max(income_sources, key=lambda s: s.concentration_ratio, default=None)
        largest_income_source_amount = dominant_source.average_amount if dominant_source else None
        required_liquidity_buffer = assessment.required_liquidity_buffer or 0

        lenders = self._lenders.list_active()
        if not lenders:
            raise ValidationError("No active lenders are seeded")
        templates = cfg.CONFIG["offer"]["templates"]  # type: ignore[index]
        assert isinstance(templates, list)  # noqa: S101 - internal invariant, not user input

        built: list[tuple[LenderOffer, offer.OfferScoreResult]] = []
        lender_by_name = {lender.name: lender for lender in lenders}
        for template in templates:
            lender_name = template["lender_name"]
            assert isinstance(lender_name, str)  # noqa: S101 - internal config invariant
            lender = lender_by_name.get(lender_name)
            if lender is None:
                raise ValidationError(
                    "Canonical simulated lender is not active",
                    details={"lender_name": lender_name},
                )
            lender_offer, score_result = self._build_offer(
                assessment=assessment,
                financing_need_requested_amount=financing_need.requested_amount,
                lender=lender,
                template=template,
                profile_median_income=profile.median_income,
                profile_essential_expenses=profile.essential_expenses,
                profile_average_free_cash_flow=profile.average_free_cash_flow,
                profile_weakest_month_cash_flow=profile.weakest_month_cash_flow,
                profile_savings_buffer=profile.savings_buffer,
                required_liquidity_buffer=required_liquidity_buffer,
                largest_income_source_amount=largest_income_source_amount,
                cash_flow_events=tuple(
                    CashFlowEventInput(
                        day_of_month=e.expected_day_of_month,
                        amount=e.amount,
                        direction=e.direction,
                        event_type=e.event_type,
                    )
                    for e in cash_flow_events
                    if e.expected_day_of_month is not None
                ),
            )
            built.append((lender_offer, score_result))

        # PLAN §5.9: "Ranking is score descending, then lower effective total
        # cost." `None` effective rate (unknown cost) sorts last.
        ranked = sorted(
            built,
            key=lambda pair: (
                -pair[1].safe_offer_score,
                (
                    pair[0].effective_annual_rate
                    if pair[0].effective_annual_rate is not None
                    else Decimal("Infinity")
                ),
            ),
        )

        views: list[OfferView] = []
        lender_by_id = {lender.id: lender for lender in lenders}
        for rank, (lender_offer, score_result) in enumerate(ranked, start=1):
            self._offers.add(lender_offer)
            offer_assessment = OfferAssessment(
                id=uuid.uuid4(),
                lender_offer_id=lender_offer.id,
                safe_offer_score=score_result.safe_offer_score,
                affordability_status=score_result.affordability_status,
                shock_resilience_status=score_result.shock_resilience_status,
                total_cost_status=score_result.total_cost_status,
                timing_status=score_result.timing_status,
                warning_flags_json=score_result.warning_flags,
                explanation=self._explanation(score_result),
                rank=rank,
                remaining_essential_expense_coverage=(
                    score_result.remaining_essential_expense_coverage
                ),
                remaining_essential_expense_coverage_ratio=(
                    score_result.remaining_essential_expense_coverage_ratio
                ),
                refinancing_dependency=score_result.refinancing_dependency,
                reason_codes_json=[
                    {"code": reason.code, "description": reason.description}
                    for reason in score_result.reason_codes
                ],
            )
            self._offer_assessments.add(offer_assessment)
            views.append(
                OfferView(
                    lender=lender_by_id[lender_offer.lender_id],
                    offer=lender_offer,
                    score=offer_assessment,
                    **self._lineage(assessment),
                )
            )

        audit_service.record(
            self._db,
            actor_type=ActorTypeEnum.USER,
            actor_id=user.id,
            action="assessment.offers_seeded",
            entity_type="assessment",
            entity_id=assessment.id,
            metadata={"offer_count": len(views)},
        )
        self._db.commit()
        return views

    def list_offers(self, user: User, assessment_id: uuid.UUID) -> list[OfferView]:
        assessment = self._get_owned(user, assessment_id)
        offers = self._offers.list_for_assessment(assessment.id)
        expected_keys = self._canonical_template_keys()
        actual_keys = {o.canonical_template_key for o in offers}
        if offers and (len(offers) != len(expected_keys) or actual_keys != expected_keys):
            raise ReassessmentRequiredError(
                "Canonical offer set is incomplete; create a new assessment",
                details={"assessment_id": str(assessment.id)},
            )
        scores = {
            s.lender_offer_id: s
            for s in self._offer_assessments.list_for_offer_ids([o.id for o in offers])
        }
        lender_by_id = {lender.id: lender for lender in self._lenders.list_active()}
        views = [
            OfferView(
                lender=lender_by_id[o.lender_id],
                offer=o,
                score=scores[o.id],
                **self._lineage(assessment),
            )
            for o in offers
            if o.id in scores and o.lender_id in lender_by_id
        ]
        if offers and len(views) != len(offers):
            raise ReassessmentRequiredError(
                "Canonical offer evidence is incomplete; create a new assessment",
                details={"assessment_id": str(assessment.id)},
            )
        return sorted(views, key=lambda v: v.score.rank)

    def get_offer_safety(self, user: User, offer_id: uuid.UUID) -> OfferView:
        lender_offer = self._offers.get_by_id(offer_id)
        if lender_offer is None:
            raise NotFoundError("Offer not found")
        if lender_offer.canonical_template_key is None:
            raise NotFoundError("Offer not found")
        assessment = self._assessments.get_by_id(lender_offer.assessment_id)
        if assessment is None or assessment.user_id != user.id:
            raise NotFoundError("Offer not found")
        score = self._offer_assessments.get_by_offer_id(lender_offer.id)
        if score is None:
            raise NotFoundError("Offer not found")
        lender = self._lenders.get_by_id(lender_offer.lender_id)
        assert lender is not None  # noqa: S101 - FK guarantees existence
        return OfferView(
            lender=lender,
            offer=lender_offer,
            score=score,
            **self._lineage(assessment),
        )

    def _build_offer(
        self,
        *,
        assessment: Assessment,
        financing_need_requested_amount: int,
        lender: Lender,
        template: dict[str, object],
        profile_median_income: int,
        profile_essential_expenses: int,
        profile_average_free_cash_flow: int,
        profile_weakest_month_cash_flow: int,
        profile_savings_buffer: int,
        required_liquidity_buffer: int,
        largest_income_source_amount: int | None,
        cash_flow_events: tuple[CashFlowEventInput, ...],
    ) -> tuple[LenderOffer, offer.OfferScoreResult]:
        principal_ratio = template["principal_ratio"]
        assert isinstance(principal_ratio, Decimal)  # noqa: S101 - internal config invariant
        principal_amount = _to_money(Decimal(financing_need_requested_amount) * principal_ratio)

        tenor_months = (
            template["tenor_months"]
            or assessment.recommended_tenor_months
            or (_DEFAULT_TENOR_MONTHS)
        )
        assert isinstance(tenor_months, int)  # noqa: S101 - internal config invariant

        nominal_rate = template["nominal_rate"]
        assert isinstance(nominal_rate, Decimal)  # noqa: S101 - internal config invariant
        upfront_fee_ratio = template["upfront_fee_ratio"]
        assert isinstance(upfront_fee_ratio, Decimal)  # noqa: S101 - internal config invariant
        upfront_fee = _to_money(Decimal(principal_amount) * upfront_fee_ratio)
        financed_fee = template["financed_fee"]
        assert isinstance(financed_fee, int)  # noqa: S101 - internal config invariant
        service_fee = template["service_fee"]
        assert isinstance(service_fee, int)  # noqa: S101 - internal config invariant
        admin_fee = template["admin_fee"]
        assert isinstance(admin_fee, int)  # noqa: S101 - internal config invariant
        amortization_method_raw = template["amortization_method"]
        assert isinstance(amortization_method_raw, str)  # noqa: S101 - internal config invariant
        amortization_method = AmortizationEnum(amortization_method_raw)

        loan_result = loan_math.compute(
            principal_amount=principal_amount,
            tenor_months=tenor_months,
            nominal_annual_rate=nominal_rate,
            upfront_fee=upfront_fee,
            financed_fee=financed_fee,
            service_fee=service_fee,
            admin_fee=admin_fee,
            amortization_method=amortization_method,
        )
        maximum_safe_instalment = assessment.maximum_safe_instalment or 0
        actual_safe_principal = loan_math.safe_principal_for_terms(
            maximum_safe_instalment=maximum_safe_instalment,
            tenor_months=tenor_months,
            nominal_annual_rate=nominal_rate,
            amortization_method=amortization_method,
            upfront_fee_ratio=upfront_fee_ratio,
            financed_fee=financed_fee,
            service_fee=service_fee,
            admin_fee=admin_fee,
        )
        reference_effective_annual_rate = loan_math.effective_annual_reference_rate(
            principal_amount=principal_amount,
            tenor_months=tenor_months,
            annual_flat_rate=offer.DEFAULT_CONFIG.reference_annual_flat_rate,
        )

        due_date_offset_days = template["due_date_offset_days"]
        assert isinstance(due_date_offset_days, int)  # noqa: S101 - internal config invariant
        base_due_date = assessment.recommended_due_date_start or 20
        due_date = min(28, max(1, base_due_date + due_date_offset_days))
        late_penalty_terms = template["late_penalty_terms"]
        assert late_penalty_terms is None or isinstance(late_penalty_terms, dict)  # noqa: S101

        shock_result = shock.run(
            ShockInput(
                median_income=profile_median_income,
                essential_expenses=profile_essential_expenses,
                average_free_cash_flow=profile_average_free_cash_flow,
                weakest_month_cash_flow=profile_weakest_month_cash_flow,
                savings_buffer=profile_savings_buffer,
                required_liquidity_buffer=required_liquidity_buffer,
                proposed_instalment=loan_result.instalment_amount,
                largest_income_source_amount=largest_income_source_amount,
                cash_flow_events=cash_flow_events,
                proposed_instalment_day=due_date,
            )
        )

        score_result = offer.run(
            OfferInput(
                instalment_amount=loan_result.instalment_amount,
                principal_amount=principal_amount,
                net_disbursed_amount=loan_result.net_disbursed_amount,
                effective_annual_rate=loan_result.effective_annual_rate,
                reference_effective_annual_rate=reference_effective_annual_rate,
                late_penalty_terms_present=late_penalty_terms is not None,
                due_date=due_date,
                maximum_safe_instalment=maximum_safe_instalment,
                actual_safe_principal=actual_safe_principal,
                actual_terms_description=(
                    f"{tenor_months} months, {nominal_rate} annual nominal rate, "
                    f"{amortization_method.value} amortization, upfront fee {upfront_fee}, "
                    f"financed fee {financed_fee}, service fee {service_fee}, "
                    f"admin fee {admin_fee} IDR"
                ),
                average_free_cash_flow=profile_average_free_cash_flow,
                essential_expenses=profile_essential_expenses,
                required_liquidity_buffer=required_liquidity_buffer,
                shock_resilience_score_for_offer=shock_result.resilience_score,
                regulatory_status=lender.regulatory_status,
                offer_source=OfferSourceEnum.SIMULATED,
                recommended_due_date_start=assessment.recommended_due_date_start,
                recommended_due_date_end=assessment.recommended_due_date_end,
            )
        )

        lender_offer = LenderOffer(
            id=uuid.uuid4(),
            assessment_id=assessment.id,
            lender_id=lender.id,
            offer_source=OfferSourceEnum.SIMULATED,
            canonical_template_key=str(template["key"]),
            principal_amount=principal_amount,
            net_disbursed_amount=loan_result.net_disbursed_amount,
            instalment_amount=loan_result.instalment_amount,
            tenor_months=tenor_months,
            amortization_method=amortization_method,
            nominal_rate=nominal_rate,
            effective_annual_rate=loan_result.effective_annual_rate,
            interest_amount=loan_result.interest_amount,
            upfront_fee=upfront_fee,
            financed_fee=financed_fee,
            service_fee=service_fee,
            admin_fee=admin_fee,
            total_repayment=loan_result.total_repayment,
            late_penalty_terms_json=late_penalty_terms,
            payment_schedule_json={
                "entries": [
                    {
                        "period": e.period,
                        "payment_amount": e.payment_amount,
                        "principal_component": e.principal_component,
                        "interest_component": e.interest_component,
                        "remaining_balance": e.remaining_balance,
                    }
                    for e in loan_result.schedule
                ]
            },
            due_date=due_date,
            frequency=assessment.recommended_frequency or FreqEnum.MONTHLY,
            received_at=datetime.now(UTC),
        )
        return lender_offer, score_result

    def _lineage(self, assessment: Assessment) -> dict[str, str]:
        model = self._model_versions.get_by_id(assessment.model_version_id)
        assert model is not None  # noqa: S101 - assessment FK guarantees existence
        return {"model_version": model.version, "config_hash": model.config_hash}

    def _require_current_lineage(self, assessment: Assessment) -> None:
        model = self._model_versions.get_by_id(assessment.model_version_id)
        if (
            model is None
            or model.version != cfg.MODEL_VERSION
            or model.config_hash != cfg.config_hash()
        ):
            raise ReassessmentRequiredError(
                "Assessment model does not match the current offer configuration; "
                "create a new assessment",
                details={"assessment_id": str(assessment.id)},
            )

    @staticmethod
    def _canonical_template_keys() -> set[str]:
        templates = cfg.CONFIG["offer"]["templates"]  # type: ignore[index]
        assert isinstance(templates, list)  # noqa: S101 - internal config invariant
        return {str(template["key"]) for template in templates}

    def _explanation(self, score_result: offer.OfferScoreResult) -> str:
        return explain_with_fallback(
            ExplanationInput(
                subject="OFFER",
                reasons=tuple(
                    ReasonInput(code=reason.code, description=reason.description)
                    for reason in score_result.reason_codes
                ),
            ),
            enabled=self._ai_explanations,
            provider=self._explainer,
        )

    def _get_owned(self, user: User, assessment_id: uuid.UUID) -> Assessment:
        assessment = self._assessments.get_by_id(assessment_id)
        if assessment is None or assessment.user_id != user.id:
            raise NotFoundError("Assessment not found")
        return assessment


def _to_money(value: Decimal) -> int:
    return int(value.quantize(_MONEY_Q, rounding=ROUND_HALF_UP))
