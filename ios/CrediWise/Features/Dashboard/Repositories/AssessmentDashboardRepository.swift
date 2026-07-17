protocol AssessmentDashboardRepository: Sendable {
    func dashboard(assessmentID: String) async throws -> AssessmentDashboard
}
