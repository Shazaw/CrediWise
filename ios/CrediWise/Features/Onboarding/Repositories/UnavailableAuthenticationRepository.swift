actor UnavailableAuthenticationRepository: AuthenticationRepository {
    func register(email: String, password: String) async throws {
        throw AuthenticationRepositoryError.unavailable
    }

    func signIn(email: String, password: String) async throws -> SessionTokens {
        throw AuthenticationRepositoryError.unavailable
    }

    func signOut() async throws {
        throw AuthenticationRepositoryError.unavailable
    }
}
