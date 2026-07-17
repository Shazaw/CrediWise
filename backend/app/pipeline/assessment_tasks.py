"""`assessments` queue: the analysis-stage task (PLAN §8.3, Sprint 4/T4.6).

Mirrors `document_tasks.py`'s shape. `AssessmentService.create` (already
known-good: financing need + documents validated, snapshot frozen,
`assessments`/`assessment_documents`/`assessment_transactions` rows
committed) dispatches this via `app/pipeline/dispatch.py
dispatch_assessment_analysis`; this task just runs the already-idempotent
`assessment_service.run_assessment_analysis` inside its own DB session.
"""

import uuid

from app.db.session import SessionLocal
from app.pipeline.celery_app import celery_app
from app.services.assessment_service import run_assessment_analysis


@celery_app.task(name="app.pipeline.run_assessment_analysis")
def run_assessment_analysis_task(assessment_id: str) -> None:
    db = SessionLocal()
    try:
        run_assessment_analysis(db, uuid.UUID(assessment_id))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
