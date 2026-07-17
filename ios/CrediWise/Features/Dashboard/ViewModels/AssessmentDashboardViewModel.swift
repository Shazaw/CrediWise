import Combine

@MainActor
final class AssessmentDashboardViewModel: ObservableObject {
    @Published private(set) var state: AssessmentDashboardViewState = .idle

    private let assessmentID: String
    private let repository: any AssessmentDashboardRepository

    init(assessmentID: String, repository: any AssessmentDashboardRepository) {
        self.assessmentID = assessmentID
        self.repository = repository
    }

    func load() async {
        guard case .idle = state else { return }
        state = .loading
        do {
            state = .loaded(try await repository.dashboard(assessmentID: assessmentID))
        } catch {
            state = .failed(errorKey: "dashboard.error.unavailable")
        }
    }

    func retry() async {
        guard case .failed = state else { return }
        state = .idle
        await load()
    }
}
