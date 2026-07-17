struct UnavailableOfferRepository: OfferRepository {
    func offers(assessmentID: String) async throws -> [SafeOffer] {
        throw OfferRepositoryError.unavailable
    }

    func offer(assessmentID: String, offerID: String) async throws -> SafeOffer {
        throw OfferRepositoryError.unavailable
    }
}
