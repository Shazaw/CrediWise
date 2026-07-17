import Combine

@MainActor
final class OffersViewModel: ObservableObject {
    @Published private(set) var state: OffersViewState = .idle

    private let assessmentID: String
    private let repository: any OfferRepository

    init(assessmentID: String, repository: any OfferRepository) {
        self.assessmentID = assessmentID
        self.repository = repository
    }

    func load() async {
        guard case .idle = state else { return }
        let previousState = state
        state = .loading
        do {
            state = .loaded(try await repository.offers(assessmentID: assessmentID))
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
