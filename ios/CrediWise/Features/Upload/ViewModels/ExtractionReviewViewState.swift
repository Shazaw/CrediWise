enum ExtractionReviewViewState: Equatable {
    struct Ready: Equatable {
        let review: ExtractionReview
        var corrections: [ExtractionReview.Correction]
        var confirmsOwnership: Bool
        var reportsOwnershipConcern: Bool
        var reportsMissingRows: Bool
        var invalidTransactionIDs: Set<String>

        var canConfirm: Bool {
            (confirmsOwnership || reportsOwnershipConcern) && invalidTransactionIDs.isEmpty
        }

        func correction(for transactionID: String) -> ExtractionReview.Correction? {
            corrections.first { $0.id == transactionID }
        }
    }

    case idle
    case loading
    case loaded(Ready)
    case confirming(Ready)
    case confirmed(documentID: String)
    case failed(Ready?, errorKey: String)
}
