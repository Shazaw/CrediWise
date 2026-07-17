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
        XCTAssertEqual(report.resilienceScore, 68)
        XCTAssertEqual(report.band, .moderate)
        XCTAssertEqual(report.requiredLiquidityBuffer, 1_250_000)
        XCTAssertEqual(report.scenarios.count, 7)
        XCTAssertEqual(report.reasons.count, 1)
        XCTAssertEqual(report.scenarios.map(\.kind), [
            .incomeDrop10,
            .incomeDrop20,
            .incomeDrop30,
            .delayedIncome,
            .emergencyExpense,
            .incomeSourceLoss,
            .weakestMonthReplay
        ])
        XCTAssertEqual(report.scenarios[5].minimumProjectedBalance, -700_000)
        XCTAssertEqual(report.scenarios[5].deficitAmount, 700_000)
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
        viewModel.proposedInstalment = 350_000.2

        await viewModel.simulate()
        let requests = await repository.simulationRequests()

        XCTAssertEqual(
            requests,
            [
                .init(
                    assessmentID: "assessment-456",
                    parameters: .init(
                        incomeDropPercentage: 20,
                        emergencyExpense: 1_000_000,
                        proposedInstalment: 350_000
                    )
                )
            ]
        )
        guard case let .loaded(report) = viewModel.state else {
            return XCTFail("Expected simulated shock assessment")
        }
        XCTAssertEqual(report.assessmentID, "assessment-456")
        XCTAssertEqual(
            report.submittedParameters,
            .init(
                incomeDropPercentage: 20,
                emergencyExpense: 1_000_000,
                proposedInstalment: 350_000
            )
        )
        XCTAssertEqual(report.resilienceScore, simulated.resilienceScore)
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

    func testUnavailableScoreAccessibilityNeverAnnouncesZero() {
        let source = MockShockRepository.makeInitialReport()
        let report = ShockAssessment(
            assessmentID: source.assessmentID,
            resilienceScore: nil,
            resilienceScoreScope: source.resilienceScoreScope,
            band: source.band,
            scenarios: source.scenarios,
            proposedInstalment: source.proposedInstalment,
            requiredLiquidityBuffer: source.requiredLiquidityBuffer,
            reasons: source.reasons,
            explanation: source.explanation,
            modelVersion: source.modelVersion,
            configHash: source.configHash,
            submittedParameters: source.submittedParameters
        )

        let label = ShockResilienceCard(report: report, onOpen: {}).accessibilityLabelText

        XCTAssertTrue(
            label.contains(
                NSLocalizedString("dashboard.value.unavailable", comment: "Unavailable value")
            )
        )
        XCTAssertFalse(label.contains("0 out of 100"))
    }

    func testReassessmentRequiredUsesConstructiveMessage() async {
        let viewModel = ShockViewModel(
            assessmentID: "assessment-123",
            repository: MockShockRepository(error: .reassessmentRequired)
        )

        await viewModel.load()

        XCTAssertEqual(
            viewModel.state,
            .failed(errorKey: "shocks.error.reassessment_required")
        )
    }
}
