"""Persistence for `offer_assessments` (PLAN §10.1 — no business rules)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.offer_assessment import OfferAssessment


class OfferAssessmentRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, offer_assessment: OfferAssessment) -> OfferAssessment:
        self._db.add(offer_assessment)
        self._db.flush()
        return offer_assessment

    def get_by_offer_id(self, lender_offer_id: uuid.UUID) -> OfferAssessment | None:
        stmt = select(OfferAssessment).where(
            OfferAssessment.lender_offer_id == lender_offer_id,
            OfferAssessment.deleted_at.is_(None),
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def list_for_offer_ids(self, offer_ids: list[uuid.UUID]) -> list[OfferAssessment]:
        if not offer_ids:
            return []
        stmt = select(OfferAssessment).where(
            OfferAssessment.lender_offer_id.in_(offer_ids), OfferAssessment.deleted_at.is_(None)
        )
        return list(self._db.execute(stmt).scalars().all())
