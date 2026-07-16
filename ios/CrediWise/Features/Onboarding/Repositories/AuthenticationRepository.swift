protocol AuthenticationRepository: Sendable {
    func register(email: String, password: String) async throws
    func signIn(email: String, password: String) async throws -> SessionTokens
    func signOut() async throws
}
