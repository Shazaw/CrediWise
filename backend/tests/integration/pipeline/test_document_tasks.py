"""`run_security_and_enqueue_extraction` idempotency (PLAN §8.2, NFR-3, T2.5)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.enums import DocStatusEnum, SourceTypeEnum
from app.models.source_document import SourceDocument
from app.models.user import User
from app.pipeline.document_tasks import run_security_and_enqueue_extraction


def _make_uploaded_document(db_session: Session) -> SourceDocument:
    user = User(email="dedup-task@example.com", password_hash="x")
    db_session.add(user)
    db_session.flush()

    document = SourceDocument(
        id=uuid.uuid4(),
        user_id=user.id,
        file_name="statement.pdf",
        file_hash="0" * 64,
        mime_type="application/pdf",
        source_type=SourceTypeEnum.ORIGINAL_PDF,
        status=DocStatusEnum.UPLOADED,
        uploaded_at=datetime.now(UTC),
    )
    db_session.add(document)
    db_session.flush()
    return document


def test_transitions_uploaded_to_extracting(db_session: Session) -> None:
    document = _make_uploaded_document(db_session)

    run_security_and_enqueue_extraction(db_session, document.id)

    db_session.refresh(document)
    assert document.status == DocStatusEnum.EXTRACTING


def test_is_a_no_op_when_not_in_uploaded_state(db_session: Session) -> None:
    document = _make_uploaded_document(db_session)
    run_security_and_enqueue_extraction(db_session, document.id)
    db_session.refresh(document)
    assert document.status == DocStatusEnum.EXTRACTING

    # A retry (e.g. a redelivered Celery message) must not raise or re-transition.
    run_security_and_enqueue_extraction(db_session, document.id)

    db_session.refresh(document)
    assert document.status == DocStatusEnum.EXTRACTING


def test_is_a_no_op_for_unknown_document_id(db_session: Session) -> None:
    run_security_and_enqueue_extraction(db_session, uuid.uuid4())
