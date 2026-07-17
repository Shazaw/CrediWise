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
        if let error {
            throw error
        }
        return report(initialReport, assessmentID: assessmentID, parameters: nil)
    }

    func simulate(
        assessmentID: String,
        parameters: ShockSimulationParameters
    ) async throws -> ShockAssessment {
        recordedSimulationRequests.append(
            SimulationRequest(assessmentID: assessmentID, parameters: parameters)
        )
        if let error {
            throw error
        }
        return report(simulatedReport, assessmentID: assessmentID, parameters: parameters)
    }

    func shockRequests() -> [String] {
        shockAssessmentIDs
    }

    func simulationRequests() -> [SimulationRequest] {
        recordedSimulationRequests
    }

    static func makeInitialReport() -> ShockAssessment {
        makeReport(score: 68, band: .moderate, modelVersion: "shock-v1")
    }

    static func makeSimulatedReport() -> ShockAssessment {
        makeReport(score: 68, band: .moderate, modelVersion: "shock-v1-custom")
    }

    private static func makeReport(
        score: Int,
        band: ShockAssessment.ResilienceBand,
        modelVersion: String
    ) -> ShockAssessment {
        ShockAssessment(
            assessmentID: "synthetic-assessment-id",
            score: score,
            band: band,
            requiredLiquidityBuffer: 1_250_000,
            scenarios: makeScenarios(),
            reasons: [
                .init(
                    id: "temporal-buffer",
                    titleKey: "shocks.reason.temporal_buffer.title",
                    detailKey: "shocks.reason.temporal_buffer.detail"
                ),
                .init(
                    id: "weakest-month",
                    titleKey: "shocks.reason.weakest_month.title",
                    detailKey: "shocks.reason.weakest_month.detail"
                ),
                .init(
                    id: "source-concentration",
                    titleKey: "shocks.reason.source_concentration.title",
                    detailKey: "shocks.reason.source_concentration.detail"
                )
            ],
            modelVersion: modelVersion,
            appliedParameters: nil
        )
    }

    private static func makeScenarios() -> [ShockAssessment.Scenario] {
        incomeDropScenarios() + timingScenarios() + lossScenarios()
    }

    private static func incomeDropScenarios() -> [ShockAssessment.Scenario] {
        [
            .init(
                id: "income-drop-10",
                kind: .incomeDrop,
                titleKey: "shocks.scenario.income_drop_10.title",
                monthlyProjectedBalance: 1_800_000,
                minimumTemporalBalance: 1_400_000,
                requiredBufferBreached: false,
                deficit: 0,
                status: .survivable,
                scoreContribution: 10,
                chartPoints: makeChart(prefix: "survivable", balances: [2_100_000, 1_700_000, 1_800_000])
            ),
            .init(
                id: "income-drop-20",
                kind: .incomeDrop,
                titleKey: "shocks.scenario.income_drop_20.title",
                monthlyProjectedBalance: 1_400_000,
                minimumTemporalBalance: 1_250_000,
                requiredBufferBreached: false,
                deficit: 0,
                status: .survivable,
                scoreContribution: 20,
                chartPoints: makeChart(prefix: "income-20", balances: [2_100_000, 1_250_000, 1_400_000])
            ),
            .init(
                id: "income-drop-30",
                kind: .incomeDrop,
                titleKey: "shocks.scenario.income_drop_30.title",
                monthlyProjectedBalance: 600_000,
                minimumTemporalBalance: 200_000,
                requiredBufferBreached: true,
                deficit: 0,
                status: .strained,
                scoreContribution: 5,
                chartPoints: makeChart(prefix: "income-30", balances: [2_100_000, 200_000, 600_000])
            )
        ]
    }

    private static func timingScenarios() -> [ShockAssessment.Scenario] {
        [
            .init(
                id: "delayed-income",
                kind: .delayedIncome,
                titleKey: "shocks.scenario.delayed_income.title",
                monthlyProjectedBalance: 1_650_000,
                minimumTemporalBalance: 1_300_000,
                requiredBufferBreached: false,
                deficit: 0,
                status: .survivable,
                scoreContribution: 15,
                chartPoints: makeChart(prefix: "delayed", balances: [1_600_000, 1_300_000, 1_650_000])
            ),
            .init(
                id: "emergency-expense",
                kind: .emergencyExpense,
                titleKey: "shocks.scenario.emergency_expense.title",
                monthlyProjectedBalance: 900_000,
                minimumTemporalBalance: 250_000,
                requiredBufferBreached: true,
                deficit: 0,
                status: .strained,
                scoreContribution: 7.5,
                chartPoints: makeChart(prefix: "strained", balances: [1_900_000, 250_000, 900_000])
            )
        ]
    }

    private static func lossScenarios() -> [ShockAssessment.Scenario] {
        [
            .init(
                id: "income-source-loss",
                kind: .incomeSourceLoss,
                titleKey: "shocks.scenario.income_source_loss.title",
                monthlyProjectedBalance: -450_000,
                minimumTemporalBalance: -700_000,
                requiredBufferBreached: true,
                deficit: 700_000,
                status: .deficit,
                scoreContribution: 0,
                chartPoints: makeChart(prefix: "deficit", balances: [1_100_000, -200_000, -700_000])
            ),
            .init(
                id: "weakest-month",
                kind: .weakestMonth,
                titleKey: "shocks.scenario.weakest_month.title",
                monthlyProjectedBalance: 850_000,
                minimumTemporalBalance: 350_000,
                requiredBufferBreached: true,
                deficit: 0,
                status: .strained,
                scoreContribution: 10,
                chartPoints: makeChart(prefix: "weakest", balances: [1_450_000, 350_000, 850_000])
            )
        ]
    }

    private static func makeChart(prefix: String, balances: [Int64]) -> [ShockAssessment.ProjectionPoint] {
        balances.enumerated().map { index, balance in
            .init(
                id: "\(prefix)-\(index)",
                periodKey: "shocks.period.\(index + 1)",
                balance: balance
            )
        }
    }

    private func report(
        _ source: ShockAssessment,
        assessmentID: String,
        parameters: ShockSimulationParameters?
    ) -> ShockAssessment {
        ShockAssessment(
            assessmentID: assessmentID,
            score: source.score,
            band: source.band,
            requiredLiquidityBuffer: source.requiredLiquidityBuffer,
            scenarios: source.scenarios,
            reasons: source.reasons,
            modelVersion: source.modelVersion,
            appliedParameters: parameters
        )
    }
}
