import SwiftUI

struct AppRootView: View {
    @ObservedObject var coordinator: AppCoordinator

    var body: some View {
        NavigationStack(path: $coordinator.path) {
            WelcomeView(
                onCreateAccount: coordinator.showRegistration,
                onSignIn: coordinator.showSignIn
            )
            .navigationDestination(for: AppRoute.self) { route in
                destination(for: route)
            }
        }
        .tint(CrediWiseColors.primary)
    }

    @ViewBuilder
    private func destination(for route: AppRoute) -> some View {
        switch route {
        case .registration:
            AuthPlaceholderView(
                titleKey: "auth.registration.placeholder.title",
                messageKey: "auth.registration.placeholder.message"
            )
        case .signIn:
            AuthPlaceholderView(
                titleKey: "auth.sign_in.placeholder.title",
                messageKey: "auth.sign_in.placeholder.message"
            )
        }
    }
}
