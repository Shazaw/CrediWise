"""Normalized transaction row (PLAN §11.3 `transactions`; FR-4 AC2, FR-6).

Sprint 3 (T3.1/T3.2) creates these rows straight from extraction with
`category`/`transaction_context` defaulted to `UNKNOWN` and
`is_internal_transfer`/`is_recurring` defaulted `False` — categorization and
transfer/recurring detection are `NormalizationEngine`'s job (FR-6, Sprint 4).
These are normalized-derived fields, not raw evidence, so refining them later
in place does not violate PLAN §6.4's raw-evidence-immutability rule.

`financial_account_id` is `NOT NULL` per PLAN §11.3, even though
`source_documents.financial_account_id` is nullable (no dedicated
create-account route ships in MVP, PLAN §11.3 `financial_accounts`
docstring) — the extraction service auto-provisions a minimal account from
the document's `source_type` when one is missing (see
`app/services/extraction_service.py` and ADR-014).
"""

import uuid
from datetime import date
from datetime import time as dtime
from decimal import Decimal

from sqlalchemy import CHAR, BigInteger, Boolean, Date, ForeignKey, Numeric, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import CategoryEnum, DirEnum, TransactionContextEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class Transaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    financial_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=True
    )
    processing_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_processing_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    transaction_date: Mapped[date] = mapped_column(Date(), nullable=False)
    transaction_time: Mapped[dtime | None] = mapped_column(Time(), nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    direction: Mapped[DirEnum] = mapped_column(sa_enum(DirEnum, "dir_enum"), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, default="IDR")
    balance_after: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    raw_description: Mapped[str] = mapped_column(Text(), nullable=False)
    normalized_merchant: Mapped[str | None] = mapped_column(Text(), nullable=True)
    category: Mapped[CategoryEnum] = mapped_column(
        sa_enum(CategoryEnum, "category_enum"), nullable=False, default=CategoryEnum.UNKNOWN
    )
    subcategory: Mapped[str | None] = mapped_column(Text(), nullable=True)
    transaction_context: Mapped[TransactionContextEnum] = mapped_column(
        sa_enum(TransactionContextEnum, "transaction_context_enum"),
        nullable=False,
        default=TransactionContextEnum.UNKNOWN,
    )
    counterparty: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_internal_transfer: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    category_confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    extraction_confidence: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    row_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
