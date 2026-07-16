"""User profile DTOs (PLAN §12.2 `/me`, `/me/profile`; FR-2)."""

import uuid

from pydantic import BaseModel, ConfigDict

from app.models.enums import EmploymentTypeEnum


class ProfileResponse(BaseModel):
    full_name: str | None
    employment_type: EmploymentTypeEnum | None
    business_type: str | None
    locale: str


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    identity_status: str
    profile: ProfileResponse | None


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = None
    employment_type: EmploymentTypeEnum | None = None
    business_type: str | None = None
    locale: str | None = None
