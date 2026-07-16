import Foundation
import XCTest
@testable import CrediWise

final class APIDocumentUploadRepositoryTests: XCTestCase {
    private let baseURL = URL(string: "https://api.crediwise.test")!
    private let documentID = UUID(uuidString: "BFA50DD7-F269-4013-BABF-11FD3EF142FE")!

    func testUploadSendsAuthenticatedMultipartContractAndDecodesReceipt() async throws {
        let uploadSession = StubDocumentUploadSession(
            responses: [
                .init(
                    statusCode: 202,
                    body: """
                    {
                      "document_id": "\(documentID.uuidString)",
                      "status": "EXTRACTING",
                      "poll": "/api/v1/documents/\(documentID.uuidString)/status",
                      "duplicate": false
                    }
                    """
                )
            ]
        )
        let repository = try await makeRepository(uploadSession: uploadSession)
        let file = try makeTemporaryFile(name: "synthetic-statement.csv", contents: "date,amount\n")
        defer { try? FileManager.default.removeItem(at: file.url) }

        let receipt = try await repository.upload(file: file, pdfPassword: nil) { _ in }

        XCTAssertEqual(receipt.documentID, documentID.uuidString)
        XCTAssertEqual(receipt.fileName, file.fileName)
        XCTAssertEqual(receipt.status, .extracting)
        let capturedUpload = await uploadSession.lastUpload()
        let captured = try XCTUnwrap(capturedUpload)
        XCTAssertEqual(captured.request.url?.path, "/api/v1/documents")
        XCTAssertEqual(captured.request.httpMethod, "POST")
        XCTAssertEqual(
            captured.request.value(forHTTPHeaderField: "Authorization"),
            "Bearer access-value"
        )
        let body = try XCTUnwrap(String(data: captured.body, encoding: .utf8))
        XCTAssertTrue(body.contains("name=\"source_type\"\r\n\r\nEXPORTED_CSV"))
        XCTAssertTrue(body.contains("filename=\"synthetic-statement.csv\""))
        XCTAssertTrue(body.contains("date,amount"))
    }

    func testDuplicateUploadMapsToReuseNoticeRegardlessOfExistingStatus() async throws {
        let uploadSession = StubDocumentUploadSession(
            responses: [
                .init(
                    statusCode: 202,
                    body: """
                    {
                      "document_id": "\(documentID.uuidString)",
                      "status": "EXTRACTING",
                      "poll": "/api/v1/documents/\(documentID.uuidString)/status",
                      "duplicate": true
                    }
                    """
                )
            ]
        )
        let repository = try await makeRepository(uploadSession: uploadSession)
        let file = try makeTemporaryFile(name: "synthetic.pdf", contents: "%PDF-1.4")
        defer { try? FileManager.default.removeItem(at: file.url) }

        let receipt = try await repository.upload(file: file, pdfPassword: nil) { _ in }

        XCTAssertEqual(receipt.status, .duplicateReused)
    }

    func testPasswordRetryErrorAndFieldFollowBackendContract() async throws {
        let uploadSession = StubDocumentUploadSession(
            responses: [
                .init(
                    statusCode: 422,
                    body: """
                    {
                      "error": {
                        "code": "PDF_PASSWORD_REQUIRED",
                        "message": "Password required",
                        "details": {},
                        "correlation_id": "test"
                      }
                    }
                    """
                ),
                .init(
                    statusCode: 202,
                    body: """
                    {
                      "document_id": "\(documentID.uuidString)",
                      "status": "UPLOADED",
                      "poll": "/api/v1/documents/\(documentID.uuidString)/status",
                      "duplicate": false
                    }
                    """
                )
            ]
        )
        let repository = try await makeRepository(uploadSession: uploadSession)
        let file = try makeTemporaryFile(name: "locked.pdf", contents: "%PDF-1.4")
        defer { try? FileManager.default.removeItem(at: file.url) }

        do {
            _ = try await repository.upload(file: file, pdfPassword: nil) { _ in }
            XCTFail("Expected password-required error")
        } catch let error as DocumentUploadRepositoryError {
            XCTAssertEqual(error, .pdfPasswordRequired)
        }
        _ = try await repository.upload(file: file, pdfPassword: "one-time-value") { _ in }

        let capturedUpload = await uploadSession.lastUpload()
        let captured = try XCTUnwrap(capturedUpload)
        let body = try XCTUnwrap(String(data: captured.body, encoding: .utf8))
        XCTAssertTrue(body.contains("name=\"pdf_password\"\r\n\r\none-time-value"))
    }

