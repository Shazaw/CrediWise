import Foundation

struct AppContainer {
    @MainActor
    func makeAppCoordinator() -> AppCoordinator {
        let isUITesting = ProcessInfo.processInfo.arguments.contains("--ui-testing")
        let tokenStore: any TokenStore
        let authenticationRepository: any AuthenticationRepository
        let documentUploadRepository: any DocumentUploadRepository
        let uploadPollingPolicy: DocumentUploadPollingPolicy
        let isDocumentUploadAvailable: Bool

        if isUITesting {
            tokenStore = VolatileTokenStore()
        } else {
            tokenStore = KeychainTokenStore(
                service: Bundle.main.bundleIdentifier ?? "com.crediwise.app"
            )
        }
        let sessionManager = SessionManager(tokenStore: tokenStore)

        if isUITesting {
            authenticationRepository = MockAuthenticationRepository()
            documentUploadRepository = MockDocumentUploadRepository(
                statuses: [.securityCheck, .complete]
            )
            uploadPollingPolicy = DocumentUploadPollingPolicy()
            isDocumentUploadAvailable = true
        } else {
            if let baseURL = apiBaseURL() {
                let apiAuthenticationRepository = APIAuthenticationRepository(
                    baseURL: baseURL,
                    tokenStore: tokenStore
                )
                authenticationRepository = apiAuthenticationRepository
                let authInterceptor = AuthInterceptor(
                    tokenStore: tokenStore,
                    refreshHandler: { refreshToken in
                        try await apiAuthenticationRepository.refresh(refreshToken: refreshToken)
                    },
                    unauthorizedHandler: {
                        await sessionManager.signOut()
                    }
                )
                documentUploadRepository = APIDocumentUploadRepository(
                    baseURL: baseURL,
                    authInterceptor: authInterceptor
                )
                isDocumentUploadAvailable = true
            } else {
                authenticationRepository = UnavailableAuthenticationRepository()
                documentUploadRepository = UnavailableDocumentUploadRepository()
                isDocumentUploadAvailable = false
            }
            uploadPollingPolicy = DocumentUploadPollingPolicy()
        }

        return AppCoordinator(
            sessionManager: sessionManager,
            authenticationRepository: authenticationRepository,
            documentUploadRepository: documentUploadRepository,
            uploadPollingPolicy: uploadPollingPolicy,
            allowsSyntheticUpload: isUITesting,
            isDocumentUploadAvailable: isDocumentUploadAvailable
        )
    }

    private func apiBaseURL() -> URL? {
        if let override = ProcessInfo.processInfo.environment["CREDIWISE_API_BASE_URL"] {
            return URL(string: override)
        }

        #if DEBUG
        return URL(string: "http://127.0.0.1:8000")
        #else
        return nil
        #endif
    }
}
