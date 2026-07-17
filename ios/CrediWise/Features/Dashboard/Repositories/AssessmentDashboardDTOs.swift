import Foundation

struct AssessmentCreateRequest: Encodable {
    let financingNeedID: UUID
    let sourceDocumentIDs: [UUID]

    enum CodingKeys: String, CodingKey {
        case financingNeedID = "financing_need_id"
        case sourceDocumentIDs = "source_document_ids"
    }
}

struct AssessmentCreateResponse: Decodable {
    let assessmentID: UUID

    enum CodingKeys: String, CodingKey {
        case assessmentID = "assessment_id"
    }
}

struct AssessmentDashboardResponse: Decodable {
    let assessmentID: UUID
    let status: String
    let modelVersionID: UUID
    let dataConfidence: AssessmentDataConfidenceResponse
    let riskBand: AssessmentRiskResponse
    let safeBorrowing: AssessmentSafeBorrowingResponse
    let twin: AssessmentTwinSummaryResponse?
    let repaymentModel: AssessmentRepaymentModelResponse?

    enum CodingKeys: String, CodingKey {
        case assessmentID = "assessment_id"
        case status
        case modelVersionID = "model_version_id"
        case dataConfidence = "data_confidence"
        case riskBand = "risk_band"
        case safeBorrowing = "safe_borrowing"
        case twin
        case repaymentModel = "repayment_model"
    }
}

struct AssessmentDataConfidenceResponse: Decodable {
    let score: String?
    let band: String?
    let reasonCodes: [AssessmentReasonResponse]

    enum CodingKeys: String, CodingKey {
        case score
        case band
        case reasonCodes = "reason_codes"
    }
}

struct AssessmentRiskResponse: Decodable {
    let band: String?
    let modelConfidence: String?
    let positiveReasonCodes: [AssessmentReasonResponse]
    let riskReasonCodes: [AssessmentReasonResponse]

    enum CodingKeys: String, CodingKey {
        case band
        case modelConfidence = "model_confidence"
        case positiveReasonCodes = "positive_reason_codes"
        case riskReasonCodes = "risk_reason_codes"
    }
}

struct AssessmentSafeBorrowingResponse: Decodable {
    let amount: Int64?
    let maxInstalment: Int64?
    let requiredLiquidityBuffer: Int64?
    let tenorMonths: Int?
    let dueDateWindow: [Int]?
    let frequency: String?

    enum CodingKeys: String, CodingKey {
        case amount
        case maxInstalment = "max_instalment"
        case requiredLiquidityBuffer = "required_liquidity_buffer"
        case tenorMonths = "tenor_months"
        case dueDateWindow = "due_date_window"
        case frequency
    }
}

struct AssessmentTwinSummaryResponse: Decodable {}

struct AssessmentReasonResponse: Decodable {
    let code: String
    let description: String
}

struct AssessmentRepaymentModelResponse: Decodable {
    let status: String
    let mode: String
    let estimatedAdverseOutcomeProbability: String?
    let modelConfidence: String?
    let modelName: String
    let modelVersion: String
    let featureSchemaVersion: String
    let reasonCodes: [AssessmentRepaymentModelReasonResponse]
    let outOfDomainFeatures: [String]

    enum CodingKeys: String, CodingKey {
        case status
        case mode
        case estimatedAdverseOutcomeProbability = "estimated_adverse_outcome_probability"
        case modelConfidence = "model_confidence"
        case modelName = "model_name"
        case modelVersion = "model_version"
        case featureSchemaVersion = "feature_schema_version"
        case reasonCodes = "reason_codes"
        case outOfDomainFeatures = "out_of_domain_features"
    }
}

struct AssessmentRepaymentModelReasonResponse: Decodable {
    let code: String
    let feature: String?
    let direction: String?
}

struct AssessmentTwinResponse: Decodable {
    let medianIncome: Int64
    let essentialExpenses: Int64
    let discretionaryExpenses: Int64
    let existingDebt: Int64
    let averageFreeCashFlow: Int64
    let weakestMonthCashFlow: Int64
    let coverageFlag: String
    let incomeSources: [AssessmentIncomeSourceResponse]

    enum CodingKeys: String, CodingKey {
        case medianIncome = "median_income"
        case essentialExpenses = "essential_expenses"
        case discretionaryExpenses = "discretionary_expenses"
        case existingDebt = "existing_debt"
        case averageFreeCashFlow = "average_free_cash_flow"
        case weakestMonthCashFlow = "weakest_month_cash_flow"
        case coverageFlag = "coverage_flag"
        case incomeSources = "income_sources"
    }
}

struct AssessmentIncomeSourceResponse: Decodable {
    let sourceType: String
    let averageAmount: Int64

    enum CodingKeys: String, CodingKey {
        case sourceType = "source_type"
        case averageAmount = "average_amount"
    }
}

struct AssessmentLineageResponse: Decodable {
    let documentIDs: [UUID]

    enum CodingKeys: String, CodingKey {
        case documentIDs = "document_ids"
    }
}
