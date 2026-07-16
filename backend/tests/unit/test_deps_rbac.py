"""RBAC guard unit tests (PLAN §18.3) — pure logic, no DB/HTTP/FastAPI DI."""

import uuid
from unittest.mock import MagicMock

import pytest

from app.core.deps import _check_access
from app.core.errors import PermissionError as CrediWisePermissionError
from app.models.enums import RoleEnum
from app.models.user import User


def _make_user(role: RoleEnum) -> User:
    user = User(email="x@example.com", password_hash="hash", role=role)
    user.id = uuid.uuid4()
    return user


def test_allows_user_with_permitted_role() -> None:
    user = _make_user(RoleEnum.USER)
    result = _check_access(user, MagicMock(), allowed=(RoleEnum.USER,), ownership_getter=None)
    assert result is user


def test_denies_user_with_role_not_in_allowlist() -> None:
    user = _make_user(RoleEnum.USER)
    with pytest.raises(CrediWisePermissionError):
        _check_access(user, MagicMock(), allowed=(RoleEnum.ADMIN,), ownership_getter=None)


def test_denies_by_default_when_role_list_excludes_lender() -> None:
    lender = _make_user(RoleEnum.LENDER)
    with pytest.raises(CrediWisePermissionError):
        _check_access(
            lender, MagicMock(), allowed=(RoleEnum.USER, RoleEnum.ADMIN), ownership_getter=None
        )


def test_allows_ownership_match() -> None:
    user = _make_user(RoleEnum.USER)
    result = _check_access(
        user,
        MagicMock(),
        allowed=(RoleEnum.USER,),
        ownership_getter=lambda db, u: user.id,
    )
    assert result is user


def test_denies_ownership_mismatch() -> None:
    user = _make_user(RoleEnum.USER)
    someone_elses_resource = uuid.uuid4()
    with pytest.raises(CrediWisePermissionError):
        _check_access(
            user,
            MagicMock(),
            allowed=(RoleEnum.USER,),
            ownership_getter=lambda db, u: someone_elses_resource,
        )


def test_role_check_runs_before_ownership_check() -> None:
    """A caller with the wrong role should never trigger a resource lookup."""
    user = _make_user(RoleEnum.LENDER)
    ownership_getter = MagicMock(side_effect=AssertionError("should not be called"))
    with pytest.raises(CrediWisePermissionError):
        _check_access(
            user, MagicMock(), allowed=(RoleEnum.USER,), ownership_getter=ownership_getter
        )
    ownership_getter.assert_not_called()
