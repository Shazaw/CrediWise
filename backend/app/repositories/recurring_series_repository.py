"""Persistence for `recurring_series` (PLAN §10.1 — no business rules).

Scoped to `(user_id, financial_account_id)`, not an assessment (see
`app/models/recurring_series.py`) -- re-running `NormalizationEngine` for a
later document reuses/updates the same row for a counterparty already
detected, rather than accumulating duplicate series rows.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import RecurringTypeEnum
from app.models.recurring_series import RecurringSeries


class RecurringSeriesRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_identity(
        self,
        *,
        user_id: uuid.UUID,
        financial_account_id: uuid.UUID,
        series_type: RecurringTypeEnum,
        normalized_counterparty: str,
    ) -> RecurringSeries | None:
        stmt = select(RecurringSeries).where(
            RecurringSeries.user_id == user_id,
            RecurringSeries.financial_account_id == financial_account_id,
            RecurringSeries.series_type == series_type,
            RecurringSeries.normalized_counterparty == normalized_counterparty,
            RecurringSeries.deleted_at.is_(None),
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def add(self, series: RecurringSeries) -> RecurringSeries:
        self._db.add(series)
        self._db.flush()
        return series

    def list_for_user(self, user_id: uuid.UUID) -> list[RecurringSeries]:
        stmt = select(RecurringSeries).where(
            RecurringSeries.user_id == user_id, RecurringSeries.deleted_at.is_(None)
        )
        return list(self._db.execute(stmt).scalars().all())
