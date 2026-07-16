protocol DocumentUploadRepository: Sendable {
    func upload(
        file: SelectedUploadFile,
        onProgress: @Sendable (Double) async -> Void
    ) async throws -> DocumentUploadReceipt

    func status(documentID: String) async throws -> DocumentStatusSnapshot
}
