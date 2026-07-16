actor MockDocumentUploadRepository: DocumentUploadRepository {
    private let acceptedStatus: DocumentProcessingStatus
    private let uploadError: DocumentUploadRepositoryError?
    private var pendingStatuses: [DocumentProcessingStatus]
    private var latestStatus: DocumentProcessingStatus
    private var uploadCalls = 0

    init(
        acceptedStatus: DocumentProcessingStatus = .uploaded,
        statuses: [DocumentProcessingStatus] = [.securityCheck, .extracting, .complete],
        uploadError: DocumentUploadRepositoryError? = nil
    ) {
        self.acceptedStatus = acceptedStatus
        self.pendingStatuses = statuses
        self.uploadError = uploadError
        latestStatus = acceptedStatus
    }

    func upload(
        file: SelectedUploadFile,
        pdfPassword: String? = nil,
        onProgress: @escaping @Sendable (Double) async -> Void
    ) async throws -> DocumentUploadReceipt {
        uploadCalls += 1
        if let uploadError {
            throw uploadError
        }

        for progress in [0.15, 0.55, 1.0] {
            await onProgress(progress)
        }

        latestStatus = acceptedStatus
        return DocumentUploadReceipt(
            documentID: "synthetic-document-id",
            fileName: file.fileName,
            status: acceptedStatus
        )
    }

    func status(documentID: String) async throws -> DocumentStatusSnapshot {
        if !pendingStatuses.isEmpty {
            latestStatus = pendingStatuses.removeFirst()
        }
        return DocumentStatusSnapshot(documentID: documentID, status: latestStatus)
    }

    func uploadCallCount() -> Int {
        uploadCalls
    }
}
