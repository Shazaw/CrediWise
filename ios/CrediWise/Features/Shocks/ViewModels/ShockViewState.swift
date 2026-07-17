enum ShockViewState: Equatable {
    case idle
    case loading
    case loaded(ShockAssessment)
    case invalid(errorKey: String)
    case failed(errorKey: String)
}
