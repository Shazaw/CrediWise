"""Persistence for the Cash-Flow Digital Twin's per-assessment detail tables
(PLAN §10.1 — no business rules): `financial_profiles`,
`monthly_cash_flow_snapshots`, `income_sources`, `cash_flow_events` -- all
child entities scoped to one assessment (PLAN §10.1 "one repository per
aggregate"; `recurring_series` is user/account-scoped, not assessment-scoped,
so it has its own repository)."""

import uuid

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.models.cash_flow_event import CashFlowEvent
from app.models.financial_profile import FinancialProfile
from app.models.income_source import IncomeSource
from app.models.monthly_cash_flow_snapshot import MonthlyCashFlowSnapshot


class FinancialProfileRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add_profile(self, profile: FinancialProfile) -> FinancialProfile:
        self._db.add(profile)
        self._db.flush()
        return profile

    def get_profile_for_assessment(self, assessment_id: uuid.UUID) -> FinancialProfile | None:
        stmt = select(FinancialProfile).where(
            FinancialProfile.assessment_id == assessment_id, FinancialProfile.deleted_at.is_(None)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def add_monthly_snapshots(
        self, snapshots: list[MonthlyCashFlowSnapshot]
    ) -> list[MonthlyCashFlowSnapshot]:
        self._db.add_all(snapshots)
        self._db.flush()
        return snapshots

    def get_monthly_snapshots_for_assessment(
        self, assessment_id: uuid.UUID
    ) -> list[MonthlyCashFlowSnapshot]:
        stmt = (
            select(MonthlyCashFlowSnapshot)
            .where(
                MonthlyCashFlowSnapshot.assessment_id == assessment_id,
                MonthlyCashFlowSnapshot.deleted_at.is_(None),
            )
            .order_by(MonthlyCashFlowSnapshot.year_month)
        )
        return list(self._db.execute(stmt).scalars().all())

    def add_income_sources(self, sources: list[IncomeSource]) -> list[IncomeSource]:
        self._db.add_all(sources)
        self._db.flush()
        return sources

    def get_income_sources_for_assessment(self, assessment_id: uuid.UUID) -> list[IncomeSource]:
        stmt = select(IncomeSource).where(
            IncomeSource.assessment_id == assessment_id, IncomeSource.deleted_at.is_(None)
        )
        return list(self._db.execute(stmt).scalars().all())

    def add_cash_flow_events(self, events: list[CashFlowEvent]) -> list[CashFlowEvent]:
        self._db.add_all(events)
        self._db.flush()
        return events

    def get_cash_flow_events_for_assessment(self, assessment_id: uuid.UUID) -> list[CashFlowEvent]:
        stmt = (
            select(CashFlowEvent)
            .where(
                CashFlowEvent.assessment_id == assessment_id,
                CashFlowEvent.deleted_at.is_(None),
            )
            .order_by(
                CashFlowEvent.expected_day_of_month.asc().nulls_last(),
                CashFlowEvent.event_date.asc().nulls_last(),
                case((CashFlowEvent.direction == "DEBIT", 0), else_=1),
                CashFlowEvent.event_type,
                CashFlowEvent.id,
            )
        )
        return list(self._db.execute(stmt).scalars().all())
