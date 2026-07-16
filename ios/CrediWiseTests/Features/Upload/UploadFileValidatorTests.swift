import Foundation
import UniformTypeIdentifiers
import XCTest
@testable import CrediWise

final class UploadFileValidatorTests: XCTestCase {
    private let testURL = URL(fileURLWithPath: "/tmp/synthetic-statement")

    func testAcceptsSupportedTypesAtMaximumSize() throws {
        let validator = UploadFileValidator()
        let cases: [(String, UTType, String)] = [
            ("statement.pdf", .pdf, "application/pdf"),
            ("transactions.csv", .commaSeparatedText, "text/csv"),
            ("wallet.png", .png, "image/png"),
            ("wallet.jpeg", .jpeg, "image/jpeg")
        ]

        for (fileName, contentType, expectedMimeType) in cases {
            let file = try validator.validate(
                fileName: fileName,
                byteCount: UploadFileValidator.defaultMaximumByteCount,
                contentType: contentType,
                url: testURL
            )

            XCTAssertEqual(file.mimeType, expectedMimeType)
        }
    }

    func testRejectsZeroByteFile() {
        XCTAssertThrowsError(
            try UploadFileValidator().validate(
                fileName: "statement.pdf",
                byteCount: 0,
                contentType: .pdf,
                url: testURL
            )
        ) { error in
            XCTAssertEqual(error as? UploadFileValidationError, .emptyFile)
        }
    }

    func testRejectsFileOverMaximumSize() {
        XCTAssertThrowsError(
            try UploadFileValidator().validate(
                fileName: "statement.pdf",
                byteCount: UploadFileValidator.defaultMaximumByteCount + 1,
                contentType: .pdf,
                url: testURL
            )
        ) { error in
            XCTAssertEqual(error as? UploadFileValidationError, .tooLarge)
        }
    }

    func testRejectsUnsupportedExtension() {
        XCTAssertThrowsError(
            try UploadFileValidator().validate(
                fileName: "statement.zip",
                byteCount: 100,
                contentType: .zip,
                url: testURL
            )
        ) { error in
            XCTAssertEqual(error as? UploadFileValidationError, .unsupportedType)
        }
    }

    func testRejectsMismatchedDeclaredType() {
        XCTAssertThrowsError(
            try UploadFileValidator().validate(
                fileName: "statement.pdf",
                byteCount: 100,
                contentType: .png,
                url: testURL
            )
        ) { error in
            XCTAssertEqual(error as? UploadFileValidationError, .unsupportedType)
        }
    }

    func testReadsSyntheticFileMetadataFromURL() throws {
        let fileURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("crediwise-upload-validator-\(UUID().uuidString).pdf")
        try Data("%PDF-1.4 synthetic fixture".utf8).write(to: fileURL)
        defer { try? FileManager.default.removeItem(at: fileURL) }

        let file = try UploadFileValidator().validate(url: fileURL)

        XCTAssertEqual(file.fileName, fileURL.lastPathComponent)
        XCTAssertEqual(file.mimeType, "application/pdf")
        XCTAssertEqual(file.byteCount, 26)
    }
}
