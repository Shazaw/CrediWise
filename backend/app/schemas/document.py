"""Document upload/status/verification/transaction DTOs (PLAN §12.2
`/documents`; FR-3, FR-4, FR-5, FR-14)."""

import uuid
from datetime import date, datetime
from datetime import time as dtime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel

from app.models.enums import (
    BandEnum,
    CategoryEnum,
    DirEnum,
    DocStatusEnum,
    SourceTypeEnum,
    TransactionContextEnum,
)


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    status: DocStatusEnum
    poll: str
    duplicate: bool


class DocumentStatusResponse(BaseModel):
    document_id: uuid.UUID
    status: DocStatusEnum
    file_name: str
    mime_type: str
    source_type: SourceTypeEnum
    page_count: int | None
    uploaded_at: datetime | None


class ReasonCodeResponse(BaseModel):
    code: str
    description: str


class DocumentVerificationResponse(BaseModel):
    document_id: uuid.UUID
    data_confidence_score: Decimal
    band: BandEnum
    provenance_score: Decimal
    consistency_score: Decimal
    metadata_score: Decimal
    ocr_score: Decimal
    visual_score: Decimal
    completeness_score: Decimal
    ownership_score: Decimal
    reason_codes: list[ReasonCodeResponse]
    recommendation: str | None
    verified_at: datetime


class TransactionResponse(BaseModel):
    transaction_id: uuid.UUID
    transaction_date: date
    transaction_time: dtime | None
    amount: int
    direction: DirEnum
    balance_after: int | None
    raw_description: str
    category: CategoryEnum
    transaction_context: TransactionContextEnum
    is_internal_transfer: bool
    is_recurring: bool
    extraction_confidence: Decimal


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    next_cursor: uuid.UUID | None


class CorrectionTypeEnum(StrEnum):
    """FR-14 EC's named dispute classes. Not a DB-native enum — the
    `corrections.correction_type` column is `TEXT` per PLAN §11.3 — but
    bounded here at the API boundary so the client can't submit an
    arbitrary free-form category."""

    INCORRECT_AMOUNT = "INCORRECT_AMOUNT"
    WRONG_CATEGORY = "WRONG_CATEGORY"
    INTERNAL_TRANSFER = "INTERNAL_TRANSFER"
    DUPLICATE = "DUPLICATE"
    MISSING_ROW = "MISSING_ROW"
    OWNERSHIP_CONCERN = "OWNERSHIP_CONCERN"
    OTHER = "OTHER"


class CorrectionRequest(BaseModel):
    transaction_id: uuid.UUID | None
    correction_type: CorrectionTypeEnum
    note: str | None = None


class ReviewRequest(BaseModel):
    corrections: list[CorrectionRequest]


class ReviewResponse(BaseModel):
    document_id: uuid.UUID
    corrections_recorded: int


class ConfirmResponse(BaseModel):
    document_id: uuid.UUID
    status: DocStatusEnum
