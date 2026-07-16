"""Persistence for `corrections` (PLAN §10.1 — no business rules; FR-14)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.correction import Correction


class CorrectionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add_all(self, corrections: list[Correction]) -> list[Correction]:
        self._db.add_all(corrections)
        self._db.flush()
        return corrections

    def list_for_user(self, user_id: uuid.UUID) -> list[Correction]:
        stmt = select(Correction).where(
            Correction.user_id == user_id, Correction.deleted_at.is_(None)
        )
        return list(self._db.execute(stmt).scalars().all())
