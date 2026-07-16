import Combine

@MainActor
final class DataConfidenceViewModel: ObservableObject {
    @Published private(set) var state: DataConfidenceViewState = .idle

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
            state = .loaded(try await repository.dataConfidence(documentID: documentID))
        } catch {
            state = .failed(errorKey: "confidence.error.unavailable")
        }
    }

    func retry() async {
        guard case .failed = state else {
            return
        }
        state = .idle
        await load()
    }
}
