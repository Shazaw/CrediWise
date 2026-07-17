protocol OfferRepository: Sendable {
    func offers(assessmentID: String) async throws -> [SafeOffer]
    func offer(assessmentID: String, offerID: String) async throws -> SafeOffer
}
