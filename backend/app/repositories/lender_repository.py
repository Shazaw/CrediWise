"""Persistence for the seeded `lenders` catalog (PLAN §10.1 — no business
rules)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lender import Lender


class LenderRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, lender: Lender) -> Lender:
        self._db.add(lender)
        self._db.flush()
        return lender

    def get_by_id(self, lender_id: uuid.UUID) -> Lender | None:
        stmt = select(Lender).where(Lender.id == lender_id, Lender.deleted_at.is_(None))
        return self._db.execute(stmt).scalar_one_or_none()

    def list_active(self) -> list[Lender]:
        stmt = (
            select(Lender)
            .where(Lender.is_active.is_(True), Lender.deleted_at.is_(None))
            .order_by(Lender.created_at)
        )
        return list(self._db.execute(stmt).scalars().all())

    def get_by_name(self, name: str) -> Lender | None:
        stmt = select(Lender).where(Lender.name == name, Lender.deleted_at.is_(None))
        return self._db.execute(stmt).scalar_one_or_none()
