import Foundation

struct SelectedUploadFile: Equatable, Sendable {
    let url: URL
    let fileName: String
    let byteCount: Int64
    let mimeType: String
    let sourceType: DocumentSourceType?

    var requiresImageSourceSelection: Bool {
        mimeType.hasPrefix("image/") && sourceType == nil
    }

    func with(sourceType: DocumentSourceType) -> SelectedUploadFile {
        SelectedUploadFile(
            url: url,
            fileName: fileName,
            byteCount: byteCount,
            mimeType: mimeType,
            sourceType: sourceType
        )
    }
}
