actor MockDocumentVerificationRepository: DocumentVerificationRepository {
    private let extractionReview: ExtractionReview
    private let confidenceReport: DataConfidenceReport
    private let reviewError: DocumentVerificationRepositoryError?
    private let confirmationError: DocumentVerificationRepositoryError?
    private let confidenceError: DocumentVerificationRepositoryError?
    private var submissions: [ExtractionReview.Submission] = []
    private var reviewCalls = 0

    init(
        extractionReview: ExtractionReview = MockDocumentVerificationRepository.makeReview(),
        confidenceReport: DataConfidenceReport = MockDocumentVerificationRepository.makeConfidenceReport(),
        reviewError: DocumentVerificationRepositoryError? = nil,
        confirmationError: DocumentVerificationRepositoryError? = nil,
        confidenceError: DocumentVerificationRepositoryError? = nil
    ) {
        self.extractionReview = extractionReview
        self.confidenceReport = confidenceReport
        self.reviewError = reviewError
        self.confirmationError = confirmationError
        self.confidenceError = confidenceError
    }

    func review(documentID: String) async throws -> ExtractionReview {
        reviewCalls += 1
        if let reviewError {
            throw reviewError
        }
        return extractionReview
    }

    func confirm(
        documentID: String,
        submission: ExtractionReview.Submission
    ) async throws {
        if let confirmationError {
            throw confirmationError
        }
        submissions.append(submission)
    }

    func dataConfidence(documentID: String) async throws -> DataConfidenceReport {
        if let confidenceError {
            throw confidenceError
        }
        return confidenceReport
    }

    func submittedReviews() -> [ExtractionReview.Submission] {
        submissions
    }

    func reviewCallCount() -> Int {
        reviewCalls
    }

    static func makeReview() -> ExtractionReview {
        ExtractionReview(
            documentID: "synthetic-document-id",
            fileName: "synthetic-bca-statement.pdf",
            accountOwner: .init(raw: "SARI WULANDARI", normalized: "Sari Wulandari"),
            periodLabel: "Juni 2026",
            transactions: [
                .init(
                    id: "transaction-1",
                    date: .init(raw: "03/06/26", normalized: "3 Jun 2026"),
                    description: .init(raw: "TRSF QRIS WARUNG SARI", normalized: "QRIS Warung Sari"),
                    amount: .init(raw: 2_450_000, normalized: 2_450_000),
                    category: .init(raw: .unknown, normalized: .income),
                    internalTransfer: .init(raw: false, normalized: false),
                    duplicate: .init(raw: false, normalized: false),
                    extractionConfidence: 98
                ),
                .init(
                    id: "transaction-2",
                    date: .init(raw: "05/06/26", normalized: "5 Jun 2026"),
                    description: .init(raw: "TOKO GROSIR MAKMUR", normalized: "Toko Grosir Makmur"),
                    amount: .init(raw: -875_000, normalized: -875_000),
                    category: .init(raw: .unknown, normalized: .essentialExpense),
                    internalTransfer: .init(raw: false, normalized: false),
                    duplicate: .init(raw: false, normalized: false),
                    extractionConfidence: 91
                )
            ]
        )
    }

    static func makeConfidenceReport() -> DataConfidenceReport {
        DataConfidenceReport(
            score: 92,
            band: .high,
            dimensions: [
                .init(id: "authenticity", titleKey: "confidence.dimension.authenticity", score: 94),
                .init(id: "integrity", titleKey: "confidence.dimension.integrity", score: 96),
                .init(id: "extraction", titleKey: "confidence.dimension.extraction", score: 93),
                .init(id: "consistency", titleKey: "confidence.dimension.consistency", score: 95),
                .init(id: "coverage", titleKey: "confidence.dimension.coverage", score: 84),
                .init(id: "freshness", titleKey: "confidence.dimension.freshness", score: 90),
                .init(id: "ownership", titleKey: "confidence.dimension.ownership", score: 94)
            ],
            reasons: [
                .init(
                    id: "original-pdf",
                    titleKey: "confidence.reason.original_pdf.title",
                    detailKey: "confidence.reason.original_pdf.detail",
                    source: .deterministic
                ),
                .init(
                    id: "balanced-rows",
                    titleKey: "confidence.reason.balance.title",
                    detailKey: "confidence.reason.balance.detail",
                    source: .deterministic
                ),
                .init(
                    id: "ownership-match",
                    titleKey: "confidence.reason.ownership.title",
                    detailKey: "confidence.reason.ownership.detail",
                    source: .deterministic
                )
            ],
            recommendationKey: "confidence.recommendation.high",
            assistanceStatus: .unavailable,
            modelVersion: "trust-v1"
        )
    }
}
