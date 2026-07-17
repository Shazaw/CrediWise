import XCTest
@testable import CrediWise

@MainActor
final class AppCoordinatorTests: XCTestCase {
    func testStartsAtWelcome() {
        let coordinator = AppCoordinator()

        XCTAssertTrue(coordinator.path.isEmpty)
    }

    func testRoutesToRegistration() {
        let coordinator = AppCoordinator()

        coordinator.showRegistration()

        XCTAssertEqual(coordinator.path, [.registration])
    }

    func testRoutesToSignIn() {
        let coordinator = AppCoordinator()

        coordinator.showSignIn()

        XCTAssertEqual(coordinator.path, [.signIn])
    }

    func testRoutesAuthenticatedUserToUpload() {
        let coordinator = AppCoordinator()

        coordinator.showUpload()

        XCTAssertEqual(coordinator.path, [.upload])
    }

    func testFinancingNeedPrecedesUpload() {
        let coordinator = AppCoordinator()
        coordinator.showFinancingNeed()
        coordinator.completeFinancingNeed(
            FinancingNeedReceipt(financingNeedID: "need-123")
        )

        XCTAssertEqual(coordinator.path, [.financingNeed, .upload])
        XCTAssertEqual(coordinator.financingNeedID, "need-123")
    }

    func testRoutesDocumentFromUploadThroughReviewAndConfidence() {
        let coordinator = AppCoordinator()

        coordinator.showUpload()
        coordinator.showExtractionReview(documentID: "document-123")
        coordinator.showDataConfidence(documentID: "document-123")

        XCTAssertEqual(
            coordinator.path,
            [
                .upload,
                .extractionReview(documentID: "document-123"),
                .dataConfidence(documentID: "document-123")
            ]
        )
    }

    func testRoutesToAssessmentDashboardWithAssessmentIdentity() {
        let coordinator = AppCoordinator()

        coordinator.showAssessmentDashboard(assessmentID: "assessment-123")

        XCTAssertEqual(coordinator.path, [.assessmentDashboard(assessmentID: "assessment-123")])
    }

    func testCreatesAssessmentFromStoredNeedAndConfirmedDocument() async throws {
        let repository = MockAssessmentDashboardRepository()
        let coordinator = AppCoordinator(
            sessionManager: SessionManager(tokenStore: VolatileTokenStore()),
            authenticationRepository: MockAuthenticationRepository(),
            documentUploadRepository: MockDocumentUploadRepository(),
            documentVerificationRepository: MockDocumentVerificationRepository(),
            financingNeedRepository: MockFinancingNeedRepository(),
            assessmentDashboardRepository: repository
        )
        coordinator.completeFinancingNeed(FinancingNeedReceipt(financingNeedID: "need-123"))

        try await coordinator.createAssessment(documentID: "document-123")

        let creations = await repository.creations()
        XCTAssertEqual(creations.first?.0, "need-123")
        XCTAssertEqual(creations.first?.1, "document-123")
        XCTAssertEqual(
            coordinator.path.last,
            .assessmentDashboard(assessmentID: "synthetic-assessment-id")
        )
    }

    func testReturnsToWelcomeFromNestedRoute() {
        let coordinator = AppCoordinator()
        coordinator.showRegistration()
        coordinator.showSignIn()

        coordinator.returnToWelcome()

        XCTAssertTrue(coordinator.path.isEmpty)
    }

    func testCompletingRegistrationRoutesToSignIn() {
        let coordinator = AppCoordinator()
        coordinator.showRegistration()

        coordinator.completeRegistration()

        XCTAssertEqual(coordinator.path, [.signIn])
    }

    func testSwitchesAuthenticationModeWithoutStackingRoutes() {
        let coordinator = AppCoordinator()
        coordinator.showRegistration()

        coordinator.switchAuthenticationMode(from: .registration)

        XCTAssertEqual(coordinator.path, [.signIn])
    }
}
