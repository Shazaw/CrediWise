import Foundation

struct AppContainer {
    @MainActor
    func makeAppCoordinator() -> AppCoordinator {
        let isUITesting = ProcessInfo.processInfo.arguments.contains("--ui-testing")
        let tokenStore: any TokenStore
        let authenticationRepository: any AuthenticationRepository

        if isUITesting {
            tokenStore = VolatileTokenStore()
            authenticationRepository = MockAuthenticationRepository()
        } else {
            tokenStore = KeychainTokenStore(
                service: Bundle.main.bundleIdentifier ?? "com.crediwise.app"
            )
            if let baseURL = apiBaseURL() {
                authenticationRepository = APIAuthenticationRepository(
                    baseURL: baseURL,
                    tokenStore: tokenStore
                )
            } else {
                authenticationRepository = UnavailableAuthenticationRepository()
            }
        }
        let sessionManager = SessionManager(tokenStore: tokenStore)

        return AppCoordinator(
            sessionManager: sessionManager,
            authenticationRepository: authenticationRepository
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
