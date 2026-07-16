"""Shared enum types for ORM models.

`RoleEnum` values are fixed by PLAN Appendix A. `IdentityStatusEnum`,
`EmploymentTypeEnum`, `DocumentTypeEnum`, `VerificationStatusEnum`,
`ActorTypeEnum`, and `ModelStatusEnum` are referenced by PLAN §11.3's table
definitions but their member sets are not enumerated in Appendix A — the
values below are the Sprint 1 implementation choice (PLAN §24.11: additive,
non-architectural gap-filling, documented in PLAN.md in the same PR).
"""

from enum import StrEnum


class RoleEnum(StrEnum):
    USER = "USER"
    LENDER = "LENDER"
    REVIEWER = "REVIEWER"
    ADMIN = "ADMIN"


class IdentityStatusEnum(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class EmploymentTypeEnum(StrEnum):
    EMPLOYED = "EMPLOYED"
    SELF_EMPLOYED = "SELF_EMPLOYED"
    GIG_WORKER = "GIG_WORKER"
    BUSINESS_OWNER = "BUSINESS_OWNER"
    UNEMPLOYED = "UNEMPLOYED"
    OTHER = "OTHER"


class DocumentTypeEnum(StrEnum):
    KTP = "KTP"
    PASSPORT = "PASSPORT"
    OTHER = "OTHER"


class VerificationStatusEnum(StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class ActorTypeEnum(StrEnum):
    USER = "USER"
    LENDER = "LENDER"
    SYSTEM = "SYSTEM"
    ADMIN = "ADMIN"


class ModelStatusEnum(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
