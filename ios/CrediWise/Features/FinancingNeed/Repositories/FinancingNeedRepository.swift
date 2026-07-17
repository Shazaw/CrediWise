protocol FinancingNeedRepository: Sendable {
    func save(_ need: FinancingNeed) async throws -> FinancingNeedReceipt
}
