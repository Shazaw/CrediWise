enum AssessmentDashboardViewState: Equatable {
    case idle
    case loading
    case loaded(AssessmentDashboard)
    case failed(errorKey: String)
}
