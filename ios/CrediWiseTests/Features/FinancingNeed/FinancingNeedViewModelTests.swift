import XCTest
@testable import CrediWise

@MainActor
final class FinancingNeedViewModelTests: XCTestCase {
    func testAmountValidationIncludesApprovedBoundaries() {
        let viewModel = FinancingNeedViewModel(repository: MockFinancingNeedRepository())
        viewModel.setPurpose(.medical)

        viewModel.setAmountText("0")
        XCTAssertFalse(viewModel.isAmountValid)
        XCTAssertFalse(viewModel.canSubmit)

        viewModel.setAmountText("1")
        XCTAssertTrue(viewModel.isAmountValid)
        XCTAssertTrue(viewModel.canSubmit)

        viewModel.setAmountText("1000000000")
        XCTAssertTrue(viewModel.isAmountValid)

        viewModel.setAmountText("1000000001")
        XCTAssertFalse(viewModel.isAmountValid)
    }

    func testAmountInputKeepsWholeRupiahDigitsOnly() {
        let viewModel = FinancingNeedViewModel(repository: MockFinancingNeedRepository())

        viewModel.setAmountText("Rp 3.500.000")

        XCTAssertEqual(viewModel.amountText, "3500000")
        XCTAssertEqual(viewModel.requestedAmount, 3_500_000)
        XCTAssertEqual(viewModel.formattedAmount, "Rp3.500.000")
    }

    func testSubmitPassesExactNeedToRepository() async {
        let repository = MockFinancingNeedRepository()
        let viewModel = FinancingNeedViewModel(repository: repository)
        viewModel.setAmountText("3500000")
        viewModel.setPurpose(.productiveBusiness)
        viewModel.preferredTenorMonths = 18
        viewModel.notes = "  Inventory restock  "

        let receipt = await viewModel.submit()
        let submissions = await repository.submissions()

        XCTAssertEqual(receipt?.financingNeedID, "synthetic-financing-need-id")
        XCTAssertEqual(
            submissions,
            [
                FinancingNeed(
                    requestedAmount: 3_500_000,
                    purpose: .productiveBusiness,
                    preferredTenorMonths: 18,
                    urgency: .medium,
                    notes: "Inventory restock"
                )
            ]
        )
    }

    func testSubmitRequiresAmountAndPurpose() async {
        let repository = MockFinancingNeedRepository()
        let viewModel = FinancingNeedViewModel(repository: repository)

        let receipt = await viewModel.submit()
        let submissions = await repository.submissions()

        XCTAssertNil(receipt)
        XCTAssertTrue(viewModel.hasAttemptedSubmission)
        XCTAssertTrue(submissions.isEmpty)
    }

    func testUnavailableRepositoryProducesRetryableFailure() async {
        let viewModel = FinancingNeedViewModel(
            repository: MockFinancingNeedRepository(error: .unavailable)
        )
        viewModel.setAmountText("3500000")
        viewModel.setPurpose(.medical)

        _ = await viewModel.submit()

        XCTAssertEqual(viewModel.state, .failed(errorKey: "financing_need.error.unavailable"))
        viewModel.retry()
        XCTAssertEqual(viewModel.state, .editing)
    }
}
