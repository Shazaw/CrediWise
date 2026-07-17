import Combine
import Foundation

@MainActor
final class AppCoordinator: ObservableObject {
    struct Dependencies {
        let authenticationRepository: any AuthenticationRepository
        let documentUploadRepository: any DocumentUploadRepository
        let documentVerificationRepository: any DocumentVerificationRepository
        let financingNeedRepository: any FinancingNeedRepository
        let assessmentDashboardRepository: any AssessmentDashboardRepository
        let shockRepository: any ShockRepository
        let offerRepository: any OfferRepository
    }

    struct Configuration {
        let uploadPollingPolicy: DocumentUploadPollingPolicy
        let allowsSyntheticUpload: Bool
        let isDocumentUploadAvailable: Bool
        let allowsSyntheticAssessment: Bool
        let allowsSyntheticCycle6: Bool

        init(
            uploadPollingPolicy: DocumentUploadPollingPolicy = DocumentUploadPollingPolicy(),
            allowsSyntheticUpload: Bool = false,
            isDocumentUploadAvailable: Bool = true,
            allowsSyntheticAssessment: Bool = false,
            allowsSyntheticCycle6: Bool = false
        ) {
            self.uploadPollingPolicy = uploadPollingPolicy
            self.allowsSyntheticUpload = allowsSyntheticUpload
            self.isDocumentUploadAvailable = isDocumentUploadAvailable
            self.allowsSyntheticAssessment = allowsSyntheticAssessment
            self.allowsSyntheticCycle6 = allowsSyntheticCycle6
        }
    }

    @Published var path: [AppRoute] = []

    let sessionManager: SessionManager

    private let authenticationRepository: any AuthenticationRepository
    private let documentUploadRepository: any DocumentUploadRepository
    private let documentVerificationRepository: any DocumentVerificationRepository
    private let financingNeedRepository: any FinancingNeedRepository
    private let assessmentDashboardRepository: any AssessmentDashboardRepository
    private let shockRepository: any ShockRepository
    private let offerRepository: any OfferRepository
    private let uploadPollingPolicy: DocumentUploadPollingPolicy
    private let allowsSyntheticUpload: Bool
    private let isDocumentUploadAvailable: Bool
    private let allowsSyntheticAssessment: Bool
    private let allowsSyntheticCycle6: Bool
    private(set) var financingNeedID: String?

    init(
        sessionManager: SessionManager,
        dependencies: Dependencies,
        configuration: Configuration = Configuration()
    ) {
        self.sessionManager = sessionManager
        authenticationRepository = dependencies.authenticationRepository
        documentUploadRepository = dependencies.documentUploadRepository
        documentVerificationRepository = dependencies.documentVerificationRepository
        financingNeedRepository = dependencies.financingNeedRepository
        assessmentDashboardRepository = dependencies.assessmentDashboardRepository
        shockRepository = dependencies.shockRepository
        offerRepository = dependencies.offerRepository
        uploadPollingPolicy = configuration.uploadPollingPolicy
        allowsSyntheticUpload = configuration.allowsSyntheticUpload
        isDocumentUploadAvailable = configuration.isDocumentUploadAvailable
        allowsSyntheticAssessment = configuration.allowsSyntheticAssessment
        allowsSyntheticCycle6 = configuration.allowsSyntheticCycle6
    }

    convenience init() {
        self.init(
            sessionManager: SessionManager(tokenStore: VolatileTokenStore()),
            dependencies: Dependencies(
                authenticationRepository: MockAuthenticationRepository(),
                documentUploadRepository: MockDocumentUploadRepository(),
                documentVerificationRepository: MockDocumentVerificationRepository(),
                financingNeedRepository: MockFinancingNeedRepository(),
                assessmentDashboardRepository: MockAssessmentDashboardRepository(),
                shockRepository: MockShockRepository(),
                offerRepository: MockOfferRepository()
            )
        )
    }

    func showRegistration() {
        path.append(.registration)
    }

    func showSignIn() {
        path.append(.signIn)
    }

