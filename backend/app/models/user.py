"""User, profile, and simulated-KYC identity models (PLAN §11.3; FR-1, FR-2, A6)."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    DocumentTypeEnum,
    EmploymentTypeEnum,
    IdentityStatusEnum,
    RoleEnum,
    VerificationStatusEnum,
)
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Auth principal (PLAN §11.3 `users`). Uniqueness on `email` is a partial
    index (`WHERE deleted_at IS NULL`) created by the migration, not an ORM
    column constraint, so a soft-deleted account never blocks re-registration.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(CITEXT(), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text(), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(
        sa_enum(RoleEnum, "role_enum"), nullable=False, default=RoleEnum.USER
    )
    identity_status: Mapped[IdentityStatusEnum] = mapped_column(
        sa_enum(IdentityStatusEnum, "identity_status_enum"),
        nullable=False,
        default=IdentityStatusEnum.UNVERIFIED,
    )
    phone: Mapped[str | None] = mapped_column(Text(), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)

    profile: Mapped["UserProfile | None"] = relationship(back_populates="user", uselist=False)
    identities: Mapped[list["UserIdentity"]] = relationship(back_populates="user")


class UserProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """1:1 profile (PLAN §11.3 `user_profiles`)."""

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    full_name: Mapped[str | None] = mapped_column(Text(), nullable=True)
    employment_type: Mapped[EmploymentTypeEnum | None] = mapped_column(
        sa_enum(EmploymentTypeEnum, "employment_enum"), nullable=True
    )
    business_type: Mapped[str | None] = mapped_column(Text(), nullable=True)
    locale: Mapped[str] = mapped_column(Text(), nullable=False, default="id-ID")

    user: Mapped[User] = relationship(back_populates="profile")


class UserIdentity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Simulated KYC record (PLAN §11.3 `user_identities`, A6 — production KYC
    is simulated in MVP; no `/identity/verify` route ships in this cycle).
    """

    __tablename__ = "user_identities"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    document_type: Mapped[DocumentTypeEnum | None] = mapped_column(
        sa_enum(DocumentTypeEnum, "doc_type_enum"), nullable=True
    )
    document_number_hash: Mapped[str | None] = mapped_column(Text(), nullable=True)
    verified_name: Mapped[str | None] = mapped_column(Text(), nullable=True)
    verification_status: Mapped[VerificationStatusEnum] = mapped_column(
        sa_enum(VerificationStatusEnum, "verify_status_enum"),
        nullable=False,
        default=VerificationStatusEnum.PENDING,
    )
    verification_provider: Mapped[str | None] = mapped_column(Text(), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(nullable=True)

    user: Mapped[User] = relationship(back_populates="identities")
