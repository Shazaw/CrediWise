struct UnavailableAssessmentDashboardRepository: AssessmentDashboardRepository {
    func create(financingNeedID: String, documentID: String) async throws -> String {
        throw AssessmentDashboardRepositoryError.unavailable
    }

    func dashboard(assessmentID: String) async throws -> AssessmentDashboard {
        throw AssessmentDashboardRepositoryError.unavailable
    }
}
