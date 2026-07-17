import Foundation

struct ShockAssessment: Equatable, Sendable {
    enum ResilienceScoreScope: String, Equatable, Sendable {
        case canonicalBattery
    }

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
        case incomeDrop10
        case incomeDrop20
        case incomeDrop30
        case delayedIncome
        case emergencyExpense
        case incomeSourceLoss
        case weakestMonthReplay
        case custom
    }

    indirect enum ParameterValue: Equatable, Sendable {
        case string(String)
        case number(Decimal)
        case boolean(Bool)
        case array([ParameterValue])
        case object([String: ParameterValue])
        case null
    }

    struct Scenario: Equatable, Identifiable, Sendable {
        let id: String
        let kind: ScenarioKind
        let parameters: [String: ParameterValue]
        let projectedCashFlow: Int64
        let minimumProjectedBalance: Int64
        let deficitAmount: Int64
        let status: AffordabilityStatus
        let resilienceScoreContribution: Decimal
        let requiredLiquidityBuffer: Int64
        let requiredBufferBreached: Bool
        let projectionPoints: [ProjectionPoint]
    }

    struct ProjectionPoint: Equatable, Identifiable, Sendable {
        let id: String
        let sequence: Int
        let dayOfMonth: Int
        let eventType: String
        let eventLabelKey: String
        let isKnownEventType: Bool
        let amount: Int64
        let projectedBalance: Int64
    }

    struct Reason: Equatable, Identifiable, Sendable {
        var id: String { code }
        let code: String
        let description: String
        let titleKey: String
        let detailKey: String?
        let isKnown: Bool
    }

    let assessmentID: String
    let resilienceScore: Decimal?
    let resilienceScoreScope: ResilienceScoreScope
    let band: ResilienceBand?
    let scenarios: [Scenario]
    let proposedInstalment: Int64
    let requiredLiquidityBuffer: Int64
    let reasons: [Reason]
    let explanation: String
    let modelVersion: String
    let configHash: String
    let submittedParameters: ShockSimulationParameters?
}
