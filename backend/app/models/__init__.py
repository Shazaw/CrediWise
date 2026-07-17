"""Import every model module so `Base.metadata` is fully populated before
Alembic autogenerate or `Base.metadata.create_all()` (integration tests) run.
"""

from app.models.assessment import Assessment
from app.models.assessment_document import AssessmentDocument
from app.models.assessment_input_snapshot import AssessmentInputSnapshot
from app.models.assessment_reason_code import AssessmentReasonCode
from app.models.assessment_transaction import AssessmentTransaction
from app.models.audit_log import AuditLog
from app.models.cash_flow_event import CashFlowEvent
from app.models.correction import Correction
from app.models.document_processing_run import DocumentProcessingRun
from app.models.document_verification_result import DocumentVerificationResult
from app.models.financial_account import FinancialAccount
from app.models.financial_profile import FinancialProfile
from app.models.financing_need import FinancingNeed
from app.models.income_source import IncomeSource
from app.models.lender import Lender
from app.models.lender_offer import LenderOffer
from app.models.model_version import ModelVersion
from app.models.monthly_cash_flow_snapshot import MonthlyCashFlowSnapshot
from app.models.offer_assessment import OfferAssessment
from app.models.pipeline_stage_run import PipelineStageRun
from app.models.recurring_series import RecurringSeries
from app.models.refresh_token import RefreshToken
from app.models.repayment_model_prediction import RepaymentModelPrediction
from app.models.shock_scenario import ShockScenario
from app.models.source_document import SourceDocument
from app.models.transaction import Transaction
from app.models.user import User, UserIdentity, UserProfile

__all__ = [
    "Assessment",
    "AssessmentDocument",
    "AssessmentInputSnapshot",
    "AssessmentReasonCode",
    "AssessmentTransaction",
    "AuditLog",
    "CashFlowEvent",
    "Correction",
    "DocumentProcessingRun",
    "DocumentVerificationResult",
    "FinancialAccount",
    "FinancialProfile",
    "FinancingNeed",
    "IncomeSource",
    "Lender",
    "LenderOffer",
    "ModelVersion",
    "MonthlyCashFlowSnapshot",
    "OfferAssessment",
    "PipelineStageRun",
    "RecurringSeries",
    "RefreshToken",
    "RepaymentModelPrediction",
    "ShockScenario",
    "SourceDocument",
    "Transaction",
    "User",
    "UserIdentity",
    "UserProfile",
]
