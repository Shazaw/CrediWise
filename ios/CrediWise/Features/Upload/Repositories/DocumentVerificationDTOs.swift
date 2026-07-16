import Foundation

struct VerificationStatusResponse: Decodable {
    let documentID: UUID
    let fileName: String
    let statementStartDate: String?
    let statementEndDate: String?

    enum CodingKeys: String, CodingKey {
        case documentID = "document_id"
        case fileName = "file_name"
        case statementStartDate = "statement_start_date"
        case statementEndDate = "statement_end_date"
    }
}

struct VerificationTransactionListResponse: Decodable {
    let items: [VerificationTransactionResponse]
    let nextCursor: UUID?

    enum CodingKeys: String, CodingKey {
        case items
        case nextCursor = "next_cursor"
    }
}

struct VerificationTransactionResponse: Decodable {
    let transactionID: UUID
    let transactionDate: String
    let amount: Int64
    let direction: String
    let rawDescription: String
    let normalizedDescription: String
    let category: String
    let isInternalTransfer: Bool
    let isDuplicate: Bool
    let extractionConfidence: String

    enum CodingKeys: String, CodingKey {
        case transactionID = "transaction_id"
        case transactionDate = "transaction_date"
        case amount
        case direction
        case rawDescription = "raw_description"
        case normalizedDescription = "normalized_description"
        case category
        case isInternalTransfer = "is_internal_transfer"
        case isDuplicate = "is_duplicate"
        case extractionConfidence = "extraction_confidence"
    }
}

struct VerificationReasonResponse: Decodable {
    let code: String
    let description: String
}

struct VerificationResponse: Decodable {
    let dataConfidenceScore: String
    let band: String
    let provenanceScore: String
    let consistencyScore: String
    let metadataScore: String
    let ocrScore: String
    let visualScore: String
    let completenessScore: String
    let ownershipScore: String
    let reasonCodes: [VerificationReasonResponse]
    let recommendation: String?
    let modelVersionID: UUID
    let aiSignal: String?

    enum CodingKeys: String, CodingKey {
        case dataConfidenceScore = "data_confidence_score"
        case band
        case provenanceScore = "provenance_score"
        case consistencyScore = "consistency_score"
        case metadataScore = "metadata_score"
        case ocrScore = "ocr_score"
        case visualScore = "visual_score"
        case completenessScore = "completeness_score"
        case ownershipScore = "ownership_score"
        case reasonCodes = "reason_codes"
        case recommendation
        case modelVersionID = "model_version_id"
        case aiSignal = "ai_signal"
    }
}

enum VerificationCorrectionValue: Encodable {
    case string(String)
    case integer(Int64)
    case boolean(Bool)

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case let .string(value):
            try container.encode(value)
        case let .integer(value):
            try container.encode(value)
        case let .boolean(value):
            try container.encode(value)
        }
    }
}

struct VerificationCorrectionRequest: Encodable {
    let transactionID: UUID?
    let correctionType: String
    let note: String?
    let rawExtractedValue: VerificationCorrectionValue?
    let systemNormalizedValue: VerificationCorrectionValue?
    let userProposedValue: VerificationCorrectionValue?

    enum CodingKeys: String, CodingKey {
        case transactionID = "transaction_id"
        case correctionType = "correction_type"
        case note
        case rawExtractedValue = "raw_extracted_value"
        case systemNormalizedValue = "system_normalized_value"
        case userProposedValue = "user_proposed_value"
    }
}

struct VerificationReviewRequest: Encodable {
    let corrections: [VerificationCorrectionRequest]
}

struct VerificationErrorDetails: Decodable {
    let status: String?
}

struct VerificationAPIError: Decodable {
    let code: String
    let details: VerificationErrorDetails?
}

struct VerificationErrorEnvelope: Decodable {
    let error: VerificationAPIError
}
