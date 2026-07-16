struct DocumentUploadReceipt: Equatable, Sendable {
    let documentID: String
    let fileName: String
    let status: DocumentProcessingStatus
}
