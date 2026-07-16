enum DocumentUploadRepositoryError: Error, Equatable, Sendable {
    case rejectedSecurity
    case validationFailed
    case unsupportedFormat
    case pdfPasswordRequired
    case invalidPDFPassword
    case rateLimited
    case serviceUnavailable
}
