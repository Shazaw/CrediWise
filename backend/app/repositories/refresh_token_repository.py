"""Persistence for `refresh_tokens` (PLAN §18.1 — server-side hashed, revocable)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, token: RefreshToken) -> RefreshToken:
        self._db.add(token)
        self._db.flush()
        return token

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash, RefreshToken.deleted_at.is_(None)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def revoke(self, token: RefreshToken, *, replaced_by: RefreshToken | None = None) -> None:
        token.revoked_at = datetime.now(UTC)
        if replaced_by is not None:
            token.replaced_by_token_id = replaced_by.id
        self._db.flush()

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.deleted_at.is_(None),
        )
        for token in self._db.execute(stmt).scalars():
            token.revoked_at = datetime.now(UTC)
        self._db.flush()
