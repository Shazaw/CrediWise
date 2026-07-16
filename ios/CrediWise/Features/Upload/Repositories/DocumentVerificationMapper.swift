import Foundation

enum DocumentVerificationMapper {
    static func review(
        status: VerificationStatusResponse,
        transactions: [VerificationTransactionResponse]
    ) -> ExtractionReview {
        ExtractionReview(
            documentID: status.documentID.uuidString,
            fileName: status.fileName,
            accountOwner: nil,
            periodLabel: periodLabel(
                start: status.statementStartDate ?? transactions.first?.transactionDate,
                end: status.statementEndDate ?? transactions.last?.transactionDate
            ),
            transactions: transactions.map(transaction)
        )
    }

    static func correctionRequests(
        submission: ExtractionReview.Submission,
        review: ExtractionReview
    ) -> [VerificationCorrectionRequest] {
        var requests = submission.corrections.flatMap { correction -> [VerificationCorrectionRequest] in
            guard let transaction = review.transactions.first(where: { $0.id == correction.id }),
                  let transactionID = UUID(uuidString: correction.id) else {
                return []
            }
            return requestsForCorrection(
                correction: correction,
                transaction: transaction,
                transactionID: transactionID
            )
        }
        if submission.reportsMissingRows {
            requests.append(correctionRequest(type: "MISSING_ROW"))
        }
        if submission.reportsOwnershipConcern {
            requests.append(correctionRequest(type: "OWNERSHIP_CONCERN"))
        }
        return requests
    }

    static func confidence(_ response: VerificationResponse) -> DataConfidenceReport {
        let band = DataConfidenceReport.Band(rawValue: response.band.lowercased()) ?? .low
        return DataConfidenceReport(
            score: score(response.dataConfidenceScore),
            band: band,
            dimensions: [
                dimension("provenance", "confidence.dimension.provenance", response.provenanceScore),
                dimension("consistency", "confidence.dimension.consistency", response.consistencyScore),
                dimension("metadata", "confidence.dimension.metadata", response.metadataScore),
                dimension("ocr", "confidence.dimension.ocr", response.ocrScore),
                dimension("visual", "confidence.dimension.visual", response.visualScore),
                dimension("completeness", "confidence.dimension.completeness", response.completenessScore),
                dimension("ownership", "confidence.dimension.ownership", response.ownershipScore)
            ],
            reasons: response.reasonCodes.map(reason),
            recommendationKey: "confidence.recommendation.\(band.rawValue)",
            assistanceStatus: assistanceStatus(response.aiSignal),
            modelVersion: response.modelVersionID.uuidString
        )
    }

    private static func requestsForCorrection(
        correction: ExtractionReview.Correction,
        transaction: ExtractionReview.Transaction,
        transactionID: UUID
    ) -> [VerificationCorrectionRequest] {
        textRequests(correction: correction, transaction: transaction, transactionID: transactionID)
            + valueRequests(correction: correction, transaction: transaction, transactionID: transactionID)
            + flagRequests(correction: correction, transaction: transaction, transactionID: transactionID)
    }

    private static func textRequests(
        correction: ExtractionReview.Correction,
        transaction: ExtractionReview.Transaction,
        transactionID: UUID
    ) -> [VerificationCorrectionRequest] {
        var requests: [VerificationCorrectionRequest] = []
        if let value = correction.proposedDate {
            requests.append(
                correctionRequest(
                    transactionID: transactionID,
                    type: "OTHER",
                    note: "TRANSACTION_DATE",
                    raw: .string(transaction.date.raw),
                    normalized: .string(transaction.date.normalized),
                    proposed: .string(value)
                )
            )
        }
        if let value = correction.proposedDescription {
            requests.append(
                correctionRequest(
                    transactionID: transactionID,
                    type: "OTHER",
                    note: "TRANSACTION_DESCRIPTION",
                    raw: .string(transaction.description.raw),
                    normalized: .string(transaction.description.normalized),
                    proposed: .string(value)
                )
            )
        }
        return requests
    }

    private static func valueRequests(
        correction: ExtractionReview.Correction,
        transaction: ExtractionReview.Transaction,
        transactionID: UUID
    ) -> [VerificationCorrectionRequest] {
        var requests: [VerificationCorrectionRequest] = []
        if let value = correction.proposedAmount {
            requests.append(
                correctionRequest(
                    transactionID: transactionID,
                    type: "INCORRECT_AMOUNT",
                    raw: .integer(transaction.amount.raw),
                    normalized: .integer(transaction.amount.normalized),
                    proposed: .integer(value)
                )
            )
        }
        if let value = correction.proposedCategory {
            requests.append(
                correctionRequest(
                    transactionID: transactionID,
                    type: "WRONG_CATEGORY",
                    raw: .string(categoryValue(transaction.category.raw)),
                    normalized: .string(categoryValue(transaction.category.normalized)),
                    proposed: .string(categoryValue(value))
                )
            )
        }
        return requests
    }

