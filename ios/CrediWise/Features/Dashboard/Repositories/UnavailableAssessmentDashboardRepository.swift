struct UnavailableAssessmentDashboardRepository: AssessmentDashboardRepository {
    func dashboard(assessmentID: String) async throws -> AssessmentDashboard {
        throw AssessmentDashboardRepositoryError.unavailable
    }
}
