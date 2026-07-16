protocol DocumentUploadRepository: Sendable {
    func upload(
        file: SelectedUploadFile,
        pdfPassword: String?,
        onProgress: @escaping @Sendable (Double) async -> Void
    ) async throws -> DocumentUploadReceipt

    func status(documentID: String) async throws -> DocumentStatusSnapshot
}
