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
            authenticationRepository = UnavailableAuthenticationRepository()
        }
        let sessionManager = SessionManager(tokenStore: tokenStore)

        return AppCoordinator(
            sessionManager: sessionManager,
            authenticationRepository: authenticationRepository
        )
    }
}
