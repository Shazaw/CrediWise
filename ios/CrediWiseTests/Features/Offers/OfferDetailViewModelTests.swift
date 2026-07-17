import XCTest
@testable import CrediWise

@MainActor
final class OfferDetailViewModelTests: XCTestCase {
    func testLoadForwardsAssessmentAndOfferIdentity() async {
        let offers = MockOfferRepository.makeOffers()
        let repository = MockOfferRepository(offers: offers)
        let viewModel = OfferDetailViewModel(
            assessmentID: "assessment-789",
            offerID: "offer-unsafe",
            repository: repository
        )

        await viewModel.load()
        let requests = await repository.detailRequests()

        XCTAssertEqual(
            requests,
            [
                .init(
                    assessmentID: "assessment-789",
                    offerID: "offer-unsafe"
                )
            ]
        )
        guard case let .loaded(offer) = viewModel.state else {
            return XCTFail("Expected loaded offer")
        }
        XCTAssertEqual(offer.assessmentID, "assessment-789")
        XCTAssertEqual(offer.offerID, "offer-unsafe")
        XCTAssertEqual(offer.band, .unsafe)
        XCTAssertEqual(offer.provider.status, .simulatedRegulatedProvider)
        XCTAssertEqual(
            offer.warnings.map(\.code),
            ["REFINANCING_DEPENDENCY_RISK"]
        )
    }

    func testFailureCanRetryWithoutInventingOffer() async {
        let repository = MockOfferRepository(error: .unavailable)
        let viewModel = OfferDetailViewModel(
            assessmentID: "assessment-789",
            offerID: "offer-safe",
            repository: repository
        )

        await viewModel.load()
        XCTAssertEqual(viewModel.state, .failed(errorKey: "offers.error.unavailable"))

        await viewModel.retry()
        let requests = await repository.detailRequests()
        XCTAssertEqual(viewModel.state, .failed(errorKey: "offers.error.unavailable"))
        XCTAssertEqual(
            requests,
            [
                .init(assessmentID: "assessment-789", offerID: "offer-safe"),
                .init(assessmentID: "assessment-789", offerID: "offer-safe")
            ]
        )
    }
}
