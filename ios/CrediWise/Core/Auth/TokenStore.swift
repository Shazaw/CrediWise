protocol TokenStore: Sendable {
    func load() async throws -> SessionTokens?
    func save(_ tokens: SessionTokens) async throws
    func clear() async throws
}
