"""`track_stage` records both outcomes (PLAN §11.3 `pipeline_stage_runs`; NFR-3)."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.models.enums import DocStatusEnum, PipelineStageEnum, SourceTypeEnum, StageStatusEnum
from app.models.pipeline_stage_run import PipelineStageRun
from app.models.source_document import SourceDocument
from app.models.user import User
from app.services.pipeline_stage_tracking import track_stage


def _make_document(db_session: Session) -> SourceDocument:
    user = User(email=f"stage-tracking-{uuid.uuid4()}@example.com", password_hash="x")
    db_session.add(user)
    db_session.flush()
    document = SourceDocument(
        id=uuid.uuid4(),
        user_id=user.id,
        file_name="statement.pdf",
        file_hash=uuid.uuid4().hex.ljust(64, "0"),
        mime_type="application/pdf",
        source_type=SourceTypeEnum.ORIGINAL_PDF,
        status=DocStatusEnum.EXTRACTING,
        uploaded_at=datetime.now(UTC),
    )
    db_session.add(document)
    db_session.flush()
    return document


def test_successful_block_records_succeeded(db_session: Session) -> None:
    document = _make_document(db_session)

    with track_stage(db_session, document.id, PipelineStageEnum.EXTRACTION):
        pass

    run = db_session.query(PipelineStageRun).filter_by(source_document_id=document.id).one()
    assert run.status == StageStatusEnum.SUCCEEDED
    assert run.attempt_number == 1
    assert run.completed_at is not None


def test_raising_block_records_failed_and_reraises(db_session: Session) -> None:
    document = _make_document(db_session)

    with (
        pytest.raises(ValueError, match="boom"),
        track_stage(db_session, document.id, PipelineStageEnum.VERIFICATION),
    ):
        raise ValueError("boom")

    run = db_session.query(PipelineStageRun).filter_by(source_document_id=document.id).one()
    assert run.status == StageStatusEnum.FAILED
    assert run.error_code == "ValueError"
    assert run.sanitized_error_message == "boom"


def test_attempt_number_increments_across_calls(db_session: Session) -> None:
    document = _make_document(db_session)

    with track_stage(db_session, document.id, PipelineStageEnum.EXTRACTION):
        pass
    with track_stage(db_session, document.id, PipelineStageEnum.EXTRACTION):
        pass

    runs = (
        db_session.query(PipelineStageRun)
        .filter_by(source_document_id=document.id)
        .order_by(PipelineStageRun.attempt_number)
        .all()
    )
    assert [r.attempt_number for r in runs] == [1, 2]
