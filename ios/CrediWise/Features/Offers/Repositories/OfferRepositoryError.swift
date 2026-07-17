enum OfferRepositoryError: Error, Equatable, Sendable {
    case invalidIdentifier
    case invalidParameters
    case notFound
    case notReady
    case rateLimited
    case reassessmentRequired
    case unavailable
}
