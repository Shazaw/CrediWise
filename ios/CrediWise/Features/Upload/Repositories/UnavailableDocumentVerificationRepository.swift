struct UnavailableDocumentVerificationRepository: DocumentVerificationRepository {
    func review(documentID: String) async throws -> ExtractionReview {
        throw DocumentVerificationRepositoryError.unavailable
    }

    func confirm(
        documentID: String,
        submission: ExtractionReview.Submission
    ) async throws {
        throw DocumentVerificationRepositoryError.unavailable
    }

    func dataConfidence(documentID: String) async throws -> DataConfidenceReport {
        throw DocumentVerificationRepositoryError.unavailable
    }
}
