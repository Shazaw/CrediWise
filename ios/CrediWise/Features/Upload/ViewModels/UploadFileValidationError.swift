enum UploadFileValidationError: Error, Equatable, Sendable {
    case emptyFile
    case tooLarge
    case unsupportedType
    case unreadable
}
