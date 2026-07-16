enum DocumentUploadRepositoryError: Error, Equatable, Sendable {
    case rejectedSecurity
    case validationFailed
    case unsupportedFormat
    case rateLimited
    case serviceUnavailable
}
