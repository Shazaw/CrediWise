"""Persistence for `users` and `user_profiles` (PLAN §10.1 — no business rules here)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserProfile


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        return self._db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
        return self._db.execute(stmt).scalar_one_or_none()

    def add(self, user: User) -> User:
        self._db.add(user)
        self._db.flush()
        return user

    def get_profile(self, user_id: uuid.UUID) -> UserProfile | None:
        stmt = select(UserProfile).where(
            UserProfile.user_id == user_id, UserProfile.deleted_at.is_(None)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def add_profile(self, profile: UserProfile) -> UserProfile:
        self._db.add(profile)
        self._db.flush()
        return profile
