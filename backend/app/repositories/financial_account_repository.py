"""Persistence for `financial_accounts` (PLAN §10.1 — no business rules here).

No dedicated create/list route ships in MVP (§26.3 T2.1 is model+migration
only); rows come either from an optionally-supplied `financial_account_id`
on upload (validated here for ownership, PLAN §18.4 BOLA/IDOR guard) or from
the Sprint 3 extraction-service auto-provisioning path (ADR-014).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import AccountTypeEnum
from app.models.financial_account import FinancialAccount


class FinancialAccountRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, account_id: uuid.UUID) -> FinancialAccount | None:
        stmt = select(FinancialAccount).where(
            FinancialAccount.id == account_id, FinancialAccount.deleted_at.is_(None)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def get_first_auto_provisioned(
        self, user_id: uuid.UUID, account_type: AccountTypeEnum
    ) -> FinancialAccount | None:
        """Sprint 3 (ADR-014): reuses an existing auto-provisioned account of
        the same inferred type instead of creating a new one per document."""
        stmt = (
            select(FinancialAccount)
            .where(
                FinancialAccount.user_id == user_id,
                FinancialAccount.account_type == account_type,
                FinancialAccount.provider_name == _AUTO_PROVISIONED_PROVIDER_NAME,
                FinancialAccount.deleted_at.is_(None),
            )
            .order_by(FinancialAccount.created_at)
            .limit(1)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def add(self, account: FinancialAccount) -> FinancialAccount:
        self._db.add(account)
        self._db.flush()
        return account


_AUTO_PROVISIONED_PROVIDER_NAME = "auto-detected"
