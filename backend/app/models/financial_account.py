"""A user's bank/e-wallet/QRIS/marketplace account (PLAN §11.3 `financial_accounts`).

No dedicated route creates these in Sprint 2 (§26.3 T2.1 is model+migration
only) — `source_documents.financial_account_id` is nullable, and later
sprints (extraction/aggregation) attribute uploads to an account, whether
auto-detected from statement metadata or explicitly chosen by the user.
"""

import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import (
    AccountTypeEnum,
    ConnectionStatusEnum,
    ConnectionTypeEnum,
    OwnershipEnum,
)
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class FinancialAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "financial_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    account_type: Mapped[AccountTypeEnum] = mapped_column(
        sa_enum(AccountTypeEnum, "account_type_enum"), nullable=False
    )
    provider_name: Mapped[str | None] = mapped_column(Text(), nullable=True)
    masked_account_number: Mapped[str | None] = mapped_column(Text(), nullable=True)
    ownership_status: Mapped[OwnershipEnum] = mapped_column(
        sa_enum(OwnershipEnum, "ownership_enum"), nullable=False, default=OwnershipEnum.DECLARED
    )
    connection_type: Mapped[ConnectionTypeEnum] = mapped_column(
        sa_enum(ConnectionTypeEnum, "conn_type_enum"), nullable=False
    )
    connection_status: Mapped[ConnectionStatusEnum] = mapped_column(
        sa_enum(ConnectionStatusEnum, "conn_status_enum"),
        nullable=False,
        default=ConnectionStatusEnum.ACTIVE,
    )
