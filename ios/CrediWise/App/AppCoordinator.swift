import Combine
import Foundation

@MainActor
final class AppCoordinator: ObservableObject {
    @Published var path: [AppRoute] = []

    let sessionManager: SessionManager

    private let authenticationRepository: any AuthenticationRepository
    private let documentUploadRepository: any DocumentUploadRepository
    private let documentVerificationRepository: any DocumentVerificationRepository
    private let financingNeedRepository: any FinancingNeedRepository
    private let assessmentDashboardRepository: any AssessmentDashboardRepository
    private let uploadPollingPolicy: DocumentUploadPollingPolicy
    private let allowsSyntheticUpload: Bool
    private let isDocumentUploadAvailable: Bool
    private let allowsSyntheticAssessment: Bool
    private(set) var financingNeedID: String?

    init(
        sessionManager: SessionManager,
        authenticationRepository: any AuthenticationRepository,
        documentUploadRepository: any DocumentUploadRepository,
        documentVerificationRepository: any DocumentVerificationRepository,
        financingNeedRepository: any FinancingNeedRepository,
        assessmentDashboardRepository: any AssessmentDashboardRepository,
        uploadPollingPolicy: DocumentUploadPollingPolicy = DocumentUploadPollingPolicy(),
        allowsSyntheticUpload: Bool = false,
        isDocumentUploadAvailable: Bool = true,
        allowsSyntheticAssessment: Bool = false
    ) {
        self.sessionManager = sessionManager
        self.authenticationRepository = authenticationRepository
        self.documentUploadRepository = documentUploadRepository
        self.documentVerificationRepository = documentVerificationRepository
        self.financingNeedRepository = financingNeedRepository
        self.assessmentDashboardRepository = assessmentDashboardRepository
        self.uploadPollingPolicy = uploadPollingPolicy
        self.allowsSyntheticUpload = allowsSyntheticUpload
        self.isDocumentUploadAvailable = isDocumentUploadAvailable
        self.allowsSyntheticAssessment = allowsSyntheticAssessment
    }

    convenience init() {
        self.init(
            sessionManager: SessionManager(tokenStore: VolatileTokenStore()),
            authenticationRepository: MockAuthenticationRepository(),
            documentUploadRepository: MockDocumentUploadRepository(),
            documentVerificationRepository: MockDocumentVerificationRepository(),
            financingNeedRepository: MockFinancingNeedRepository(),
            assessmentDashboardRepository: MockAssessmentDashboardRepository()
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

    func showSyntheticAssessmentDashboard() {
        guard allowsSyntheticAssessment else { return }
        showAssessmentDashboard(assessmentID: "synthetic-assessment-id")
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

    var shouldOfferSyntheticUpload: Bool {
        allowsSyntheticUpload
    }

    var shouldEnableDocumentUpload: Bool {
        isDocumentUploadAvailable
    }

    var shouldOfferSyntheticAssessment: Bool {
        allowsSyntheticAssessment
    }

    func signOut() async {
        try? await authenticationRepository.signOut()
        await sessionManager.signOut()
        financingNeedID = nil
        path.removeAll()
    }
}
