enum AppRoute: Hashable {
    case registration
    case signIn
    case financingNeed
    case upload
    case extractionReview(documentID: String)
    case dataConfidence(documentID: String)
    case assessmentDashboard(assessmentID: String)
}
