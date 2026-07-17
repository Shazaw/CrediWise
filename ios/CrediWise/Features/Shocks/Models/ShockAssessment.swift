struct ShockAssessment: Equatable, Sendable {
    enum ResilienceBand: String, Equatable, Sendable {
        case strong
        case moderate
        case fragile
    }

    enum AffordabilityStatus: String, Equatable, Sendable {
        case survivable
        case strained
        case deficit
    }

    enum ScenarioKind: String, Equatable, Sendable {
        case incomeDrop
        case delayedIncome
        case emergencyExpense
        case incomeSourceLoss
        case weakestMonth
    }

    struct Scenario: Equatable, Identifiable, Sendable {
        let id: String
        let kind: ScenarioKind
        let titleKey: String
        let monthlyProjectedBalance: Int64
        let minimumTemporalBalance: Int64
        let requiredBufferBreached: Bool
        let deficit: Int64
        let status: AffordabilityStatus
        let scoreContribution: Double
        let chartPoints: [ProjectionPoint]
    }

    struct ProjectionPoint: Equatable, Identifiable, Sendable {
        let id: String
        let periodKey: String
        let balance: Int64
    }

    struct Reason: Equatable, Identifiable, Sendable {
        let id: String
        let titleKey: String
        let detailKey: String
    }

    let assessmentID: String
    let score: Int
    let band: ResilienceBand
    let requiredLiquidityBuffer: Int64
    let scenarios: [Scenario]
    let reasons: [Reason]
    let modelVersion: String
    let appliedParameters: ShockSimulationParameters?
}
