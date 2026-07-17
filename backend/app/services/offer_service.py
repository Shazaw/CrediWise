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

**Documented simplification (§24.11):** re-running this endpoint inserts a
fresh set of `lender_offers`/`offer_assessments` rows rather than
replacing/deduplicating prior ones -- offers are simulated, non-financial
data, and the added complexity of offer-set versioning is not justified for
an MVP demo endpoint the golden path (PLAN §1.6) calls once per assessment.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.engines import loan_math, offer, shock
from app.engines.config import model_config as cfg
from app.engines.offer import OfferInput
from app.engines.shock import ShockInput
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
from app.repositories.offer_assessment_repository import OfferAssessmentRepository
from app.services import audit_service

_DEFAULT_TENOR_MONTHS = 12
_MONEY_Q = Decimal("1")


@dataclass(frozen=True)
class OfferView:
    lender: Lender
    offer: LenderOffer
    score: OfferAssessment


class OfferService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._assessments = AssessmentRepository(db)
        self._financing_needs = FinancingNeedRepository(db)
        self._profiles = FinancialProfileRepository(db)
        self._lenders = LenderRepository(db)
        self._offers = LenderOfferRepository(db)
        self._offer_assessments = OfferAssessmentRepository(db)

    def create_or_simulate_offers(self, user: User, assessment_id: uuid.UUID) -> list[OfferView]:
        assessment = self._get_owned(user, assessment_id)
        if assessment.status != AssessmentStatusEnum.COMPLETE:
            raise ValidationError(
                "Assessment must be COMPLETE before offers can be seeded",
                details={"status": assessment.status.value},
            )
        financing_need = self._financing_needs.get_by_id(assessment.financing_need_id)
        assert financing_need is not None  # noqa: S101 - FK guarantees existence
        profile = self._profiles.get_profile_for_assessment(assessment.id)
        if profile is None:
            raise NotFoundError("Twin not available yet")
        income_sources = self._profiles.get_income_sources_for_assessment(assessment.id)
        dominant_source = max(income_sources, key=lambda s: s.concentration_ratio, default=None)
        largest_income_source_amount = dominant_source.average_amount if dominant_source else None
        required_liquidity_buffer = assessment.required_liquidity_buffer or 0

        lenders = self._lenders.list_active()
        if not lenders:
            raise ValidationError("No active lenders are seeded")
        templates = cfg.CONFIG["offer"]["templates"]  # type: ignore[index]
        assert isinstance(templates, list)  # noqa: S101 - internal invariant, not user input

        built: list[tuple[LenderOffer, offer.OfferScoreResult]] = []
        for index, lender in enumerate(lenders):
            template = templates[index % len(templates)]
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
                explanation=_explanation(score_result),
                rank=rank,
            )
            self._offer_assessments.add(offer_assessment)
            views.append(
                OfferView(
                    lender=lender_by_id[lender_offer.lender_id],
                    offer=lender_offer,
                    score=offer_assessment,
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
        scores = {
            s.lender_offer_id: s
            for s in self._offer_assessments.list_for_offer_ids([o.id for o in offers])
        }
        lender_by_id = {lender.id: lender for lender in self._lenders.list_active()}
        views = [
            OfferView(lender=lender_by_id[o.lender_id], offer=o, score=scores[o.id])
            for o in offers
            if o.id in scores and o.lender_id in lender_by_id
        ]
        return sorted(views, key=lambda v: v.score.rank)

    def get_offer_safety(self, user: User, offer_id: uuid.UUID) -> OfferView:
        lender_offer = self._offers.get_by_id(offer_id)
        if lender_offer is None:
            raise NotFoundError("Offer not found")
        assessment = self._assessments.get_by_id(lender_offer.assessment_id)
        if assessment is None or assessment.user_id != user.id:
            raise NotFoundError("Offer not found")
        score = self._offer_assessments.get_by_offer_id(lender_offer.id)
        if score is None:
            raise NotFoundError("Offer not found")
        lender = self._lenders.get_by_id(lender_offer.lender_id)
        assert lender is not None  # noqa: S101 - FK guarantees existence
        return OfferView(lender=lender, offer=lender_offer, score=score)

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
            amortization_method=amortization_method,
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
            )
        )

        score_result = offer.run(
            OfferInput(
                instalment_amount=loan_result.instalment_amount,
                principal_amount=principal_amount,
                effective_annual_rate=loan_result.effective_annual_rate,
                late_penalty_terms_present=late_penalty_terms is not None,
                due_date=due_date,
                maximum_safe_instalment=assessment.maximum_safe_instalment or 0,
                safe_loan_amount=assessment.safe_loan_amount or 0,
                average_free_cash_flow=profile_average_free_cash_flow,
                required_liquidity_buffer=required_liquidity_buffer,
                shock_resilience_score_for_offer=shock_result.resilience_score,
                regulatory_status=lender.regulatory_status,
                recommended_due_date_start=assessment.recommended_due_date_start,
                recommended_due_date_end=assessment.recommended_due_date_end,
            )
        )

        lender_offer = LenderOffer(
            id=uuid.uuid4(),
            assessment_id=assessment.id,
            lender_id=lender.id,
            offer_source=OfferSourceEnum.SIMULATED,
            principal_amount=principal_amount,
            net_disbursed_amount=loan_result.net_disbursed_amount,
            instalment_amount=loan_result.instalment_amount,
            tenor_months=tenor_months,
            amortization_method=amortization_method,
            nominal_rate=nominal_rate,
            effective_annual_rate=loan_result.effective_annual_rate,
            interest_amount=loan_result.interest_amount,
            upfront_fee=upfront_fee,
            financed_fee=0,
            service_fee=0,
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

    def _get_owned(self, user: User, assessment_id: uuid.UUID) -> Assessment:
        assessment = self._assessments.get_by_id(assessment_id)
        if assessment is None or assessment.user_id != user.id:
            raise NotFoundError("Assessment not found")
        return assessment


def _explanation(score_result: offer.OfferScoreResult) -> str:
    band = offer.offer_safety_band_from_score(score_result.safe_offer_score)
    if not score_result.warning_flags:
        return f"{band.value} offer -- no caution flags raised."
    flags = ", ".join(flag.replace("_", " ").title() for flag in score_result.warning_flags)
    return f"{band.value} offer with {len(score_result.warning_flags)} caution flag(s): {flags}."


def _to_money(value: Decimal) -> int:
    return int(value.quantize(_MONEY_Q, rounding=ROUND_HALF_UP))
