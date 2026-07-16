"""User profile use cases (PLAN §10.1; FR-2 `/me`, `/me/profile`)."""

from sqlalchemy.orm import Session

from app.models.enums import ActorTypeEnum
from app.models.user import User, UserProfile
from app.repositories.user_repository import UserRepository
from app.schemas.user import UpdateProfileRequest
from app.services import audit_service


class UserService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._users = UserRepository(db)

    def get_profile(self, user: User) -> UserProfile | None:
        return self._users.get_profile(user.id)

    def update_profile(self, user: User, data: UpdateProfileRequest) -> UserProfile:
        profile = self._users.get_profile(user.id)
        if profile is None:
            profile = UserProfile(user_id=user.id, locale="id-ID")
            self._users.add_profile(profile)

        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(profile, field, value)
        self._db.flush()

        audit_service.record(
            self._db,
            actor_type=ActorTypeEnum.USER,
            actor_id=user.id,
            action="user.profile_updated",
            entity_type="user_profile",
            entity_id=profile.id,
            metadata={"fields": sorted(updates.keys())},
        )
        self._db.commit()
        return profile
