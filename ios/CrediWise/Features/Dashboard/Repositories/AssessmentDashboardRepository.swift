protocol AssessmentDashboardRepository: Sendable {
    func create(financingNeedID: String, documentID: String) async throws -> String
    func dashboard(assessmentID: String) async throws -> AssessmentDashboard
}
