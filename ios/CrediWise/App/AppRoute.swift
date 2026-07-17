enum AppRoute: Hashable {
    case registration
    case signIn
    case financingNeed
    case upload
    case extractionReview(documentID: String)
    case dataConfidence(documentID: String)
    case assessmentDashboard(assessmentID: String)
    case shockSimulation(assessmentID: String)
    case offers(assessmentID: String)
    case offerDetail(assessmentID: String, offerID: String)
}
