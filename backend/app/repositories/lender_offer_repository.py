"""Persistence for `lender_offers` (PLAN §10.1 — no business rules)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lender_offer import LenderOffer


class LenderOfferRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, offer: LenderOffer) -> LenderOffer:
        self._db.add(offer)
        self._db.flush()
        return offer

    def get_by_id(self, offer_id: uuid.UUID) -> LenderOffer | None:
        stmt = select(LenderOffer).where(
            LenderOffer.id == offer_id, LenderOffer.deleted_at.is_(None)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def list_for_assessment(self, assessment_id: uuid.UUID) -> list[LenderOffer]:
        stmt = select(LenderOffer).where(
            LenderOffer.assessment_id == assessment_id, LenderOffer.deleted_at.is_(None)
        )
        return list(self._db.execute(stmt).scalars().all())
