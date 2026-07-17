enum AuthInterceptorError: Error, Equatable {
    case missingSession
    case refreshFailed
    case unauthorized
}
