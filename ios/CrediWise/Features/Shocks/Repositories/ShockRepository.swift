protocol ShockRepository: Sendable {
    func shocks(assessmentID: String) async throws -> ShockAssessment

    func simulate(
        assessmentID: String,
        parameters: ShockSimulationParameters
    ) async throws -> ShockAssessment
}
