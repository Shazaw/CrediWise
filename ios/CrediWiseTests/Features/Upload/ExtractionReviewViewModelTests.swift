import XCTest
@testable import CrediWise

@MainActor
final class ExtractionReviewViewModelTests: XCTestCase {
    func testCorrectionPreservesRawAndNormalizedEvidence() async {
        let repository = MockDocumentVerificationRepository()
        let viewModel = ExtractionReviewViewModel(
            documentID: "synthetic-document-id",
            repository: repository
        )
        await viewModel.load()

        viewModel.proposeDate("4 Jun 2026", for: "transaction-1")
        viewModel.proposeAmount(2_500_000, for: "transaction-1")
        viewModel.proposeCategory(.unknown, for: "transaction-1")

        guard case let .loaded(ready) = viewModel.state,
              let transaction = ready.review.transactions.first,
              let correction = ready.correction(for: transaction.id) else {
            return XCTFail("Expected review with a proposed correction")
        }
        XCTAssertEqual(transaction.amount.raw, 2_450_000)
        XCTAssertEqual(transaction.amount.normalized, 2_450_000)
        XCTAssertEqual(transaction.category.raw, .unknown)
        XCTAssertEqual(transaction.category.normalized, .income)
        XCTAssertEqual(correction.proposedDate, "4 Jun 2026")
        XCTAssertEqual(correction.proposedAmount, 2_500_000)
        XCTAssertEqual(correction.proposedCategory, .unknown)
    }

    func testReturningToNormalizedValueRemovesCorrection() async {
        let viewModel = ExtractionReviewViewModel(
            documentID: "synthetic-document-id",
            repository: MockDocumentVerificationRepository()
        )
        await viewModel.load()
        viewModel.proposeAmount(2_500_000, for: "transaction-1")

        viewModel.proposeAmount(2_450_000, for: "transaction-1")

        guard case let .loaded(ready) = viewModel.state else {
            return XCTFail("Expected loaded review")
        }
        XCTAssertTrue(ready.corrections.isEmpty)
    }

    func testConfirmationRequiresOwnershipAndSubmitsOnce() async {
        let repository = MockDocumentVerificationRepository()
        let viewModel = ExtractionReviewViewModel(
            documentID: "synthetic-document-id",
            repository: repository
        )
        await viewModel.load()

        await viewModel.confirm()
        let submissionsBeforeOwnership = await repository.submittedReviews()
        XCTAssertTrue(submissionsBeforeOwnership.isEmpty)

        viewModel.setOwnershipConfirmed(true)
        viewModel.setReportsMissingRows(true)
        await viewModel.confirm()
        await viewModel.confirm()

        let submissions = await repository.submittedReviews()
        XCTAssertEqual(submissions.count, 1)
        XCTAssertTrue(submissions[0].confirmsOwnership)
        XCTAssertFalse(submissions[0].reportsOwnershipConcern)
        XCTAssertTrue(submissions[0].reportsMissingRows)
        XCTAssertEqual(viewModel.state, .confirmed(documentID: "synthetic-document-id"))
    }

    func testUnavailableReviewOffersRetryableFailure() async {
        let viewModel = ExtractionReviewViewModel(
            documentID: "synthetic-document-id",
            repository: UnavailableDocumentVerificationRepository()
        )

        await viewModel.load()

        XCTAssertEqual(viewModel.state, .failed(nil, errorKey: "review.error.unavailable"))
    }

    func testInvalidVisibleInputPreventsSubmittingStaleCorrection() async {
        let repository = MockDocumentVerificationRepository()
        let viewModel = ExtractionReviewViewModel(
            documentID: "synthetic-document-id",
            repository: repository
        )
        await viewModel.load()
        viewModel.proposeAmount(2_500_000, for: "transaction-1")
        viewModel.setTransactionInputValid(false, for: "transaction-1")
        viewModel.setOwnershipConfirmed(true)

        await viewModel.confirm()

        let submissions = await repository.submittedReviews()
        XCTAssertTrue(submissions.isEmpty)
    }

    func testOwnershipConcernCanBeSubmittedWithoutClaimingOwnership() async {
        let repository = MockDocumentVerificationRepository()
        let viewModel = ExtractionReviewViewModel(
            documentID: "synthetic-document-id",
            repository: repository
        )
        await viewModel.load()
        viewModel.setReportsOwnershipConcern(true)

        await viewModel.confirm()

        let submissions = await repository.submittedReviews()
        XCTAssertEqual(submissions.count, 1)
        XCTAssertFalse(submissions[0].confirmsOwnership)
        XCTAssertTrue(submissions[0].reportsOwnershipConcern)
    }

    func testChangedReviewReloadsInsteadOfResubmittingStaleEvidence() async {
        let repository = MockDocumentVerificationRepository(confirmationError: .reviewChanged)
        let viewModel = ExtractionReviewViewModel(
            documentID: "synthetic-document-id",
            repository: repository
        )
        await viewModel.load()
        viewModel.proposeAmount(2_500_000, for: "transaction-1")
        viewModel.setOwnershipConfirmed(true)
        await viewModel.confirm()

        await viewModel.retry()

        let reviewCallCount = await repository.reviewCallCount()
        XCTAssertEqual(reviewCallCount, 2)
        guard case let .loaded(ready) = viewModel.state else {
            return XCTFail("Expected refreshed review")
        }
        XCTAssertTrue(ready.corrections.isEmpty)
        XCTAssertFalse(ready.confirmsOwnership)
    }

    func testAlreadyConfirmedResponseContinuesWithoutDuplicateSubmission() async {
        let viewModel = ExtractionReviewViewModel(
            documentID: "synthetic-document-id",
            repository: MockDocumentVerificationRepository(confirmationError: .alreadyConfirmed)
        )
        await viewModel.load()
        viewModel.setOwnershipConfirmed(true)

        await viewModel.confirm()

        XCTAssertEqual(viewModel.state, .confirmed(documentID: "synthetic-document-id"))
    }
}
