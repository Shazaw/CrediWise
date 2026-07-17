"""Financing-need use case (PLAN §10.1; FR-2). `POST /financing-needs`,
`GET /financing-needs`."""

import uuid

from sqlalchemy.orm import Session

from app.models.enums import ActorTypeEnum, PurposeEnum, UrgencyEnum
from app.models.financing_need import FinancingNeed
from app.models.user import User
from app.repositories.financing_need_repository import FinancingNeedRepository
from app.services import audit_service


class FinancingNeedService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._financing_needs = FinancingNeedRepository(db)

    def create(
        self,
        *,
        user: User,
        requested_amount: int,
        purpose: PurposeEnum,
        preferred_tenor_months: int,
        urgency: UrgencyEnum,
        notes: str | None,
    ) -> FinancingNeed:
        need = FinancingNeed(
            id=uuid.uuid4(),
            user_id=user.id,
            requested_amount=requested_amount,
            purpose=purpose,
            preferred_tenor_months=preferred_tenor_months,
            urgency=urgency,
            notes=notes,
        )
        self._financing_needs.add(need)
        audit_service.record(
            self._db,
            actor_type=ActorTypeEnum.USER,
            actor_id=user.id,
            action="financing_need.created",
            entity_type="financing_need",
            entity_id=need.id,
        )
        self._db.commit()
        return need

    def list_for_user(self, user: User) -> list[FinancingNeed]:
        return self._financing_needs.list_for_user(user.id)
