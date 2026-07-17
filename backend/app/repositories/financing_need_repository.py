"""Persistence for `financing_needs` (PLAN §10.1 — no business rules)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.financing_need import FinancingNeed


class FinancingNeedRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, need: FinancingNeed) -> FinancingNeed:
        self._db.add(need)
        self._db.flush()
        return need

    def get_by_id(self, financing_need_id: uuid.UUID) -> FinancingNeed | None:
        stmt = select(FinancingNeed).where(
            FinancingNeed.id == financing_need_id, FinancingNeed.deleted_at.is_(None)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def list_for_user(self, user_id: uuid.UUID) -> list[FinancingNeed]:
        stmt = (
            select(FinancingNeed)
            .where(FinancingNeed.user_id == user_id, FinancingNeed.deleted_at.is_(None))
            .order_by(FinancingNeed.created_at.desc())
        )
        return list(self._db.execute(stmt).scalars().all())
