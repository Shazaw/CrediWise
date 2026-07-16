struct DocumentStatusSnapshot: Equatable, Sendable {
    let documentID: String
    let status: DocumentProcessingStatus
}
