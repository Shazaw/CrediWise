actor MockAuthenticationRepository: AuthenticationRepository {
    func register(email: String, password: String) async throws {
        if email.lowercased() == "existing@example.com" {
            throw AuthenticationRepositoryError.duplicateEmail
        }
    }

    func signIn(email: String, password: String) async throws -> SessionTokens {
        if email.lowercased() == "blocked@example.com" {
            throw AuthenticationRepositoryError.invalidCredentials
        }
        return SessionTokens(
            accessToken: "synthetic-access-token",
            refreshToken: "synthetic-refresh-token"
        )
    }

    func signOut() async throws {}
}
