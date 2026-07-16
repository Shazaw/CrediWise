"""`/api/v1/me` routes (PLAN §12.2; FR-2)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.user import User, UserProfile
from app.schemas.user import MeResponse, ProfileResponse, UpdateProfileRequest
from app.services.user_service import UserService

router = APIRouter(tags=["me"], dependencies=[Depends(rate_limit("general"))])


def _to_profile_response(profile: UserProfile) -> ProfileResponse:
    return ProfileResponse(
        full_name=profile.full_name,
        employment_type=profile.employment_type,
        business_type=profile.business_type,
        locale=profile.locale,
    )


def _to_me_response(user: User, profile: UserProfile | None) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=str(user.email),
        role=user.role.value,
        identity_status=user.identity_status.value,
        profile=_to_profile_response(profile) if profile else None,
    )


@router.get("/me", response_model=MeResponse)
def get_me(current_user: CurrentUser, db: Session = Depends(get_db)) -> MeResponse:
    profile = UserService(db).get_profile(current_user)
    return _to_me_response(current_user, profile)


@router.patch("/me/profile", response_model=ProfileResponse)
def update_profile(
    payload: UpdateProfileRequest, current_user: CurrentUser, db: Session = Depends(get_db)
) -> ProfileResponse:
    profile = UserService(db).update_profile(current_user, payload)
    return _to_profile_response(profile)
