import Foundation

struct ExtractionReview: Equatable, Sendable {
    struct ExtractedField<Value: Equatable & Sendable>: Equatable, Sendable {
        let raw: Value
        let normalized: Value
    }

    enum Category: String, CaseIterable, Equatable, Sendable {
        case income
        case essentialExpense
        case financialObligation
        case discretionary
        case savingsTransfer
        case internalTransfer
        case unknown
    }

    struct Transaction: Equatable, Identifiable, Sendable {
        let id: String
        let date: ExtractedField<String>
        let description: ExtractedField<String>
        let amount: ExtractedField<Int64>
        let category: ExtractedField<Category>
        let internalTransfer: ExtractedField<Bool>
        let duplicate: ExtractedField<Bool>
        let extractionConfidence: Int
    }

    struct Correction: Equatable, Identifiable, Sendable {
        let id: String
        var proposedDate: String?
        var proposedDescription: String?
        var proposedAmount: Int64?
        var proposedCategory: Category?
        var proposedInternalTransfer: Bool?
        var proposedDuplicate: Bool?

        var isEmpty: Bool {
            proposedDate == nil &&
                proposedDescription == nil &&
                proposedAmount == nil &&
                proposedCategory == nil &&
                proposedInternalTransfer == nil &&
                proposedDuplicate == nil
        }
    }

    struct Submission: Equatable, Sendable {
        let corrections: [Correction]
        let confirmsOwnership: Bool
        let reportsOwnershipConcern: Bool
        let reportsMissingRows: Bool
    }

    let documentID: String
    let fileName: String
    let accountOwner: ExtractedField<String>
    let periodLabel: String
    let transactions: [Transaction]
}