    func showUpload() {
        path.append(.upload)
    }

    func showFinancingNeed() {
        path.append(.financingNeed)
    }

    func completeFinancingNeed(_ receipt: FinancingNeedReceipt) {
        financingNeedID = receipt.financingNeedID
        path.append(.upload)
    }

    func showExtractionReview(documentID: String) {
        path.append(.extractionReview(documentID: documentID))
    }

    func showDataConfidence(documentID: String) {
        path.append(.dataConfidence(documentID: documentID))
    }

    func showAssessmentDashboard(assessmentID: String) {
        path.append(.assessmentDashboard(assessmentID: assessmentID))
    }

    func showShockSimulation(assessmentID: String) {
        path.append(.shockSimulation(assessmentID: assessmentID))
    }

    func showOffers(assessmentID: String) {
        path.append(.offers(assessmentID: assessmentID))
    }

    func showOfferDetail(assessmentID: String, offerID: String) {
        path.append(.offerDetail(assessmentID: assessmentID, offerID: offerID))
    }

    func createAssessment(documentID: String) async throws {
        guard let financingNeedID else {
            throw AssessmentDashboardRepositoryError.unavailable
        }
        let assessmentID = try await assessmentDashboardRepository.create(
            financingNeedID: financingNeedID,
            documentID: documentID
        )
        showAssessmentDashboard(assessmentID: assessmentID)
    }

    func returnToWelcome() {
        path.removeAll()
    }

    func completeRegistration() {
        path = [.signIn]
    }

    func completeSignIn() {
        path.removeAll()
    }

    func switchAuthenticationMode(from mode: AuthenticationMode) {
        path = [mode == .registration ? .signIn : .registration]
    }

    func makeAuthenticationViewModel(mode: AuthenticationMode) -> AuthenticationViewModel {
        AuthenticationViewModel(
            mode: mode,
            repository: authenticationRepository,
            sessionManager: sessionManager
        )
    }

    func makeUploadViewModel() -> UploadViewModel {
        UploadViewModel(
            repository: documentUploadRepository,
            pollingPolicy: uploadPollingPolicy
        )
    }

    func makeFinancingNeedViewModel() -> FinancingNeedViewModel {
        FinancingNeedViewModel(repository: financingNeedRepository)
    }

    func makeExtractionReviewViewModel(documentID: String) -> ExtractionReviewViewModel {
        ExtractionReviewViewModel(
            documentID: documentID,
            repository: documentVerificationRepository
        )
    }

    func makeDataConfidenceViewModel(documentID: String) -> DataConfidenceViewModel {
        DataConfidenceViewModel(
            documentID: documentID,
            repository: documentVerificationRepository
        )
    }

    func makeAssessmentDashboardViewModel(assessmentID: String) -> AssessmentDashboardViewModel {
        AssessmentDashboardViewModel(
            assessmentID: assessmentID,
            repository: assessmentDashboardRepository
        )
    }

    func makeShockViewModel(assessmentID: String) -> ShockViewModel {
        ShockViewModel(assessmentID: assessmentID, repository: shockRepository)
    }

    func makeOffersViewModel(assessmentID: String) -> OffersViewModel {
        OffersViewModel(assessmentID: assessmentID, repository: offerRepository)
    }

    func makeOfferDetailViewModel(assessmentID: String, offerID: String) -> OfferDetailViewModel {
        OfferDetailViewModel(
            assessmentID: assessmentID,
            offerID: offerID,
            repository: offerRepository
        )
    }

    var shouldOfferSyntheticUpload: Bool {
        allowsSyntheticUpload
    }

    var shouldEnableDocumentUpload: Bool {
        isDocumentUploadAvailable
    }

    var shouldOfferSyntheticAssessment: Bool {
        allowsSyntheticAssessment
    }

    var shouldOfferSyntheticCycle6: Bool {
        allowsSyntheticCycle6
    }

    func signOut() async {
        try? await authenticationRepository.signOut()
        await sessionManager.signOut()
        financingNeedID = nil
        path.removeAll()
    }
}
