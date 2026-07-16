import Foundation

struct SelectedUploadFile: Equatable, Sendable {
    let url: URL
    let fileName: String
    let byteCount: Int64
    let mimeType: String
}
