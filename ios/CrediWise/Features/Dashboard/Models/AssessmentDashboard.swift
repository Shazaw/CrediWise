struct AssessmentDashboard: Equatable, Sendable {
    enum RiskBand: String, Equatable, Sendable {
        case bandA = "a"
        case bandB = "b"
        case bandC = "c"
        case bandD = "d"
        case insufficientData
    }

    enum ModelConfidence: String, Equatable, Sendable {
        case high
        case medium
        case low
    }

    enum RepaymentFrequency: String, Equatable, Sendable {
        case monthly
        case biweekly
        case weekly
    }

    enum Coverage: String, Equatable, Sendable {
        case sufficient
        case low
    }

    struct Reason: Equatable, Identifiable, Sendable {
        let id: String
        let titleKey: String
        let detailKey: String
    }

    struct Risk: Equatable, Sendable {
        let band: RiskBand
        let modelConfidence: ModelConfidence
        let positiveFactors: [Reason]
        let riskFactors: [Reason]
    }

    struct SafeBorrowing: Equatable, Sendable {
        let illustrativeAmount: Int64
        let maximumSafeInstalment: Int64
        let recommendedTenorMonths: Int
        let dueDateStart: Int
        let dueDateEnd: Int
        let frequency: RepaymentFrequency
        let requiredLiquidityBuffer: Int64
        let reasons: [Reason]
    }

    struct Twin: Equatable, Sendable {
        let medianIncome: Int64
        let essentialExpenses: Int64
        let discretionaryExpenses: Int64
        let existingDebt: Int64
        let averageFreeCashFlow: Int64
        let weakestMonthCashFlow: Int64
        let personalIncome: Int64
        let businessIncome: Int64
        let coverage: Coverage
    }

    struct Recommendation: Equatable, Identifiable, Sendable {
        let id: String
        let titleKey: String
        let detailKey: String
        let targetMetricKey: String
    }

    let assessmentID: String
    let dataConfidence: DataConfidenceReport
    let risk: Risk
    let safeBorrowing: SafeBorrowing
    let twin: Twin
    let recommendations: [Recommendation]
    let modelVersion: String
}
