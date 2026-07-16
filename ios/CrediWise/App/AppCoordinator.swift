import Combine
import Foundation

@MainActor
final class AppCoordinator: ObservableObject {
    @Published var path: [AppRoute] = []

    let sessionManager: SessionManager

    private let authenticationRepository: any AuthenticationRepository
    private let documentUploadRepository: any DocumentUploadRepository
    private let uploadPollingPolicy: DocumentUploadPollingPolicy
    private let allowsSyntheticUpload: Bool
    private let isDocumentUploadAvailable: Bool

    init(
        sessionManager: SessionManager,
        authenticationRepository: any AuthenticationRepository,
        documentUploadRepository: any DocumentUploadRepository,
        uploadPollingPolicy: DocumentUploadPollingPolicy = DocumentUploadPollingPolicy(),
        allowsSyntheticUpload: Bool = false,
        isDocumentUploadAvailable: Bool = true
    ) {
        self.sessionManager = sessionManager
        self.authenticationRepository = authenticationRepository
        self.documentUploadRepository = documentUploadRepository
        self.uploadPollingPolicy = uploadPollingPolicy
        self.allowsSyntheticUpload = allowsSyntheticUpload
        self.isDocumentUploadAvailable = isDocumentUploadAvailable
    }

    convenience init() {
        self.init(
            sessionManager: SessionManager(tokenStore: VolatileTokenStore()),
            authenticationRepository: MockAuthenticationRepository(),
            documentUploadRepository: MockDocumentUploadRepository()
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
