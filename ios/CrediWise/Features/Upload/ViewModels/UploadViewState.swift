enum UploadViewState: Equatable {
    case idle
    case selected(SelectedUploadFile)
    case passwordRequired(SelectedUploadFile, invalid: Bool)
    case uploading(SelectedUploadFile, progress: Double)
    case processing(DocumentUploadReceipt, status: DocumentProcessingStatus)
    case completed(DocumentUploadReceipt)
    case duplicate(DocumentUploadReceipt)
    case failed(SelectedUploadFile?, errorKey: String)
}
