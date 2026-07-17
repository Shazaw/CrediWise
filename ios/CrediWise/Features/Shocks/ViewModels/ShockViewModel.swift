import Combine

@MainActor
final class ShockViewModel: ObservableObject {
    @Published private(set) var state: ShockViewState = .idle
    @Published var incomeDropPercentage: Double = 20
    @Published var emergencyExpense: Double = 1_000_000
    @Published var proposedInstalment: Double = 0

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
            proposedInstalment = Double(report.proposedInstalment)
            stableState = .loaded(report)
            state = stableState
        } catch is CancellationError {
            guard generation == requestGeneration else { return }
            state = stableState
        } catch let error as ShockRepositoryError {
            guard generation == requestGeneration else { return }
            state = .failed(errorKey: errorKey(error))
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
        } catch let error as ShockRepositoryError {
            guard generation == requestGeneration else { return }
            state = .failed(errorKey: errorKey(error))
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
              emergencyExpense < Double(Int64.max),
              proposedInstalment.isFinite,
              proposedInstalment >= 0,
              proposedInstalment < Double(Int64.max) else {
            return nil
        }

        return ShockSimulationParameters(
            incomeDropPercentage: Int(incomeDropPercentage.rounded()),
            emergencyExpense: Int64(emergencyExpense.rounded()),
            proposedInstalment: Int64(proposedInstalment.rounded())
        )
    }

    private func errorKey(_ error: ShockRepositoryError) -> String {
        switch error {
        case .invalidIdentifier, .notFound: return "shocks.error.not_found"
        case .invalidParameters: return "shocks.error.invalid_parameters"
        case .notReady: return "shocks.error.not_ready"
        case .rateLimited: return "shocks.error.rate_limited"
        case .reassessmentRequired: return "shocks.error.reassessment_required"
        case .unavailable: return "shocks.error.unavailable"
        }
    }
}
