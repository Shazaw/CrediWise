enum DataConfidenceViewState: Equatable {
    case idle
    case loading
    case loaded(DataConfidenceReport)
    case failed(errorKey: String)
}
