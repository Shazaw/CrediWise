import Combine
import Foundation

@MainActor
final class AppCoordinator: ObservableObject {
    @Published var path: [AppRoute] = []

    let sessionManager: SessionManager

    private let authenticationRepository: any AuthenticationRepository
    private let documentUploadRepository: any DocumentUploadRepository
    private let documentVerificationRepository: any DocumentVerificationRepository
    private let uploadPollingPolicy: DocumentUploadPollingPolicy
    private let allowsSyntheticUpload: Bool
    private let isDocumentUploadAvailable: Bool

    init(
        sessionManager: SessionManager,
        authenticationRepository: any AuthenticationRepository,
        documentUploadRepository: any DocumentUploadRepository,
        documentVerificationRepository: any DocumentVerificationRepository,
        uploadPollingPolicy: DocumentUploadPollingPolicy = DocumentUploadPollingPolicy(),
        allowsSyntheticUpload: Bool = false,
        isDocumentUploadAvailable: Bool = true
    ) {
        self.sessionManager = sessionManager
        self.authenticationRepository = authenticationRepository
        self.documentUploadRepository = documentUploadRepository
        self.documentVerificationRepository = documentVerificationRepository
        self.uploadPollingPolicy = uploadPollingPolicy
        self.allowsSyntheticUpload = allowsSyntheticUpload
        self.isDocumentUploadAvailable = isDocumentUploadAvailable
    }

    convenience init() {
        self.init(
            sessionManager: SessionManager(tokenStore: VolatileTokenStore()),
            authenticationRepository: MockAuthenticationRepository(),
            documentUploadRepository: MockDocumentUploadRepository(),
            documentVerificationRepository: MockDocumentVerificationRepository()
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

    func showExtractionReview(documentID: String) {
        path.append(.extractionReview(documentID: documentID))
    }

    func showDataConfidence(documentID: String) {
        path.append(.dataConfidence(documentID: documentID))
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

    var shouldOfferSyntheticUpload: Bool {
        allowsSyntheticUpload
    }

    var shouldEnableDocumentUpload: Bool {
        isDocumentUploadAvailable
    }

    func signOut() async {
        try? await authenticationRepository.signOut()
        await sessionManager.signOut()
        path.removeAll()
    }
}