    private static func flagRequests(
        correction: ExtractionReview.Correction,
        transaction: ExtractionReview.Transaction,
        transactionID: UUID
    ) -> [VerificationCorrectionRequest] {
        var requests: [VerificationCorrectionRequest] = []
        if let value = correction.proposedInternalTransfer {
            requests.append(
                correctionRequest(
                    transactionID: transactionID,
                    type: "INTERNAL_TRANSFER",
                    raw: .boolean(transaction.internalTransfer.raw),
                    normalized: .boolean(transaction.internalTransfer.normalized),
                    proposed: .boolean(value)
                )
            )
        }
        if let value = correction.proposedDuplicate {
            requests.append(
                correctionRequest(
                    transactionID: transactionID,
                    type: "DUPLICATE",
                    raw: .boolean(transaction.duplicate.raw),
                    normalized: .boolean(transaction.duplicate.normalized),
                    proposed: .boolean(value)
                )
            )
        }
        return requests
    }

    private static func correctionRequest(
        transactionID: UUID? = nil,
        type: String,
        note: String? = nil,
        raw: VerificationCorrectionValue? = nil,
        normalized: VerificationCorrectionValue? = nil,
        proposed: VerificationCorrectionValue? = nil
    ) -> VerificationCorrectionRequest {
        .init(
            transactionID: transactionID,
            correctionType: type,
            note: note,
            rawExtractedValue: raw,
            systemNormalizedValue: normalized,
            userProposedValue: proposed
        )
    }

    private static func transaction(_ response: VerificationTransactionResponse) -> ExtractionReview.Transaction {
        let amount = response.direction == "DEBIT" ? -abs(response.amount) : abs(response.amount)
        let category = mapCategory(response.category)
        return .init(
            id: response.transactionID.uuidString,
            date: .init(raw: response.transactionDate, normalized: displayDate(response.transactionDate)),
            description: .init(
                raw: response.rawDescription,
                normalized: response.normalizedDescription
            ),
            amount: .init(raw: amount, normalized: amount),
            category: .init(raw: .unknown, normalized: category),
            internalTransfer: .init(
                raw: response.isInternalTransfer,
                normalized: response.isInternalTransfer
            ),
            duplicate: .init(raw: response.isDuplicate, normalized: response.isDuplicate),
            extractionConfidence: extractionScore(response.extractionConfidence)
        )
    }

    private static func mapCategory(_ value: String) -> ExtractionReview.Category {
        switch value {
        case "INCOME": return .income
        case "ESSENTIAL_EXPENSE": return .essentialExpense
        case "FINANCIAL_OBLIGATION": return .financialObligation
        case "DISCRETIONARY": return .discretionary
        case "SAVINGS_TRANSFER": return .savingsTransfer
        case "INTERNAL_TRANSFER": return .internalTransfer
        default: return .unknown
        }
    }

    private static func categoryValue(_ category: ExtractionReview.Category) -> String {
        switch category {
        case .income: return "INCOME"
        case .essentialExpense: return "ESSENTIAL_EXPENSE"
        case .financialObligation: return "FINANCIAL_OBLIGATION"
        case .discretionary: return "DISCRETIONARY"
        case .savingsTransfer: return "SAVINGS_TRANSFER"
        case .internalTransfer: return "INTERNAL_TRANSFER"
        case .unknown: return "UNKNOWN"
        }
    }

    private static func periodLabel(start: String?, end: String?) -> String {
        switch (start, end) {
        case let (start?, end?) where start != end: return "\(displayDate(start)) - \(displayDate(end))"
        case let (start?, _): return displayDate(start)
        case let (_, end?): return displayDate(end)
        default: return "-"
        }
    }

    private static func displayDate(_ value: String) -> String {
        let parser = DateFormatter()
        parser.locale = Locale(identifier: "en_US_POSIX")
        parser.dateFormat = "yyyy-MM-dd"
        guard let date = parser.date(from: value) else { return value }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "id_ID")
        formatter.dateStyle = .medium
        return formatter.string(from: date)
    }

    private static func score(_ value: String) -> Int {
        min(max(Int((Double(value) ?? 0).rounded()), 0), 100)
    }

    private static func extractionScore(_ value: String) -> Int {
        let raw = Double(value) ?? 0
        return min(max(Int(((raw <= 1 ? raw * 100 : raw)).rounded()), 0), 100)
    }

    private static func dimension(
        _ id: String,
        _ titleKey: String,
        _ value: String
    ) -> DataConfidenceReport.Dimension {
        .init(id: id, titleKey: titleKey, score: score(value))
    }

    private static func reason(_ response: VerificationReasonResponse) -> DataConfidenceReport.Reason {
        let keys: (String, String)
        if response.code == "PROVENANCE_ORIGINAL_PDF" {
            keys = ("confidence.reason.original_pdf.title", "confidence.reason.original_pdf.detail")
        } else if response.code == "CONSISTENCY_MATCHED" {
            keys = ("confidence.reason.balance.title", "confidence.reason.balance.detail")
        } else if response.code == "OWNERSHIP_MATCH" {
            keys = ("confidence.reason.ownership.title", "confidence.reason.ownership.detail")
        } else {
            keys = ("confidence.reason.verification_signal.title", response.description)
        }
        return .init(
            id: response.code,
            titleKey: keys.0,
            detailKey: keys.1,
            source: response.code.contains("_AI_") ? .localAIAssistance : .deterministic
        )
    }

    private static func assistanceStatus(_ value: String?) -> DataConfidenceReport.AssistanceStatus {
        switch value {
        case "INCLUDED": return .available
        case "UNAVAILABLE": return .unavailable
        default: return .notUsed
        }
    }
}
