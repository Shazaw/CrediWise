"""Password hashing + RS256 JWT unit tests (PLAN §18.1)."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core import security
from app.core.config import get_settings


def test_hash_password_round_trips() -> None:
    hashed = security.hash_password("amanpassword1")
    assert hashed != "amanpassword1"
    assert security.verify_password("amanpassword1", hashed)


def test_verify_password_rejects_wrong_password() -> None:
    hashed = security.hash_password("amanpassword1")
    assert not security.verify_password("wrongpassword1", hashed)


def test_hash_password_uses_argon2() -> None:
    assert security.hash_password("amanpassword1").startswith("$argon2")


def test_access_token_round_trips() -> None:
    user_id = uuid.uuid4()
    token = security.create_access_token(user_id=user_id, role="USER")
    payload = security.decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "USER"
    assert payload["type"] == "access"


def test_access_token_is_signed_rs256_with_kid_header() -> None:
    token = security.create_access_token(user_id=uuid.uuid4(), role="USER")
    header = jwt.get_unverified_header(token)
    assert header["alg"] == "RS256"
    assert header["kid"] == get_settings().security_jwt_kid


def test_decode_access_token_rejects_expired_token() -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    expired_payload = {
        "sub": str(uuid.uuid4()),
        "role": "USER",
        "type": "access",
        "iat": now - timedelta(minutes=20),
        "exp": now - timedelta(minutes=5),
    }
    token = jwt.encode(expired_payload, settings.jwt_private_key_pem, algorithm="RS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_access_token(token)


def test_decode_access_token_rejects_wrong_token_type() -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    refresh_shaped_payload = {
        "sub": str(uuid.uuid4()),
        "role": "USER",
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    token = jwt.encode(refresh_shaped_payload, settings.jwt_private_key_pem, algorithm="RS256")
    with pytest.raises(jwt.InvalidTokenError):
        security.decode_access_token(token)


def test_decode_access_token_rejects_tampered_signature() -> None:
    token = security.create_access_token(user_id=uuid.uuid4(), role="USER")
    tampered = token[:-4] + ("A" if token[-4] != "A" else "B") + token[-3:]
    with pytest.raises(jwt.InvalidTokenError):
        security.decode_access_token(tampered)


def test_generate_refresh_token_is_high_entropy_and_unique() -> None:
    tokens = {security.generate_refresh_token() for _ in range(20)}
    assert len(tokens) == 20
    assert all(len(t) >= 40 for t in tokens)


def test_hash_refresh_token_is_deterministic_sha256() -> None:
    raw = security.generate_refresh_token()
    assert security.hash_refresh_token(raw) == security.hash_refresh_token(raw)
    assert len(security.hash_refresh_token(raw)) == 64


def test_refresh_token_expiry_is_in_the_future_by_configured_days() -> None:
    settings = get_settings()
    expiry = security.refresh_token_expiry()
    now = datetime.now(UTC)
    delta = expiry - now
    assert timedelta(days=settings.security_refresh_token_ttl_days) - delta < timedelta(seconds=5)
