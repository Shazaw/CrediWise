"""Shared enum types for ORM models.

`RoleEnum` values are fixed by PLAN Appendix A. `IdentityStatusEnum`,
`EmploymentTypeEnum`, `DocumentTypeEnum`, `VerificationStatusEnum`,
`ActorTypeEnum`, and `ModelStatusEnum` are referenced by PLAN §11.3's table
definitions but their member sets are not enumerated in Appendix A — the
values below are the Sprint 1 implementation choice (PLAN §24.11: additive,
non-architectural gap-filling, documented in PLAN.md in the same PR).

`AccountTypeEnum`, `ConnectionTypeEnum`, and `SourceTypeEnum` member sets are
fixed by PLAN Appendix A. `OwnershipEnum` and `ConnectionStatusEnum` are
referenced by PLAN §11.3's `financial_accounts` definition but their member
sets are not enumerated in Appendix A; `DocStatusEnum`'s Appendix A list is
missing two states (`VALIDATION_FAILED`, `DUPLICATE_REUSED`) that PLAN §8.2's
state diagram requires. All of these are the Sprint 2 implementation choice
(PLAN §24.11 gap-filling, documented in PLAN.md in the same PR — see §11.3).
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


class AccountTypeEnum(StrEnum):
    BANK = "BANK"
    EWALLET = "EWALLET"
    QRIS = "QRIS"
    MARKETPLACE = "MARKETPLACE"


class OwnershipEnum(StrEnum):
    """Gap-fill (PLAN §24.11): PLAN §11.3 only names the default, `DECLARED`.
    `VERIFIED` is reserved for a future ownership-verification step (e.g.
    micro-deposit/OTP) — not implemented in MVP.
    """

    DECLARED = "DECLARED"
    VERIFIED = "VERIFIED"


class ConnectionTypeEnum(StrEnum):
    UPLOAD = "UPLOAD"
    API = "API"


class ConnectionStatusEnum(StrEnum):
    """Gap-fill (PLAN §24.11): not enumerated in Appendix A. `UPLOAD`-type
    accounts (the only kind created in MVP) are always `ACTIVE`; `INACTIVE`
    and `ERROR` are reserved for the post-MVP `API` connection type (§16.2).
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"


class SourceTypeEnum(StrEnum):
    BANK_API = "BANK_API"
    SIGNED_STATEMENT = "SIGNED_STATEMENT"
    ORIGINAL_PDF = "ORIGINAL_PDF"
    EXPORTED_CSV = "EXPORTED_CSV"
    SCREENSHOT = "SCREENSHOT"
    PHOTO = "PHOTO"


class DocStatusEnum(StrEnum):
    """PLAN §8.2's state diagram plus Appendix A, with two gap-filled states
    (PLAN §24.11) that the diagram requires but Appendix A's list omits:
    `VALIDATION_FAILED` (oversize/corrupt/zero-byte) and `DUPLICATE_REUSED`
    (same user+hash re-upload).
    """

    UPLOADED = "UPLOADED"
    SECURITY_CHECK = "SECURITY_CHECK"
    REJECTED_SECURITY = "REJECTED_SECURITY"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    DUPLICATE_REUSED = "DUPLICATE_REUSED"
    EXTRACTING = "EXTRACTING"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    VERIFYING = "VERIFYING"
    NORMALIZING = "NORMALIZING"
    ANALYZING = "ANALYZING"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    COMPLETE = "COMPLETE"
