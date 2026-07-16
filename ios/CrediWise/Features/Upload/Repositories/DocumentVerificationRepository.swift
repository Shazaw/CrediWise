protocol DocumentVerificationRepository: Sendable {
    func review(documentID: String) async throws -> ExtractionReview

    func confirm(
        documentID: String,
        submission: ExtractionReview.Submission
    ) async throws

    func dataConfidence(documentID: String) async throws -> DataConfidenceReport
}
