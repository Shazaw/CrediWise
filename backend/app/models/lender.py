"""Seeded lender catalog (PLAN §11.3 `lenders`; FR-11, §16.4 — no live
lender integration in MVP, catalog is seed data under `app/db/seeds/`)."""

from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import RegStatusEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class Lender(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lenders"

    name: Mapped[str] = mapped_column(Text(), nullable=False)
    regulatory_status: Mapped[RegStatusEnum] = mapped_column(
        sa_enum(RegStatusEnum, "reg_status_enum"), nullable=False
    )
    logo_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
