import XCTest
@testable import CrediWise

@MainActor
final class OffersViewModelTests: XCTestCase {
    func testLoadPreservesRepositoryOrderAndSuppliedSafetyValues() async {
        let supplied = MockOfferRepository.makeOffers()
        let repository = MockOfferRepository(offers: supplied)
        let viewModel = OffersViewModel(
            assessmentID: "assessment-123",
            repository: repository
        )

        await viewModel.load()
        let requests = await repository.listRequests()

        XCTAssertEqual(requests, ["assessment-123"])
        guard case let .loaded(offers) = viewModel.state else {
            return XCTFail("Expected loaded offers")
        }
        XCTAssertEqual(offers.map(\.offerID), ["offer-safe", "offer-caution", "offer-unsafe"])
        XCTAssertEqual(offers.map(\.assessmentID), Array(repeating: "assessment-123", count: 3))
        XCTAssertEqual(offers.map(\.suppliedRank), [1, 2, 3])
        XCTAssertTrue(offers[0].isSafest)
        XCTAssertEqual(offers[0].band, .safe)
        XCTAssertEqual(offers[0].provider.status, .simulatedRegulatedProvider)
        XCTAssertEqual(offers[2].provider.status, .simulatedRegulatedProvider)
        XCTAssertTrue(offers[2].refinancingDependency)
        XCTAssertEqual(
            offers[2].warnings.map(\.code),
            ["REFINANCING_DEPENDENCY_RISK", "INSUFFICIENT_ESSENTIAL_COVERAGE"]
        )
        XCTAssertTrue(offers.allSatisfy { $0.reasons.count >= 3 })
    }

    func testSyntheticLoanTermsRemainInternallyConsistent() {
        let offers = MockOfferRepository.makeOffers()
        let auditedEffectiveAnnualCosts = [38.96, 76.75, 148.66]

        for (offer, effectiveAnnualCost) in zip(offers, auditedEffectiveAnnualCosts) {
            XCTAssertEqual(offer.scheduledPayments.count, offer.tenorMonths)
            XCTAssertEqual(
                offer.scheduledPayments.reduce(Int64(0)) { $0 + $1.amount },
                offer.costs.totalScheduledRepayment
            )
            XCTAssertEqual(
                offer.principal + offer.costs.scheduledInterest + offer.costs.financedFees,
                offer.costs.totalScheduledRepayment
            )
            XCTAssertEqual(offer.principal - offer.costs.upfrontFees, offer.netAmountReceived)
            XCTAssertEqual(offer.costs.effectiveAnnualCostPercentage, effectiveAnnualCost)
        }
    }

    func testFailureRetryDoesNotInventOrReorderOffers() async {
        let repository = MockOfferRepository(error: .unavailable)
        let viewModel = OffersViewModel(
            assessmentID: "assessment-123",
            repository: repository
        )

        await viewModel.load()
        XCTAssertEqual(viewModel.state, .failed(errorKey: "offers.error.unavailable"))

        await viewModel.retry()
        let requests = await repository.listRequests()
        XCTAssertEqual(viewModel.state, .failed(errorKey: "offers.error.unavailable"))
        XCTAssertEqual(requests, ["assessment-123", "assessment-123"])
    }
}
