enum FinancingNeedViewState: Equatable {
    case editing
    case submitting
    case saved(FinancingNeedReceipt)
    case failed(errorKey: String)
}
