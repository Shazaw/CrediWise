import XCTest
@testable import CrediWise

@MainActor
final class DataConfidenceViewModelTests: XCTestCase {
    func testLoadsServerSuppliedScoreDimensionsAndReasonsWithoutRecalculation() async {
        let report = MockDocumentVerificationRepository.makeConfidenceReport()
        let viewModel = DataConfidenceViewModel(
            documentID: "synthetic-document-id",
            repository: MockDocumentVerificationRepository(confidenceReport: report)
        )

        await viewModel.load()

        XCTAssertEqual(viewModel.state, .loaded(report))
        XCTAssertEqual(report.score, 92)
        XCTAssertEqual(report.dimensions.count, 7)
        XCTAssertGreaterThanOrEqual(report.reasons.count, 3)
    }

    func testKeepsDataConfidenceSeparateFromFinancialBehaviour() async {
        let report = DataConfidenceReport(
            score: 42,
            band: .low,
            dimensions: [],
            reasons: [],
            recommendationKey: "confidence.recommendation.low",
            assistanceStatus: .notUsed,
            modelVersion: "trust-v1"
        )
        let viewModel = DataConfidenceViewModel(
            documentID: "synthetic-document-id",
            repository: MockDocumentVerificationRepository(confidenceReport: report)
        )

        await viewModel.load()

        XCTAssertEqual(viewModel.state, .loaded(report))
        XCTAssertEqual(report.band, .low)
        XCTAssertEqual(report.recommendationKey, "confidence.recommendation.low")
    }

    func testUnavailableReportOffersRetryableFailure() async {
        let viewModel = DataConfidenceViewModel(
            documentID: "synthetic-document-id",
            repository: UnavailableDocumentVerificationRepository()
        )

        await viewModel.load()

        XCTAssertEqual(viewModel.state, .failed(errorKey: "confidence.error.unavailable"))
    }
}