    func testStatusUsesAuthenticatedEndpointAndDecodesBoundedStatus() async throws {
        let dataSession = StubDocumentDataSession(
            responses: [
                .init(
                    statusCode: 200,
                    body: """
                    {
                      "document_id": "\(documentID.uuidString)",
                      "status": "VERIFYING",
                      "file_name": "synthetic.pdf",
                      "mime_type": "application/pdf",
                      "source_type": "ORIGINAL_PDF",
                      "page_count": 2,
                      "uploaded_at": "2026-07-17T10:00:00Z"
                    }
                    """
                )
            ]
        )
        let repository = try await makeRepository(dataSession: dataSession)

        let snapshot = try await repository.status(documentID: documentID.uuidString)

        XCTAssertEqual(snapshot.status, .verifying)
        let capturedRequest = await dataSession.lastRequest()
        let request = try XCTUnwrap(capturedRequest)
        XCTAssertEqual(
            request.url?.path,
            "/api/v1/documents/\(documentID.uuidString)/status"
        )
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-value")
    }

    func testUnauthorizedUploadRefreshesOnceAndRetriesWithNewAccessToken() async throws {
        let uploadSession = StubDocumentUploadSession(
            responses: [
                .init(statusCode: 401, body: errorBody(code: "AUTH_ERROR")),
                .init(
                    statusCode: 202,
                    body: """
                    {
                      "document_id": "\(documentID.uuidString)",
                      "status": "UPLOADED",
                      "poll": "/api/v1/documents/\(documentID.uuidString)/status",
                      "duplicate": false
                    }
                    """
                )
            ]
        )
        let repository = try await makeRepository(
            uploadSession: uploadSession,
            refreshedTokens: SessionTokens(accessToken: "new-access", refreshToken: "new-refresh")
        )
        let file = try makeTemporaryFile(name: "synthetic.pdf", contents: "%PDF-1.4")
        defer { try? FileManager.default.removeItem(at: file.url) }

        _ = try await repository.upload(file: file, pdfPassword: nil) { _ in }

        let uploads = await uploadSession.allUploads()
        XCTAssertEqual(uploads.count, 2)
        XCTAssertEqual(
            uploads.last?.request.value(forHTTPHeaderField: "Authorization"),
            "Bearer new-access"
        )
    }

    private func makeRepository(
        dataSession: StubDocumentDataSession = StubDocumentDataSession(responses: []),
        uploadSession: StubDocumentUploadSession = StubDocumentUploadSession(responses: []),
        refreshedTokens: SessionTokens = SessionTokens(
            accessToken: "new-access",
            refreshToken: "new-refresh"
        )
    ) async throws -> APIDocumentUploadRepository {
        let tokenStore = VolatileTokenStore()
        try await tokenStore.save(
            SessionTokens(accessToken: "access-value", refreshToken: "refresh-value")
        )
        let interceptor = AuthInterceptor(
            tokenStore: tokenStore,
            refreshHandler: { _ in refreshedTokens },
            unauthorizedHandler: {}
        )
        return APIDocumentUploadRepository(
            baseURL: baseURL,
            dataSession: dataSession,
            uploadSession: uploadSession,
            authInterceptor: interceptor
        )
    }

    private func makeTemporaryFile(name: String, contents: String) throws -> SelectedUploadFile {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let url = directory.appendingPathComponent(name)
        let data = Data(contents.utf8)
        try data.write(to: url)
        return SelectedUploadFile(
            url: url,
            fileName: name,
            byteCount: Int64(data.count),
            mimeType: name.hasSuffix(".csv") ? "text/csv" : "application/pdf",
            sourceType: name.hasSuffix(".csv") ? .exportedCSV : .originalPDF
        )
    }

    private func errorBody(code: String) -> String {
        """
        {"error":{"code":"\(code)","message":"Request failed","details":{},"correlation_id":"test"}}
        """
    }
}

private struct StubDocumentResponse: Sendable {
    let statusCode: Int
    let body: String
}

private actor StubDocumentUploadSession: HTTPUploadSession {
    struct CapturedUpload: Sendable {
        let request: URLRequest
        let body: Data
    }

    private var responses: [StubDocumentResponse]
    private var uploads: [CapturedUpload] = []

    init(responses: [StubDocumentResponse]) {
        self.responses = responses
    }

    func upload(
        for request: URLRequest,
        from bodyData: Data,
        delegate: (any URLSessionTaskDelegate)?
    ) async throws -> (Data, URLResponse) {
        uploads.append(CapturedUpload(request: request, body: bodyData))
        let response = responses.removeFirst()
        return (
            Data(response.body.utf8),
            HTTPURLResponse(
                url: request.url!,
                statusCode: response.statusCode,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
        )
    }

    func lastUpload() -> CapturedUpload? {
        uploads.last
    }

    func allUploads() -> [CapturedUpload] {
        uploads
    }
}

private actor StubDocumentDataSession: HTTPDataSession {
    private var responses: [StubDocumentResponse]
    private var requests: [URLRequest] = []

    init(responses: [StubDocumentResponse]) {
        self.responses = responses
    }

    func response(for request: URLRequest) async throws -> (Data, URLResponse) {
        requests.append(request)
        let response = responses.removeFirst()
        return (
            Data(response.body.utf8),
            HTTPURLResponse(
                url: request.url!,
                statusCode: response.statusCode,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
        )
    }

    func lastRequest() -> URLRequest? {
        requests.last
    }
}
