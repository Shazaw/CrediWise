import Combine
import Foundation

@MainActor
final class AppCoordinator: ObservableObject {
    @Published var path: [AppRoute] = []

    let sessionManager: SessionManager

    private let authenticationRepository: any AuthenticationRepository

    init(
        sessionManager: SessionManager,
        authenticationRepository: any AuthenticationRepository
    ) {
        self.sessionManager = sessionManager
        self.authenticationRepository = authenticationRepository
    }

    convenience init() {
        self.init(
            sessionManager: SessionManager(tokenStore: VolatileTokenStore()),
            authenticationRepository: MockAuthenticationRepository()
        )
    }

    func showRegistration() {
        path.append(.registration)
    }

    func showSignIn() {
        path.append(.signIn)
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

    func signOut() async {
        try? await authenticationRepository.signOut()
        await sessionManager.signOut()
        path.removeAll()
    }
}
