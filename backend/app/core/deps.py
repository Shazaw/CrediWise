"""Request-scoped dependencies: current user + RBAC guard (PLAN §18.3).

`require(...)` is deny-by-default: every protected route declares the
role(s) it accepts. Ownership is checked by comparing a resource's `user_id`
to the current user — callers pass an `ownership_getter` that loads the
resource and returns its owning user id (resource lookup is route-specific,
so it isn't hardcoded here). Consent checking (lender reads) is scaffolded
via the same guard shape and wired in when lender endpoints ship.
"""

import uuid
from collections.abc import Callable, Sequence
from typing import Annotated

import jwt
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.errors import AuthError
from app.core.errors import PermissionError as CrediWisePermissionError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import RoleEnum
from app.models.user import User
from app.repositories.user_repository import UserRepository


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Missing or malformed Authorization header")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid or expired access token") from exc

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise AuthError("Invalid or expired access token") from exc

    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise AuthError("Invalid or expired access token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def _check_access(
    current_user: User,
    db: Session,
    *,
    allowed: Sequence[RoleEnum],
    ownership_getter: Callable[[Session, User], uuid.UUID] | None,
) -> User:
    """Pure guard logic, split out from the FastAPI dependency wrapper below
    so it can be unit tested without going through DI/HTTP (PLAN §7.1)."""
    if current_user.role not in allowed:
        raise CrediWisePermissionError("Role not permitted for this resource")
    if ownership_getter is not None:
        owner_id = ownership_getter(db, current_user)
        if owner_id != current_user.id:
            raise CrediWisePermissionError("Not the owner of this resource")
    return current_user


def require(
    *roles: RoleEnum,
    ownership_getter: Callable[[Session, User], uuid.UUID] | None = None,
) -> Callable[..., User]:
    allowed: Sequence[RoleEnum] = roles or (RoleEnum.USER,)

    def _guard(current_user: CurrentUser, db: Session = Depends(get_db)) -> User:
        return _check_access(current_user, db, allowed=allowed, ownership_getter=ownership_getter)

    return _guard
