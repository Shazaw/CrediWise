import Foundation

actor MockShockRepository: ShockRepository {
    struct SimulationRequest: Equatable, Sendable {
        let assessmentID: String
        let parameters: ShockSimulationParameters
    }

    private let initialReport: ShockAssessment
    private let simulatedReport: ShockAssessment
    private let error: ShockRepositoryError?
    private var shockAssessmentIDs: [String] = []
    private var recordedSimulationRequests: [SimulationRequest] = []

    init(
        initialReport: ShockAssessment = MockShockRepository.makeInitialReport(),
        simulatedReport: ShockAssessment = MockShockRepository.makeSimulatedReport(),
        error: ShockRepositoryError? = nil
    ) {
        self.initialReport = initialReport
        self.simulatedReport = simulatedReport
        self.error = error
    }

    func shocks(assessmentID: String) async throws -> ShockAssessment {
        shockAssessmentIDs.append(assessmentID)
        if let error { throw error }
        return report(initialReport, assessmentID: assessmentID, parameters: nil)
    }

    func simulate(
        assessmentID: String,
        parameters: ShockSimulationParameters
    ) async throws -> ShockAssessment {
        recordedSimulationRequests.append(.init(assessmentID: assessmentID, parameters: parameters))
        if let error { throw error }
        return report(simulatedReport, assessmentID: assessmentID, parameters: parameters)
    }

    func shockRequests() -> [String] { shockAssessmentIDs }
    func simulationRequests() -> [SimulationRequest] { recordedSimulationRequests }

    static func makeInitialReport() -> ShockAssessment {
        makeReport(kind: .incomeDrop20, score: 68)
    }

    static func makeSimulatedReport() -> ShockAssessment {
        makeReport(kind: .custom, score: 64)
    }

    private static func makeReport(
        kind: ShockAssessment.ScenarioKind,
        score: Decimal
    ) -> ShockAssessment {
        let kinds: [ShockAssessment.ScenarioKind] = kind == .custom
            ? [.custom]
            : [
                .incomeDrop10, .incomeDrop20, .incomeDrop30, .delayedIncome,
                .emergencyExpense, .incomeSourceLoss, .weakestMonthReplay
            ]
        return ShockAssessment(
            assessmentID: "synthetic-assessment-id",
            resilienceScore: score,
            resilienceScoreScope: .canonicalBattery,
            band: .moderate,
            scenarios: kinds.enumerated().map { index, scenarioKind in
                scenario(kind: scenarioKind, index: index)
            },
            proposedInstalment: 350_000,
            requiredLiquidityBuffer: 1_250_000,
            reasons: [
                .init(
                    code: "SHOCK_TEMPORAL_LIQUIDITY",
                    description: "Some scenarios create temporary liquidity pressure.",
                    titleKey: "shocks.reason.temporal_liquidity",
                    detailKey: "shocks.reason.temporal_liquidity.detail",
                    isKnown: true
                )
            ],
            explanation: "The supplied scenarios show where cash-flow timing creates pressure.",
            modelVersion: "shock-v1",
            configHash: "synthetic-shock-config-v1",
            submittedParameters: nil
        )
    }

    private static func scenario(
        kind: ShockAssessment.ScenarioKind,
        index: Int
    ) -> ShockAssessment.Scenario {
        let isDeficit = kind == .incomeSourceLoss
        let minimum: Int64 = isDeficit ? -700_000 : 900_000 + Int64(index * 50_000)
        let status: ShockAssessment.AffordabilityStatus = isDeficit ? .deficit : .strained
        return .init(
            id: "\(kind.rawValue)-\(index)",
            kind: kind,
            parameters: ["fixture_index": .number(Decimal(index))],
            projectedCashFlow: isDeficit ? -450_000 : 1_400_000,
            minimumProjectedBalance: minimum,
            deficitAmount: isDeficit ? 700_000 : 0,
            status: status,
            resilienceScoreContribution: isDeficit ? 0 : 10,
            requiredLiquidityBuffer: 1_250_000,
            requiredBufferBreached: true,
            projectionPoints: [
                .init(
                    id: "\(kind.rawValue)-0", sequence: 0, dayOfMonth: 1,
                    eventType: "OPENING_BALANCE",
                    eventLabelKey: "shocks.event.opening_balance",
                    isKnownEventType: true,
                    amount: 0, projectedBalance: 2_100_000
                ),
                .init(
                    id: "\(kind.rawValue)-1", sequence: 1, dayOfMonth: 18,
                    eventType: "ESSENTIAL_EXPENSE",
                    eventLabelKey: "shocks.event.essential_expense",
                    isKnownEventType: true,
                    amount: -1_200_000, projectedBalance: minimum
                ),
                .init(
                    id: "\(kind.rawValue)-2", sequence: 2, dayOfMonth: 30,
                    eventType: "MONTH_END_RECONCILIATION",
                    eventLabelKey: "shocks.event.month_end_reconciliation",
                    isKnownEventType: true,
                    amount: 500_000,
                    projectedBalance: isDeficit ? -450_000 : 1_400_000
                )
            ]
        )
    }

    private func report(
        _ source: ShockAssessment,
        assessmentID: String,
        parameters: ShockSimulationParameters?
    ) -> ShockAssessment {
        .init(
            assessmentID: assessmentID,
            resilienceScore: source.resilienceScore,
            resilienceScoreScope: source.resilienceScoreScope,
            band: source.band,
            scenarios: source.scenarios,
            proposedInstalment: source.proposedInstalment,
            requiredLiquidityBuffer: source.requiredLiquidityBuffer,
            reasons: source.reasons,
            explanation: source.explanation,
            modelVersion: source.modelVersion,
            configHash: source.configHash,
            submittedParameters: parameters
        )
    }
}
