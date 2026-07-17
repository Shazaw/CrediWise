import XCTest
@testable import CrediWise

@MainActor
final class ShockViewModelTests: XCTestCase {
    func testLoadPreservesSuppliedAssessmentValues() async {
        let supplied = MockShockRepository.makeInitialReport()
        let repository = MockShockRepository(initialReport: supplied)
        let viewModel = ShockViewModel(
            assessmentID: "assessment-123",
            repository: repository
        )

        await viewModel.load()
        let requests = await repository.shockRequests()

        XCTAssertEqual(requests, ["assessment-123"])
        guard case let .loaded(report) = viewModel.state else {
            return XCTFail("Expected loaded shock assessment")
        }
        XCTAssertEqual(report.assessmentID, "assessment-123")
        XCTAssertEqual(report.score, 68)
        XCTAssertEqual(report.band, .moderate)
        XCTAssertEqual(report.requiredLiquidityBuffer, 1_250_000)
        XCTAssertEqual(report.scenarios.count, 7)
        XCTAssertEqual(report.reasons.count, 3)
        XCTAssertEqual(report.scenarios.map(\.kind), [
            .incomeDrop,
            .incomeDrop,
            .incomeDrop,
            .delayedIncome,
            .emergencyExpense,
            .incomeSourceLoss,
            .weakestMonth
        ])
        XCTAssertEqual(report.scenarios.reduce(0) { $0 + $1.scoreContribution }, 67.5)
        XCTAssertEqual(report.scenarios[5].minimumTemporalBalance, -700_000)
        XCTAssertEqual(report.scenarios[5].deficit, 700_000)
    }

    func testSimulationForwardsRoundedParametersExactly() async {
        let simulated = MockShockRepository.makeSimulatedReport()
        let repository = MockShockRepository(simulatedReport: simulated)
        let viewModel = ShockViewModel(
            assessmentID: "assessment-456",
            repository: repository
        )
        viewModel.incomeDropPercentage = 19.6
        viewModel.emergencyExpense = 1_000_000.4

        await viewModel.simulate()
        let requests = await repository.simulationRequests()

        XCTAssertEqual(
            requests,
            [
                .init(
                    assessmentID: "assessment-456",
                    parameters: .init(
                        incomeDropPercentage: 20,
                        emergencyExpense: 1_000_000
                    )
                )
            ]
        )
        guard case let .loaded(report) = viewModel.state else {
            return XCTFail("Expected simulated shock assessment")
        }
        XCTAssertEqual(report.assessmentID, "assessment-456")
        XCTAssertEqual(
            report.appliedParameters,
            .init(incomeDropPercentage: 20, emergencyExpense: 1_000_000)
        )
        XCTAssertEqual(report.score, simulated.score)
    }

    func testInvalidSimulationDoesNotCallRepository() async {
        let repository = MockShockRepository()
        let viewModel = ShockViewModel(
            assessmentID: "assessment-123",
            repository: repository
        )
        viewModel.incomeDropPercentage = 101
        viewModel.emergencyExpense = -1

        await viewModel.simulate()
        let requests = await repository.simulationRequests()

        XCTAssertEqual(
            viewModel.state,
            .invalid(errorKey: "shocks.error.invalid_parameters")
        )
        XCTAssertEqual(requests, [])
    }

    func testFailureRetryDoesNotInventShockOutput() async {
        let repository = MockShockRepository(error: .unavailable)
        let viewModel = ShockViewModel(
            assessmentID: "assessment-123",
            repository: repository
        )

        await viewModel.load()
        XCTAssertEqual(viewModel.state, .failed(errorKey: "shocks.error.unavailable"))

        await viewModel.retry()
        let requests = await repository.shockRequests()
        XCTAssertEqual(viewModel.state, .failed(errorKey: "shocks.error.unavailable"))
        XCTAssertEqual(requests, ["assessment-123", "assessment-123"])
    }
}
