"""`run_verification` idempotency (PLAN §8.2, NFR-3, FR-5; T3.3/T3.4)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session
from tests.support.pdf_builder import bca_style_statement_lines, build_pdf

from app.integrations.storage import get_storage_port, raw_document_key
from app.models.document_verification_result import DocumentVerificationResult
from app.models.enums import AccountTypeEnum, ConnectionTypeEnum, DocStatusEnum, SourceTypeEnum
from app.models.financial_account import FinancialAccount
from app.models.source_document import SourceDocument
from app.models.user import User
from app.services.extraction_service import run_extraction
from app.services.verification_service import run_verification


def _make_verifying_document(db_session: Session) -> SourceDocument:
    user = User(email=f"verification-{uuid.uuid4()}@example.com", password_hash="x")
    db_session.add(user)
    db_session.flush()
    account = FinancialAccount(
        id=uuid.uuid4(),
        user_id=user.id,
        account_type=AccountTypeEnum.BANK,
        connection_type=ConnectionTypeEnum.UPLOAD,
    )
    db_session.add(account)
    db_session.flush()

    document = SourceDocument(
        id=uuid.uuid4(),
        user_id=user.id,
        financial_account_id=account.id,
        file_name="statement.pdf",
        file_hash="2" * 64,
        mime_type="application/pdf",
        source_type=SourceTypeEnum.ORIGINAL_PDF,
        status=DocStatusEnum.EXTRACTING,
        uploaded_at=datetime.now(UTC),
    )
    db_session.add(document)
    db_session.flush()
    storage_path = raw_document_key(str(user.id), str(document.id))
    get_storage_port().put_object(
        storage_path, build_pdf(bca_style_statement_lines()), content_type="application/pdf"
    )
    document.storage_path = storage_path
    db_session.flush()

    run_extraction(db_session, document.id)
    db_session.refresh(document)
    assert document.status == DocStatusEnum.VERIFYING
    return document


def test_verification_persists_result_and_advances_to_review_pending(
    db_session: Session,
) -> None:
    document = _make_verifying_document(db_session)

    run_verification(db_session, document.id)

    db_session.refresh(document)
    assert document.status == DocStatusEnum.REVIEW_PENDING

    result = (
        db_session.query(DocumentVerificationResult)
        .filter(DocumentVerificationResult.source_document_id == document.id)
        .one()
    )
    assert result.data_confidence_score is not None
    assert "reason_codes" in result.flags_json
    assert len(result.flags_json["reason_codes"]) >= 3


def test_is_a_no_op_when_not_in_verifying_state(db_session: Session) -> None:
    document = _make_verifying_document(db_session)
    run_verification(db_session, document.id)
    db_session.refresh(document)
    assert document.status == DocStatusEnum.REVIEW_PENDING

    # A retry (e.g. a redelivered Celery message) must not raise or re-run.
    run_verification(db_session, document.id)

    db_session.refresh(document)
    assert document.status == DocStatusEnum.REVIEW_PENDING


def test_is_a_no_op_for_unknown_document_id(db_session: Session) -> None:
    run_verification(db_session, uuid.uuid4())
