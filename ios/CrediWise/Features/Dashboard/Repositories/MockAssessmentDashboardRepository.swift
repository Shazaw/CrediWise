actor MockAssessmentDashboardRepository: AssessmentDashboardRepository {
    private let report: AssessmentDashboard
    private let error: AssessmentDashboardRepositoryError?
    private var requestedAssessmentIDs: [String] = []
    private var creationRequests: [(String, String)] = []

    init(
        report: AssessmentDashboard = MockAssessmentDashboardRepository.makeDashboard(),
        error: AssessmentDashboardRepositoryError? = nil
    ) {
        self.report = report
        self.error = error
    }

    func create(financingNeedID: String, documentID: String) async throws -> String {
        if let error {
            throw error
        }
        creationRequests.append((financingNeedID, documentID))
        return report.assessmentID
    }

    func dashboard(assessmentID: String) async throws -> AssessmentDashboard {
        requestedAssessmentIDs.append(assessmentID)
        if let error {
            throw error
        }
        return report
    }

    func requests() -> [String] {
        requestedAssessmentIDs
    }

    func creations() -> [(String, String)] {
        creationRequests
    }

    static func makeDashboard() -> AssessmentDashboard {
        AssessmentDashboard(
            assessmentID: "synthetic-assessment-id",
            dataConfidence: MockDocumentVerificationRepository.makeConfidenceReport(),
            risk: makeRisk(),
            safeBorrowing: makeSafeBorrowing(),
            twin: makeTwin(),
            recommendations: makeRecommendations(),
            modelVersion: "risk-safe-v1"
        )
    }

    private static func makeRisk() -> AssessmentDashboard.Risk {
        .init(
            band: .bandB,
            modelConfidence: .high,
            positiveFactors: [
                .init(
                    id: "income-consistency",
                    titleKey: "dashboard.reason.income_consistency.title",
                    detailKey: "dashboard.reason.income_consistency.detail"
                ),
                .init(
                    id: "debt-burden",
                    titleKey: "dashboard.reason.low_debt.title",
                    detailKey: "dashboard.reason.low_debt.detail"
                )
            ],
            riskFactors: [
                .init(
                    id: "income-variation",
                    titleKey: "dashboard.reason.income_variation.title",
                    detailKey: "dashboard.reason.income_variation.detail"
                )
            ]
        )
    }

    private static func makeSafeBorrowing() -> AssessmentDashboard.SafeBorrowing {
        .init(
            illustrativeAmount: 3_500_000,
            maximumSafeInstalment: 375_000,
            recommendedTenorMonths: 12,
            dueDateStart: 20,
            dueDateEnd: 25,
            frequency: .monthly,
            requiredLiquidityBuffer: 1_250_000,
            reasons: [
                .init(
                    id: "buffer-preserved",
                    titleKey: "dashboard.reason.buffer.title",
                    detailKey: "dashboard.reason.buffer.detail"
                )
            ]
        )
    }

    private static func makeTwin() -> AssessmentDashboard.Twin {
        .init(
            medianIncome: 3_700_000,
            essentialExpenses: 2_050_000,
            discretionaryExpenses: 300_000,
            existingDebt: 200_000,
            averageFreeCashFlow: 1_150_000,
            weakestMonthCashFlow: 475_000,
            personalIncome: 1_250_000,
            businessIncome: 2_450_000,
            coverage: .sufficient
        )
    }

    private static func makeRecommendations() -> [AssessmentDashboard.Recommendation] {
        [
            .init(
                id: "protect-buffer",
                titleKey: "dashboard.plan.protect_buffer.title",
                detailKey: "dashboard.plan.protect_buffer.detail",
                targetMetricKey: "dashboard.plan.protect_buffer.metric"
            ),
            .init(
                id: "stabilize-income",
                titleKey: "dashboard.plan.stabilize_income.title",
                detailKey: "dashboard.plan.stabilize_income.detail",
                targetMetricKey: "dashboard.plan.stabilize_income.metric"
            )
        ]
    }
}
