import Foundation
import UniformTypeIdentifiers

struct UploadFileValidator: Sendable {
    static let defaultMaximumByteCount: Int64 = 15 * 1_024 * 1_024

    let maximumByteCount: Int64

    init(maximumByteCount: Int64 = Self.defaultMaximumByteCount) {
        self.maximumByteCount = maximumByteCount
    }

    func validate(url: URL) throws -> SelectedUploadFile {
        let hasSecurityScope = url.startAccessingSecurityScopedResource()
        defer {
            if hasSecurityScope {
                url.stopAccessingSecurityScopedResource()
            }
        }

        do {
            let values = try url.resourceValues(forKeys: [.contentTypeKey, .fileSizeKey, .nameKey])
            guard let byteCount = values.fileSize else {
                throw UploadFileValidationError.unreadable
            }
            return try validate(
                fileName: values.name ?? url.lastPathComponent,
                byteCount: Int64(byteCount),
                contentType: values.contentType,
                url: url
            )
        } catch let error as UploadFileValidationError {
            throw error
        } catch {
            throw UploadFileValidationError.unreadable
        }
    }

    func validate(
        fileName: String,
        byteCount: Int64,
        contentType: UTType?,
        url: URL
    ) throws -> SelectedUploadFile {
        guard byteCount > 0 else {
            throw UploadFileValidationError.emptyFile
        }
        guard byteCount <= maximumByteCount else {
            throw UploadFileValidationError.tooLarge
        }
        guard let mimeType = supportedMimeType(
            fileExtension: (fileName as NSString).pathExtension.lowercased(),
            contentType: contentType
        ) else {
            throw UploadFileValidationError.unsupportedType
        }

        return SelectedUploadFile(
            url: url,
            fileName: fileName,
            byteCount: byteCount,
            mimeType: mimeType,
            sourceType: sourceType(for: mimeType)
        )
    }

    private func supportedMimeType(fileExtension: String, contentType: UTType?) -> String? {
        switch fileExtension {
        case "pdf" where matches(contentType, expected: .pdf):
            return "application/pdf"
        case "csv" where matches(contentType, expected: .commaSeparatedText):
            return "text/csv"
        case "png" where matches(contentType, expected: .png):
            return "image/png"
        case "jpg", "jpeg" where matches(contentType, expected: .jpeg):
            return "image/jpeg"
        default:
            return nil
        }
    }

    private func matches(_ contentType: UTType?, expected: UTType) -> Bool {
        guard let contentType, contentType != .data else {
            return true
        }
        return contentType.conforms(to: expected)
    }

    private func sourceType(for mimeType: String) -> DocumentSourceType? {
        switch mimeType {
        case "application/pdf":
            return .originalPDF
        case "text/csv":
            return .exportedCSV
        default:
            return nil
        }
    }
}
