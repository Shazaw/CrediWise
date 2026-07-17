import Combine

@MainActor
final class ShockViewModel: ObservableObject {
    @Published private(set) var state: ShockViewState = .idle
    @Published var incomeDropPercentage: Double = 20
    @Published var emergencyExpense: Double = 1_000_000

    private let assessmentID: String
    private let repository: any ShockRepository
    private var requestGeneration = 0
    private var stableState: ShockViewState = .idle

    init(assessmentID: String, repository: any ShockRepository) {
        self.assessmentID = assessmentID
        self.repository = repository
    }

    func load() async {
        guard case .idle = state else { return }
        requestGeneration += 1
        let generation = requestGeneration
        state = .loading
        do {
            let report = try await repository.shocks(assessmentID: assessmentID)
            try Task.checkCancellation()
            guard generation == requestGeneration else { return }
            stableState = .loaded(report)
            state = stableState
        } catch is CancellationError {
            guard generation == requestGeneration else { return }
            state = stableState
        } catch {
            guard generation == requestGeneration else { return }
            state = .failed(errorKey: "shocks.error.unavailable")
        }
    }

    func retry() async {
        guard case .failed = state else { return }
        state = .idle
        await load()
    }

    func simulate() async {
        guard let parameters = simulationParameters else {
            state = .invalid(errorKey: "shocks.error.invalid_parameters")
            return
        }

        requestGeneration += 1
        let generation = requestGeneration
        state = .loading
        do {
            let report = try await repository.simulate(
                assessmentID: assessmentID,
                parameters: parameters
            )
            try Task.checkCancellation()
            guard generation == requestGeneration else { return }
            stableState = .loaded(report)
            state = stableState
        } catch is CancellationError {
            guard generation == requestGeneration else { return }
            state = stableState
        } catch {
            guard generation == requestGeneration else { return }
            state = .failed(errorKey: "shocks.error.unavailable")
        }
    }

    private var simulationParameters: ShockSimulationParameters? {
        guard incomeDropPercentage.isFinite,
              (0...100).contains(incomeDropPercentage),
              emergencyExpense.isFinite,
              emergencyExpense >= 0,
              emergencyExpense < Double(Int64.max) else {
            return nil
        }

        return ShockSimulationParameters(
            incomeDropPercentage: Int(incomeDropPercentage.rounded()),
            emergencyExpense: Int64(emergencyExpense.rounded())
        )
    }
}
