struct UnavailableFinancingNeedRepository: FinancingNeedRepository {
    func save(_ need: FinancingNeed) async throws -> FinancingNeedReceipt {
        throw FinancingNeedRepositoryError.unavailable
    }
}
