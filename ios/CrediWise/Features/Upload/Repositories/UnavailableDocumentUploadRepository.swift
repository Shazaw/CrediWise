struct UnavailableDocumentUploadRepository: DocumentUploadRepository {
    func upload(
        file: SelectedUploadFile,
        pdfPassword: String? = nil,
        onProgress: @escaping @Sendable (Double) async -> Void
    ) async throws -> DocumentUploadReceipt {
        throw DocumentUploadRepositoryError.serviceUnavailable
    }

    func status(documentID: String) async throws -> DocumentStatusSnapshot {
        throw DocumentUploadRepositoryError.serviceUnavailable
    }
}
