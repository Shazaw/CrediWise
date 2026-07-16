enum AppRoute: Hashable {
    case registration
    case signIn
    case upload
    case extractionReview(documentID: String)
    case dataConfidence(documentID: String)
}
