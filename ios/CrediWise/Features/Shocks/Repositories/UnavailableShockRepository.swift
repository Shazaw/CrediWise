struct UnavailableShockRepository: ShockRepository {
    func shocks(assessmentID: String) async throws -> ShockAssessment {
        throw ShockRepositoryError.unavailable
    }

    func simulate(
        assessmentID: String,
        parameters: ShockSimulationParameters
    ) async throws -> ShockAssessment {
        throw ShockRepositoryError.unavailable
    }
}
