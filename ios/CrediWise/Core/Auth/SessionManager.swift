import Combine
import Foundation

@MainActor
final class SessionManager: ObservableObject {
    @Published private(set) var state: SessionState = .restoring

    private let tokenStore: any TokenStore

    init(tokenStore: any TokenStore) {
        self.tokenStore = tokenStore
    }

    func restore() async {
        guard state == .restoring else {
            return
        }

        do {
            state = try await tokenStore.load() == nil ? .signedOut : .signedIn
        } catch TokenStoreError.invalidData {
            try? await tokenStore.clear()
            state = .signedOut
        } catch {
            state = .restorationFailed
        }
    }

    func retryRestoration() async {
        state = .restoring
        await restore()
    }

    func establish(_ tokens: SessionTokens) async throws {
        try await tokenStore.save(tokens)
        state = .signedIn
    }

    func signOut() async {
        try? await tokenStore.clear()
        state = .signedOut
    }
}
