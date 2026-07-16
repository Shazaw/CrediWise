import XCTest
@testable import CrediWise

@MainActor
final class SessionManagerTests: XCTestCase {
    func testRestoreSignsInWhenTokensExist() async throws {
        let store = VolatileTokenStore(tokens: makeTokens())
        let manager = SessionManager(tokenStore: store)

        await manager.restore()

        XCTAssertEqual(manager.state, .signedIn)
    }

    func testRestoreSignsOutWhenTokensAreMissing() async {
        let manager = SessionManager(tokenStore: VolatileTokenStore())

        await manager.restore()

        XCTAssertEqual(manager.state, .signedOut)
    }

    func testEstablishPersistsTokensBeforeSigningIn() async throws {
        let store = VolatileTokenStore()
        let manager = SessionManager(tokenStore: store)
        let tokens = makeTokens()

        try await manager.establish(tokens)

        XCTAssertEqual(manager.state, .signedIn)
        let storedTokens = try await store.load()
        XCTAssertEqual(storedTokens, tokens)
    }

    func testSignOutClearsTokens() async throws {
        let store = VolatileTokenStore(tokens: makeTokens())
        let manager = SessionManager(tokenStore: store)
        await manager.restore()

        await manager.signOut()

        XCTAssertEqual(manager.state, .signedOut)
        let storedTokens = try await store.load()
        XCTAssertNil(storedTokens)
    }

    func testTransientStoreFailurePreservesCredentialsForRetry() async {
        let store = FailingTokenStore()
        let manager = SessionManager(tokenStore: store)

        await manager.restore()

        XCTAssertEqual(manager.state, .restorationFailed)
        let clearCount = await store.clearCount
        XCTAssertEqual(clearCount, 0)
    }

    private func makeTokens() -> SessionTokens {
        SessionTokens(accessToken: "access", refreshToken: "refresh")
    }

    private actor FailingTokenStore: TokenStore {
        private(set) var clearCount = 0

        func load() async throws -> SessionTokens? {
            throw TokenStoreError.unexpectedStatus(-1)
        }

        func save(_ tokens: SessionTokens) async throws {}

        func clear() async throws {
            clearCount += 1
        }
    }
}
