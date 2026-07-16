import SwiftUI

@main
struct CrediWiseApp: App {
    @StateObject private var coordinator: AppCoordinator

    @MainActor
    init() {
        let container = AppContainer()
        _coordinator = StateObject(wrappedValue: container.makeAppCoordinator())
    }

    var body: some Scene {
        WindowGroup {
            AppRootView(coordinator: coordinator)
        }
    }
}
