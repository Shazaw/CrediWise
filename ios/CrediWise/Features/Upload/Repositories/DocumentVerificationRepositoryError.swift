enum DocumentVerificationRepositoryError: Error, Equatable {
    case unavailable
    case reviewChanged
    case alreadyConfirmed
}
