import Combine
import Foundation

@MainActor
final class AppCoordinator: ObservableObject {
    @Published var path: [AppRoute] = []

    func showRegistration() {
        path.append(.registration)
    }

    func showSignIn() {
        path.append(.signIn)
    }

    func returnToWelcome() {
        path.removeAll()
    }
}
