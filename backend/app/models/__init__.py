"""Import every model module so `Base.metadata` is fully populated before
Alembic autogenerate or `Base.metadata.create_all()` (integration tests) run.
"""

from app.models.audit_log import AuditLog
from app.models.financial_account import FinancialAccount
from app.models.model_version import ModelVersion
from app.models.refresh_token import RefreshToken
from app.models.source_document import SourceDocument
from app.models.user import User, UserIdentity, UserProfile

__all__ = [
    "AuditLog",
    "FinancialAccount",
    "ModelVersion",
    "RefreshToken",
    "SourceDocument",
    "User",
    "UserIdentity",
    "UserProfile",
]
