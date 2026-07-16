enum AuthenticationRepositoryError: Error, Equatable {
    case duplicateEmail
    case invalidCredentials
    case rateLimited
    case unavailable
}
