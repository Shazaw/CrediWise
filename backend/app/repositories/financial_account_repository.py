"""Persistence for `financial_accounts` (PLAN §10.1 — no business rules here).

No route creates these in Sprint 2 (§26.3 T2.1 is model+migration only); this
repository exists so `POST /documents` can validate ownership of an
optionally-supplied `financial_account_id` (PLAN §18.4 BOLA/IDOR guard).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.financial_account import FinancialAccount


class FinancialAccountRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, account_id: uuid.UUID) -> FinancialAccount | None:
        stmt = select(FinancialAccount).where(
            FinancialAccount.id == account_id, FinancialAccount.deleted_at.is_(None)
        )
        return self._db.execute(stmt).scalar_one_or_none()
