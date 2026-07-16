import Combine

@MainActor
final class ExtractionReviewViewModel: ObservableObject {
    @Published private(set) var state: ExtractionReviewViewState = .idle

    private let documentID: String
    private let repository: any DocumentVerificationRepository

    init(documentID: String, repository: any DocumentVerificationRepository) {
        self.documentID = documentID
        self.repository = repository
    }

    func load() async {
        guard case .idle = state else {
            return
        }
        state = .loading
        do {
            let review = try await repository.review(documentID: documentID)
            state = .loaded(
                .init(
                    review: review,
                    corrections: [],
                    confirmsOwnership: false,
                    reportsOwnershipConcern: false,
                    reportsMissingRows: false,
                    invalidTransactionIDs: []
                )
            )
        } catch {
            state = .failed(nil, errorKey: errorKey(for: error))
        }
    }

    func proposeDescription(_ value: String, for transactionID: String) {
        updateCorrection(for: transactionID) { correction, transaction in
            let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
            correction.proposedDescription = trimmed == transaction.description.normalized ? nil : trimmed
        }
    }

    func proposeDate(_ value: String, for transactionID: String) {
        updateCorrection(for: transactionID) { correction, transaction in
            let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
            correction.proposedDate = trimmed == transaction.date.normalized ? nil : trimmed
        }
    }

    func proposeAmount(_ value: Int64, for transactionID: String) {
        updateCorrection(for: transactionID) { correction, transaction in
            correction.proposedAmount = value == transaction.amount.normalized ? nil : value
        }
    }

    func proposeCategory(_ value: ExtractionReview.Category, for transactionID: String) {
        updateCorrection(for: transactionID) { correction, transaction in
            correction.proposedCategory = value == transaction.category.normalized ? nil : value
        }
    }

    func proposeInternalTransfer(_ value: Bool, for transactionID: String) {
        updateCorrection(for: transactionID) { correction, transaction in
            correction.proposedInternalTransfer = value == transaction.internalTransfer.normalized ? nil : value
        }
    }

    func proposeDuplicate(_ value: Bool, for transactionID: String) {
        updateCorrection(for: transactionID) { correction, transaction in
            correction.proposedDuplicate = value == transaction.duplicate.normalized ? nil : value
        }
    }

    func setOwnershipConfirmed(_ value: Bool) {
        updateReady {
            $0.confirmsOwnership = value
            if value {
                $0.reportsOwnershipConcern = false
            }
        }
    }

    func setReportsOwnershipConcern(_ value: Bool) {
        updateReady {
            $0.reportsOwnershipConcern = value
            if value {
                $0.confirmsOwnership = false
            }
        }
    }

    func setReportsMissingRows(_ value: Bool) {
        updateReady { $0.reportsMissingRows = value }
    }

    func setTransactionInputValid(_ isValid: Bool, for transactionID: String) {
        updateReady {
            if isValid {
                $0.invalidTransactionIDs.remove(transactionID)
            } else {
                $0.invalidTransactionIDs.insert(transactionID)
            }
        }
    }

    func confirm() async {
        guard case let .loaded(ready) = state, ready.canConfirm else {
            return
        }
        state = .confirming(ready)
        let submission = ExtractionReview.Submission(
            corrections: ready.corrections,
            confirmsOwnership: ready.confirmsOwnership,
            reportsOwnershipConcern: ready.reportsOwnershipConcern,
            reportsMissingRows: ready.reportsMissingRows
        )
        do {
            try await repository.confirm(documentID: documentID, submission: submission)
            state = .confirmed(documentID: documentID)
        } catch DocumentVerificationRepositoryError.alreadyConfirmed {
            state = .confirmed(documentID: documentID)
        } catch {
            state = .failed(ready, errorKey: errorKey(for: error))
        }
    }

    func retry() async {
        guard case let .failed(ready, errorKey) = state else {
            return
        }
        if errorKey == "review.error.changed" {
            state = .idle
            await load()
            return
        }
        if let ready {
            state = .loaded(ready)
            await confirm()
        } else {
            state = .idle
            await load()
        }
    }

    private func updateReady(_ update: (inout ExtractionReviewViewState.Ready) -> Void) {
        guard case var .loaded(ready) = state else {
            return
        }
        update(&ready)
        state = .loaded(ready)
    }

    private func updateCorrection(
        for transactionID: String,
        update: (inout ExtractionReview.Correction, ExtractionReview.Transaction) -> Void
    ) {
        guard case var .loaded(ready) = state,
              let transaction = ready.review.transactions.first(where: { $0.id == transactionID }) else {
            return
        }
        var correction = ready.correction(for: transactionID) ?? .init(id: transactionID)
        update(&correction, transaction)
        ready.corrections.removeAll { $0.id == transactionID }
        if !correction.isEmpty {
            ready.corrections.append(correction)
        }
        state = .loaded(ready)
    }

    private func errorKey(for error: Error) -> String {
        guard let repositoryError = error as? DocumentVerificationRepositoryError else {
            return "review.error.unavailable"
        }
        switch repositoryError {
        case .unavailable:
            return "review.error.unavailable"
        case .reviewChanged:
            return "review.error.changed"
        case .alreadyConfirmed:
            return "review.error.already_confirmed"
        }
    }
}
