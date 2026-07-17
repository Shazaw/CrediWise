actor MockFinancingNeedRepository: FinancingNeedRepository {
    private let receipt: FinancingNeedReceipt
    private let error: FinancingNeedRepositoryError?
    private var savedNeeds: [FinancingNeed] = []

    init(
        receipt: FinancingNeedReceipt = .init(financingNeedID: "synthetic-financing-need-id"),
        error: FinancingNeedRepositoryError? = nil
    ) {
        self.receipt = receipt
        self.error = error
    }

    func save(_ need: FinancingNeed) async throws -> FinancingNeedReceipt {
        if let error {
            throw error
        }
        savedNeeds.append(need)
        return receipt
    }

    func submissions() -> [FinancingNeed] {
        savedNeeds
    }
}
