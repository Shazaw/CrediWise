import XCTest
@testable import CrediWise

@MainActor
final class AssessmentDashboardViewModelTests: XCTestCase {
    func testLoadPreservesBackendSuppliedRiskAndSafeBorrowingValues() async {
        let supplied = MockAssessmentDashboardRepository.makeDashboard()
        let repository = MockAssessmentDashboardRepository(report: supplied)
        let viewModel = AssessmentDashboardViewModel(
            assessmentID: "assessment-123",
            repository: repository
        )

        await viewModel.load()
        let requests = await repository.requests()

        XCTAssertEqual(viewModel.state, .loaded(supplied))
        guard case let .loaded(report) = viewModel.state else {
            return XCTFail("Expected loaded dashboard")
        }
        XCTAssertEqual(report.risk.band, .bandB)
        XCTAssertEqual(report.risk.modelConfidence, .high)
        XCTAssertEqual(report.safeBorrowing.illustrativeAmount, 3_500_000)
        XCTAssertEqual(report.safeBorrowing.maximumSafeInstalment, 375_000)
        XCTAssertEqual(report.twin.weakestMonthCashFlow, 475_000)
        XCTAssertEqual(requests, ["assessment-123"])
    }

    func testLowCoverageAndInsufficientDataRemainDistinctSuppliedStates() async {
        let base = MockAssessmentDashboardRepository.makeDashboard()
        let supplied = AssessmentDashboard(
            assessmentID: base.assessmentID,
            dataConfidence: base.dataConfidence,
            risk: .init(
                band: .insufficientData,
                modelConfidence: .low,
                positiveFactors: [],
                riskFactors: base.risk.riskFactors
            ),
            safeBorrowing: .init(
                illustrativeAmount: 0,
                maximumSafeInstalment: 0,
                recommendedTenorMonths: 12,
                dueDateStart: 20,
                dueDateEnd: 25,
                frequency: .monthly,
                requiredLiquidityBuffer: 1_250_000,
                reasons: base.safeBorrowing.reasons
            ),
            twin: .init(
                medianIncome: base.twin.medianIncome,
                essentialExpenses: base.twin.essentialExpenses,
                discretionaryExpenses: base.twin.discretionaryExpenses,
                existingDebt: base.twin.existingDebt,
                averageFreeCashFlow: base.twin.averageFreeCashFlow,
                weakestMonthCashFlow: base.twin.weakestMonthCashFlow,
                personalIncome: base.twin.personalIncome,
                businessIncome: base.twin.businessIncome,
                coverage: .low
            ),
            recommendations: base.recommendations,
            modelVersion: base.modelVersion
        )
        let viewModel = AssessmentDashboardViewModel(
            assessmentID: supplied.assessmentID,
            repository: MockAssessmentDashboardRepository(report: supplied)
        )

        await viewModel.load()

        guard case let .loaded(report) = viewModel.state else {
            return XCTFail("Expected loaded dashboard")
        }
        XCTAssertEqual(report.risk.band, .insufficientData)
        XCTAssertEqual(report.risk.modelConfidence, .low)
        XCTAssertEqual(report.safeBorrowing.illustrativeAmount, 0)
        XCTAssertEqual(report.twin.coverage, .low)
    }

    func testFailureCanRetryWithoutInventingFallbackValues() async {
        let viewModel = AssessmentDashboardViewModel(
            assessmentID: "assessment-123",
            repository: MockAssessmentDashboardRepository(error: .unavailable)
        )

        await viewModel.load()
        XCTAssertEqual(viewModel.state, .failed(errorKey: "dashboard.error.unavailable"))

        await viewModel.retry()
        XCTAssertEqual(viewModel.state, .failed(errorKey: "dashboard.error.unavailable"))
    }
}
