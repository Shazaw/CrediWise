"""Persistence for `shock_scenarios` (PLAN §10.1 — no business rules)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.shock_scenario import ShockScenario


class ShockScenarioRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add_all(self, scenarios: list[ShockScenario]) -> list[ShockScenario]:
        self._db.add_all(scenarios)
        self._db.flush()
        return scenarios

    def list_for_assessment(self, assessment_id: uuid.UUID) -> list[ShockScenario]:
        stmt = select(ShockScenario).where(
            ShockScenario.assessment_id == assessment_id, ShockScenario.deleted_at.is_(None)
        )
        return list(self._db.execute(stmt).scalars().all())
