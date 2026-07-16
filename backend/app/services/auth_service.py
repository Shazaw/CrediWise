"""Auth use cases: register, login, refresh, logout (PLAN §10.1 services layer; FR-1).

Owns the DB transaction boundary for each use case and emits the matching
`audit_logs` entry in the same transaction (FR-15 AC1).
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core import security
from app.core.config import get_settings
from app.core.errors import AuthError, ConflictError
from app.models.enums import ActorTypeEnum, RoleEnum
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services import audit_service


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in_seconds: int


class AuthService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._users = UserRepository(db)
        self._refresh_tokens = RefreshTokenRepository(db)

    def register(self, *, email: str, password: str) -> User:
        """FR-1 AC1: creates a `USER` account with a pending identity status."""
        if self._users.get_by_email(email) is not None:
            raise ConflictError("An account with this email already exists")

        user = User(
            email=email,
            password_hash=security.hash_password(password),
            role=RoleEnum.USER,
        )
        self._users.add(user)
        audit_service.record(
            self._db,
            actor_type=ActorTypeEnum.USER,
            actor_id=user.id,
            action="user.registered",
            entity_type="user",
            entity_id=user.id,
        )
        self._db.commit()
        return user

    def login(self, *, email: str, password: str) -> tuple[User, TokenPair]:
        """FR-1 AC2: issues a 15-minute access token + 30-day refresh token."""
        user = self._users.get_by_email(email)
        if user is None or not security.verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password")

        user.last_login_at = datetime.now(UTC)
        tokens = self._issue_token_pair(user)

        audit_service.record(
            self._db,
            actor_type=ActorTypeEnum.USER,
            actor_id=user.id,
            action="user.logged_in",
            entity_type="user",
            entity_id=user.id,
        )
        self._db.commit()
        return user, tokens

    def refresh(self, *, raw_refresh_token: str) -> TokenPair:
        """FR-1 EC: rotates the refresh token; an expired/revoked token → 401."""
        token_hash = security.hash_refresh_token(raw_refresh_token)
        stored = self._refresh_tokens.get_by_hash(token_hash)
        if stored is None or not stored.is_active:
            raise AuthError("Invalid or expired refresh token")

        user = self._users.get_by_id(stored.user_id)
        if user is None:
            raise AuthError("Invalid or expired refresh token")

        tokens = self._issue_token_pair(user)
        new_stored = self._refresh_tokens.get_by_hash(
            security.hash_refresh_token(tokens.refresh_token)
        )
        self._refresh_tokens.revoke(stored, replaced_by=new_stored)

        audit_service.record(
            self._db,
            actor_type=ActorTypeEnum.USER,
            actor_id=user.id,
            action="user.token_refreshed",
            entity_type="user",
            entity_id=user.id,
        )
        self._db.commit()
        return tokens

    def logout(self, *, user_id: uuid.UUID, raw_refresh_token: str) -> None:
        """Idempotent: an unknown or already-revoked token is a silent no-op."""
        token_hash = security.hash_refresh_token(raw_refresh_token)
        stored = self._refresh_tokens.get_by_hash(token_hash)
        if stored is None or stored.user_id != user_id:
            return
        self._refresh_tokens.revoke(stored)
        audit_service.record(
            self._db,
            actor_type=ActorTypeEnum.USER,
            actor_id=user_id,
            action="user.logged_out",
            entity_type="user",
            entity_id=user_id,
        )
        self._db.commit()

    def _issue_token_pair(self, user: User) -> TokenPair:
        access_token = security.create_access_token(user_id=user.id, role=user.role.value)
        raw_refresh = security.generate_refresh_token()
        self._refresh_tokens.add(
            RefreshToken(
                user_id=user.id,
                token_hash=security.hash_refresh_token(raw_refresh),
                expires_at=security.refresh_token_expiry(),
            )
        )
        ttl_seconds = get_settings().security_access_token_ttl_minutes * 60
        return TokenPair(
            access_token=access_token, refresh_token=raw_refresh, expires_in_seconds=ttl_seconds
        )
