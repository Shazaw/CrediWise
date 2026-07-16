"""Password hashing (argon2id) and RS256 JWT issuance/verification (PLAN §18.1).

Access tokens are short-lived and stateless (§18.1). Refresh tokens are
opaque random strings; only their SHA-256 hash is ever persisted
(``refresh_tokens.token_hash``) so a leaked database row cannot be replayed
as a live session and a compromised token can still be revoked.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

_ACCESS_TOKEN_TYPE = "access"


def hash_password(password: str) -> str:
    return str(_pwd_context.hash(password))


def verify_password(password: str, password_hash: str) -> bool:
    return bool(_pwd_context.verify(password, password_hash))


def create_access_token(*, user_id: uuid.UUID, role: str) -> str:
    """§5.6/§18.1: 15-minute stateless access token, RS256-signed."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": _ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.security_access_token_ttl_minutes),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(
        payload,
        settings.jwt_private_key_pem,
        algorithm="RS256",
        headers={"kid": settings.security_jwt_kid},
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises ``jwt.InvalidTokenError`` (or a subclass) on any failure."""
    settings = get_settings()
    payload: dict[str, Any] = jwt.decode(token, settings.jwt_public_key_pem, algorithms=["RS256"])
    if payload.get("type") != _ACCESS_TOKEN_TYPE:
        raise jwt.InvalidTokenError("not an access token")
    return payload


def generate_refresh_token() -> str:
    """High-entropy opaque string. Only its hash is ever persisted."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def refresh_token_expiry() -> datetime:
    settings = get_settings()
    return datetime.now(UTC) + timedelta(days=settings.security_refresh_token_ttl_days)
