enum OfferDetailViewState: Equatable {
    case idle
    case loading
    case loaded(SafeOffer)
    case failed(errorKey: String)
}
