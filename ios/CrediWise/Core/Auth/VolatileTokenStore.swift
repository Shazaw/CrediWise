actor VolatileTokenStore: TokenStore {
    private var tokens: SessionTokens?

    init(tokens: SessionTokens? = nil) {
        self.tokens = tokens
    }

    func load() async throws -> SessionTokens? {
        tokens
    }

    func save(_ tokens: SessionTokens) async throws {
        self.tokens = tokens
    }

    func clear() async throws {
        tokens = nil
    }
}
