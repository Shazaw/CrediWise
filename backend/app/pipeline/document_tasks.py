"""`documents` queue: the Sprint 2 state-machine orchestrator (PLAN §8.2, T2.5).

`app/services/document_service.py` (see its module docstring and ADR-013)
already runs the *entire* FR-3 file-security stage synchronously in the
`POST /documents` request — the password-transient-decryption requirement
(PLAN §24.10: never pass passwords through Celery/Redis) and the AC3 dedup
gate (must resolve before the HTTP response is built) both force that. By
the time `dispatch_document_processing` enqueues this task, the document is
already known-good and sitting in `UPLOADED`.

This task's job for Sprint 2 is exactly the state diagram's
`SECURITY_CHECK --> EXTRACTING: passed` edge — recording that the document
has now entered the async pipeline. Sprint 3 (T3.1+) extends this same task
with the real OCR/extraction stage.
"""

import uuid

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.enums import ActorTypeEnum, DocStatusEnum
from app.pipeline.celery_app import celery_app
from app.repositories.source_document_repository import SourceDocumentRepository
from app.services import audit_service


def run_security_and_enqueue_extraction(db: Session, document_id: uuid.UUID) -> None:
    """Idempotent/resumable per NFR-3: a document not sitting in `UPLOADED`
    has already been processed (or is terminal), so a retry is a no-op."""
    documents = SourceDocumentRepository(db)
    document = documents.get_by_id(document_id)
    if document is None or document.status != DocStatusEnum.UPLOADED:
        return

    document.status = DocStatusEnum.EXTRACTING
    db.flush()
    audit_service.record(
        db,
        actor_type=ActorTypeEnum.SYSTEM,
        actor_id=None,
        action="document.extracting_started",
        entity_type="source_document",
        entity_id=document.id,
    )
    db.commit()


@celery_app.task(name="app.pipeline.process_document")
def process_document(document_id: str) -> None:
    db = SessionLocal()
    try:
        run_security_and_enqueue_extraction(db, uuid.UUID(document_id))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
