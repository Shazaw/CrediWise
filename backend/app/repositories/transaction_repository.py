"""Persistence for `transactions` (PLAN §10.1 — no business rules).

Cursor pagination follows PLAN §12.1 (`?limit=&cursor=`): ordered by
`(transaction_date, id)` so the cursor is stable even when many rows share a
date, using `id` as the tiebreaker.
"""

import uuid

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.models.transaction import Transaction


class TransactionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add_all(self, transactions: list[Transaction]) -> list[Transaction]:
        self._db.add_all(transactions)
        self._db.flush()
        return transactions

    def get_by_id(self, transaction_id: uuid.UUID) -> Transaction | None:
        stmt = select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.deleted_at.is_(None),
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def list_for_document(
        self,
        source_document_id: uuid.UUID,
        *,
        limit: int,
        cursor: uuid.UUID | None,
    ) -> list[Transaction]:
        stmt = select(Transaction).where(
            Transaction.source_document_id == source_document_id,
            Transaction.deleted_at.is_(None),
        )
        if cursor is not None:
            cursor_row = self._db.get(Transaction, cursor)
            if cursor_row is not None:
                stmt = stmt.where(
                    tuple_(Transaction.transaction_date, Transaction.id)
                    > (cursor_row.transaction_date, cursor_row.id)
                )
        stmt = stmt.order_by(Transaction.transaction_date, Transaction.id).limit(limit)
        return list(self._db.execute(stmt).scalars().all())

    def get_by_processing_run(self, processing_run_id: uuid.UUID) -> list[Transaction]:
        stmt = select(Transaction).where(
            Transaction.processing_run_id == processing_run_id,
            Transaction.deleted_at.is_(None),
        )
        return list(self._db.execute(stmt).scalars().all())

    def list_for_user(self, user_id: uuid.UUID) -> list[Transaction]:
        """Every active transaction across the user's accounts/documents --
        `NormalizationEngine`'s cross-account internal-transfer detection
        (FR-6 AC5) and `CashFlowTwinEngine` both need the whole picture, not
        one document's rows (see `app/services/normalization_service.py`)."""
        stmt = select(Transaction).where(
            Transaction.user_id == user_id, Transaction.deleted_at.is_(None)
        )
        return list(self._db.execute(stmt).scalars().all())

    def get_by_ids(self, transaction_ids: list[uuid.UUID]) -> list[Transaction]:
        stmt = select(Transaction).where(
            Transaction.id.in_(transaction_ids), Transaction.deleted_at.is_(None)
        )
        return list(self._db.execute(stmt).scalars().all())

    def list_for_documents(self, source_document_ids: list[uuid.UUID]) -> list[Transaction]:
        """`AssessmentService.create` scopes a new assessment's transactions
        to exactly the documents the caller included (FR-18 lineage), not
        every transaction the user has ever had normalized."""
        stmt = select(Transaction).where(
            Transaction.source_document_id.in_(source_document_ids),
            Transaction.deleted_at.is_(None),
        )
        return list(self._db.execute(stmt).scalars().all())
