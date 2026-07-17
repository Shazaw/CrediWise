import Combine

@MainActor
final class OfferDetailViewModel: ObservableObject {
    @Published private(set) var state: OfferDetailViewState = .idle

    private let assessmentID: String
    private let offerID: String
    private let repository: any OfferRepository

    init(assessmentID: String, offerID: String, repository: any OfferRepository) {
        self.assessmentID = assessmentID
        self.offerID = offerID
        self.repository = repository
    }

    func load() async {
        guard case .idle = state else { return }
        let previousState = state
        state = .loading
        do {
            state = .loaded(
                try await repository.offer(
                    assessmentID: assessmentID,
                    offerID: offerID
                )
            )
        } catch is CancellationError {
            state = previousState
        } catch {
            state = .failed(errorKey: "offers.error.unavailable")
        }
    }

    func retry() async {
        guard case .failed = state else { return }
        state = .idle
        await load()
    }
}
