"""`run_extraction` idempotency and auto-provisioning (PLAN §8.2, NFR-3,
FR-4; T3.1/T3.2; ADR-014).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.support.pdf_builder import bca_style_statement_lines, build_pdf

from app.integrations.storage import get_storage_port, raw_document_key
from app.models.document_processing_run import DocumentProcessingRun
from app.models.enums import AccountTypeEnum, ConnectionTypeEnum, DocStatusEnum, SourceTypeEnum
from app.models.financial_account import FinancialAccount
from app.models.source_document import SourceDocument
from app.models.transaction import Transaction
from app.models.user import User
from app.services.extraction_service import run_extraction


def _make_extracting_document(
    db_session: Session, *, data: bytes, financial_account_id: uuid.UUID | None = None
) -> SourceDocument:
    user = User(email=f"extraction-{uuid.uuid4()}@example.com", password_hash="x")
    db_session.add(user)
    db_session.flush()

    document = SourceDocument(
        id=uuid.uuid4(),
        user_id=user.id,
        financial_account_id=financial_account_id,
        file_name="statement.pdf",
        file_hash="0" * 64,
        mime_type="application/pdf",
        source_type=SourceTypeEnum.ORIGINAL_PDF,
        status=DocStatusEnum.EXTRACTING,
        uploaded_at=datetime.now(UTC),
    )
    db_session.add(document)
    db_session.flush()

    storage_path = raw_document_key(str(user.id), str(document.id))
    get_storage_port().put_object(storage_path, data, content_type="application/pdf")
    document.storage_path = storage_path
    db_session.flush()
    return document


def test_clean_statement_advances_to_verifying_and_auto_provisions_account(
    db_session: Session,
) -> None:
    document = _make_extracting_document(db_session, data=build_pdf(bca_style_statement_lines()))

    run_extraction(db_session, document.id)

    db_session.refresh(document)
    assert document.status == DocStatusEnum.VERIFYING
    assert document.financial_account_id is not None
    assert document.statement_start_date is not None
    assert document.statement_start_date.isoformat() == "2026-06-01"

    account = db_session.get(FinancialAccount, document.financial_account_id)
    assert account is not None
    assert account.account_type is AccountTypeEnum.BANK
    assert account.user_id == document.user_id

    transactions = (
        db_session.execute(select(Transaction).where(Transaction.source_document_id == document.id))
        .scalars()
        .all()
    )
    assert len(transactions) == 4  # excludes the Rp0 opening-balance row
    assert all(t.amount > 0 for t in transactions)


def test_reuses_document_supplied_financial_account(db_session: Session) -> None:
    user = User(email=f"extraction-owned-{uuid.uuid4()}@example.com", password_hash="x")
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
        file_hash="1" * 64,
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
    assert document.financial_account_id == account.id


def test_unrecognized_layout_becomes_unsupported_format(db_session: Session) -> None:
    document = _make_extracting_document(
        db_session, data=build_pdf(["No recognizable statement layout here."])
    )

    run_extraction(db_session, document.id)

    db_session.refresh(document)
    assert document.status == DocStatusEnum.UNSUPPORTED_FORMAT
    assert document.financial_account_id is None

    run = db_session.execute(
        select(DocumentProcessingRun).where(DocumentProcessingRun.source_document_id == document.id)
    ).scalar_one()
    assert run.status.value == "FAILED"


def test_is_a_no_op_when_not_in_extracting_state(db_session: Session) -> None:
    document = _make_extracting_document(db_session, data=build_pdf(bca_style_statement_lines()))
    run_extraction(db_session, document.id)
    db_session.refresh(document)
    assert document.status == DocStatusEnum.VERIFYING

    # A retry (e.g. a redelivered Celery message) must not raise or re-run.
    run_extraction(db_session, document.id)

    db_session.refresh(document)
    assert document.status == DocStatusEnum.VERIFYING


def test_is_a_no_op_for_unknown_document_id(db_session: Session) -> None:
    run_extraction(db_session, uuid.uuid4())
