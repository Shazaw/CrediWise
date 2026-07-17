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
                enablesCompleteAssessmentFlow: !isUITesting || isCycle6Flow
            )
        )
    }

    @MainActor
    private func makeProductionDependencies(
        tokenStore: any TokenStore,
        sessionManager: SessionManager
    ) -> AppDependencies {
        guard let baseURL = apiBaseURL() else {
            return unavailableDependencies()
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
        let verificationRepository = APIDocumentVerificationRepository(
            baseURL: baseURL,
            authInterceptor: authInterceptor
        )
        return AppDependencies(
            authenticationRepository: authenticationRepository,
            documentUploadRepository: APIDocumentUploadRepository(
                baseURL: baseURL,
                authInterceptor: authInterceptor
            ),
            documentVerificationRepository: verificationRepository,
            financingNeedRepository: APIFinancingNeedRepository(
                baseURL: baseURL,
                authInterceptor: authInterceptor
            ),
            assessmentDashboardRepository: APIAssessmentDashboardRepository(
                baseURL: baseURL,
                authInterceptor: authInterceptor,
                verificationRepository: verificationRepository
            ),
            shockRepository: APIShockRepository(
                baseURL: baseURL,
                authInterceptor: authInterceptor
            ),
            offerRepository: APIOfferRepository(
                baseURL: baseURL,
                authInterceptor: authInterceptor
            ),
            isDocumentUploadAvailable: true
        )
    }

    private func unavailableDependencies() -> AppDependencies {
        AppDependencies(
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

    private func apiBaseURL() -> URL? {
        let environmentValue = ProcessInfo.processInfo.environment["CREDIWISE_API_BASE_URL"]
        let bundleValue = Bundle.main.object(
            forInfoDictionaryKey: "CREDIWISE_API_BASE_URL"
        ) as? String
        #if DEBUG
        return Self.validatedAPIBaseURL(
            environmentValue: environmentValue,
            bundleValue: bundleValue,
            allowsInsecureLocalhost: true
        ) ?? URL(string: "http://127.0.0.1:8000")
        #else
        return Self.validatedAPIBaseURL(
            environmentValue: environmentValue,
            bundleValue: bundleValue,
            allowsInsecureLocalhost: false
        )
        #endif
    }

    static func validatedAPIBaseURL(
        environmentValue: String?,
        bundleValue: String?,
        allowsInsecureLocalhost: Bool
    ) -> URL? {
        let value = [environmentValue, bundleValue]
            .compactMap { $0?.trimmingCharacters(in: .whitespacesAndNewlines) }
            .first { !$0.isEmpty }
        guard let value, let url = URL(string: value), url.host?.isEmpty == false else {
            return nil
        }
        if url.scheme?.lowercased() == "https" {
            return url
        }
        let localHosts = ["127.0.0.1", "localhost", "::1"]
        guard allowsInsecureLocalhost,
              url.scheme?.lowercased() == "http",
              localHosts.contains(url.host?.lowercased() ?? "") else {
            return nil
        }
        return url
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
