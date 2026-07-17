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
        let isCycle6Flow = ProcessInfo.processInfo.arguments.contains("--cycle-6-flow")
        let isCycle5Flow = ProcessInfo.processInfo.arguments.contains("--cycle-5-flow") || isCycle6Flow
        let dependencies = isUITesting
            ? AppDependencies(
                authenticationRepository: MockAuthenticationRepository(),
                documentUploadRepository: MockDocumentUploadRepository(
                    statuses: ProcessInfo.processInfo.arguments.contains("--review-flow") || isCycle5Flow
                        ? [.reviewPending]
                        : [.securityCheck, .complete]
                ),
                documentVerificationRepository: MockDocumentVerificationRepository(),
                financingNeedRepository: MockFinancingNeedRepository(),
                assessmentDashboardRepository: MockAssessmentDashboardRepository(),
                shockRepository: MockShockRepository(),
                offerRepository: MockOfferRepository(),
                isDocumentUploadAvailable: true
            )
            : makeProductionDependencies(tokenStore: tokenStore, sessionManager: sessionManager)

        return AppCoordinator(
            sessionManager: sessionManager,
            dependencies: AppCoordinator.Dependencies(
                authenticationRepository: dependencies.authenticationRepository,
                documentUploadRepository: dependencies.documentUploadRepository,
                documentVerificationRepository: dependencies.documentVerificationRepository,
                financingNeedRepository: dependencies.financingNeedRepository,
                assessmentDashboardRepository: dependencies.assessmentDashboardRepository,
                shockRepository: dependencies.shockRepository,
                offerRepository: dependencies.offerRepository
            ),
            configuration: AppCoordinator.Configuration(
                allowsSyntheticUpload: isUITesting,
                isDocumentUploadAvailable: dependencies.isDocumentUploadAvailable,
                allowsSyntheticAssessment: isUITesting && isCycle5Flow,
                allowsSyntheticCycle6: isUITesting && isCycle6Flow
            )
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
                financingNeedRepository: UnavailableFinancingNeedRepository(),
                assessmentDashboardRepository: UnavailableAssessmentDashboardRepository(),
                shockRepository: UnavailableShockRepository(),
                offerRepository: UnavailableOfferRepository(),
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
            documentVerificationRepository: APIDocumentVerificationRepository(
                baseURL: baseURL,
                authInterceptor: authInterceptor
            ),
            financingNeedRepository: APIFinancingNeedRepository(
                baseURL: baseURL,
                authInterceptor: authInterceptor
            ),
            assessmentDashboardRepository: APIAssessmentDashboardRepository(
                baseURL: baseURL,
                authInterceptor: authInterceptor,
                verificationRepository: APIDocumentVerificationRepository(
                    baseURL: baseURL,
                    authInterceptor: authInterceptor
                )
            ),
            shockRepository: UnavailableShockRepository(),
            offerRepository: UnavailableOfferRepository(),
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
    let financingNeedRepository: any FinancingNeedRepository
    let assessmentDashboardRepository: any AssessmentDashboardRepository
    let shockRepository: any ShockRepository
    let offerRepository: any OfferRepository
    let isDocumentUploadAvailable: Bool
}
