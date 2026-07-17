import Combine
import Foundation

@MainActor
final class FinancingNeedViewModel: ObservableObject {
    @Published private(set) var state: FinancingNeedViewState = .editing
    @Published private(set) var amountText = ""
    @Published var purpose: FinancingNeed.Purpose?
    @Published var preferredTenorMonths = 12
    @Published var notes = ""
    @Published private(set) var hasAttemptedSubmission = false

    private let repository: any FinancingNeedRepository

    init(repository: any FinancingNeedRepository) {
        self.repository = repository
    }

    var requestedAmount: Int64? {
        Int64(amountText)
    }

    var formattedAmount: String? {
        guard let requestedAmount else { return nil }
        return IDRFormatter.string(from: requestedAmount)
    }

    var isAmountValid: Bool {
        guard let requestedAmount else { return false }
        return (1...1_000_000_000).contains(requestedAmount)
    }

    var canSubmit: Bool {
        isAmountValid && purpose != nil && state != .submitting
    }

    func setAmountText(_ value: String) {
        amountText = String(value.filter(\.isNumber).prefix(10))
        resetFailure()
    }

    func setPurpose(_ value: FinancingNeed.Purpose) {
        purpose = value
        resetFailure()
    }

    func submit() async -> FinancingNeedReceipt? {
        hasAttemptedSubmission = true
        guard canSubmit, let requestedAmount, let purpose else {
            return nil
        }
        state = .submitting
        do {
            let receipt = try await repository.save(
                FinancingNeed(
                    requestedAmount: requestedAmount,
                    purpose: purpose,
                    preferredTenorMonths: preferredTenorMonths,
                    notes: notes.trimmingCharacters(in: .whitespacesAndNewlines)
                )
            )
            state = .saved(receipt)
            return receipt
        } catch {
            state = .failed(errorKey: "financing_need.error.unavailable")
            return nil
        }
    }

    func retry() {
        guard case .failed = state else { return }
        state = .editing
    }

    private func resetFailure() {
        if case .failed = state {
            state = .editing
        }
    }
}
