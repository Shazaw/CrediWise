import Foundation

struct AppContainer {
    @MainActor
    func makeAppCoordinator() -> AppCoordinator {
        let isUITesting = ProcessInfo.processInfo.arguments.contains("--ui-testing")
        let tokenStore: any TokenStore = isUITesting
            ? VolatileTokenStore()
            : KeychainTokenStore(
                service: Bundle.main.bundleIdentifier ?? "com.crediwise.app"
            )
        let sessionManager = SessionManager(tokenStore: tokenStore)
        let dependencies = isUITesting
            ? AppDependencies(
                authenticationRepository: MockAuthenticationRepository(),
                documentUploadRepository: MockDocumentUploadRepository(
                    statuses: ProcessInfo.processInfo.arguments.contains("--review-flow")
                        ? [.reviewPending]
                        : [.securityCheck, .complete]
                ),
                documentVerificationRepository: MockDocumentVerificationRepository(),
                isDocumentUploadAvailable: true
            )
            : makeProductionDependencies(tokenStore: tokenStore, sessionManager: sessionManager)

        return AppCoordinator(
            sessionManager: sessionManager,
            authenticationRepository: dependencies.authenticationRepository,
            documentUploadRepository: dependencies.documentUploadRepository,
            documentVerificationRepository: dependencies.documentVerificationRepository,
            uploadPollingPolicy: DocumentUploadPollingPolicy(),
            allowsSyntheticUpload: isUITesting,
            isDocumentUploadAvailable: dependencies.isDocumentUploadAvailable
        )
    }

    @MainActor
    private func makeProductionDependencies(
        tokenStore: any TokenStore,
        sessionManager: SessionManager
    ) -> AppDependencies {
        guard let baseURL = apiBaseURL() else {
            return AppDependencies(
                authenticationRepository: UnavailableAuthenticationRepository(),
                documentUploadRepository: UnavailableDocumentUploadRepository(),
                documentVerificationRepository: UnavailableVerificationRepository(),
                isDocumentUploadAvailable: false
            )
        }

        let authenticationRepository = APIAuthenticationRepository(
            baseURL: baseURL,
            tokenStore: tokenStore
        )
        let authInterceptor = AuthInterceptor(
            tokenStore: tokenStore,
            refreshHandler: { refreshToken in
                try await authenticationRepository.refresh(refreshToken: refreshToken)
            },
            unauthorizedHandler: {
                await sessionManager.signOut()
            }
        )
        return AppDependencies(
            authenticationRepository: authenticationRepository,
            documentUploadRepository: APIDocumentUploadRepository(
                baseURL: baseURL,
                authInterceptor: authInterceptor
            ),
            documentVerificationRepository: UnavailableVerificationRepository(),
            isDocumentUploadAvailable: true
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

private struct AppDependencies {
    let authenticationRepository: any AuthenticationRepository
    let documentUploadRepository: any DocumentUploadRepository
    let documentVerificationRepository: any DocumentVerificationRepository
    let isDocumentUploadAvailable: Bool
}
