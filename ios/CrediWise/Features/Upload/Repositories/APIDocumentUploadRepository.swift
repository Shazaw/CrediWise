import Foundation

protocol HTTPUploadSession: Sendable {
    func upload(
        for request: URLRequest,
        from bodyData: Data,
        delegate: (any URLSessionTaskDelegate)?
    ) async throws -> (Data, URLResponse)
}

extension URLSession: HTTPUploadSession {}

actor APIDocumentUploadRepository: DocumentUploadRepository {
    private let baseURL: URL
    private let dataSession: any HTTPDataSession
    private let uploadSession: any HTTPUploadSession
    private let authInterceptor: AuthInterceptor
    private let decoder = JSONDecoder()

    init(
        baseURL: URL,
        dataSession: any HTTPDataSession = URLSession.shared,
        uploadSession: any HTTPUploadSession = URLSession.shared,
        authInterceptor: AuthInterceptor
    ) {
        self.baseURL = baseURL
        self.dataSession = dataSession
        self.uploadSession = uploadSession
        self.authInterceptor = authInterceptor
    }

    func upload(
        file: SelectedUploadFile,
        pdfPassword: String? = nil,
        onProgress: @escaping @Sendable (Double) async -> Void
    ) async throws -> DocumentUploadReceipt {
        let boundary = "CrediWise-\(UUID().uuidString)"
        let body: Data
        do {
            body = try multipartBody(
                file: file,
                pdfPassword: pdfPassword,
                boundary: boundary
            )
        } catch {
            throw DocumentUploadRepositoryError.validationFailed
        }

        var request = URLRequest(url: baseURL.appendingPathComponent("api/v1/documents"))
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let data = try await executeUpload(request, body: body, onProgress: onProgress)
        let response: DocumentUploadResponse = try decode(data)
        guard let status = DocumentProcessingStatus(rawValue: response.status) else {
            throw DocumentUploadRepositoryError.serviceUnavailable
        }
        return DocumentUploadReceipt(
            documentID: response.documentID.uuidString,
            fileName: file.fileName,
            status: response.duplicate ? .duplicateReused : status
        )
    }

    func status(documentID: String) async throws -> DocumentStatusSnapshot {
        guard let documentUUID = UUID(uuidString: documentID) else {
            throw DocumentUploadRepositoryError.validationFailed
        }
        var request = URLRequest(
            url: baseURL.appendingPathComponent(
                "api/v1/documents/\(documentUUID.uuidString)/status"
            )
        )
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let data = try await executeData(request)
        let response: DocumentStatusResponse = try decode(data)
        guard let status = DocumentProcessingStatus(rawValue: response.status) else {
            throw DocumentUploadRepositoryError.serviceUnavailable
        }
        return DocumentStatusSnapshot(
            documentID: response.documentID.uuidString,
            status: status
        )
    }

    private func multipartBody(
        file: SelectedUploadFile,
        pdfPassword: String?,
        boundary: String
    ) throws -> Data {
        guard let sourceType = file.sourceType else {
            throw DocumentUploadRepositoryError.validationFailed
        }
        let fileData = try Data(contentsOf: file.url)
        var body = Data()
        body.appendFormField(
            name: "source_type",
            value: sourceType.rawValue,
            boundary: boundary
        )
        if let pdfPassword, !pdfPassword.isEmpty {
            body.appendFormField(name: "pdf_password", value: pdfPassword, boundary: boundary)
        }
        body.appendUTF8("--\(boundary)\r\n")
        body.appendUTF8(
            "Content-Disposition: form-data; name=\"file\"; "
                + "filename=\"\(sanitized(file.fileName))\"\r\n"
        )
        body.appendUTF8("Content-Type: \(file.mimeType)\r\n\r\n")
        body.append(fileData)
        body.appendUTF8("\r\n--\(boundary)--\r\n")
        return body
    }

    private func sanitized(_ fileName: String) -> String {
        fileName.replacingOccurrences(of: "\r", with: "_")
            .replacingOccurrences(of: "\n", with: "_")
            .replacingOccurrences(of: "\"", with: "_")
    }

    private func executeUpload(
        _ request: URLRequest,
        body: Data,
        onProgress: @escaping @Sendable (Double) async -> Void
    ) async throws -> Data {
        var authorizedRequest = try await authorized(request)
        var retryCount = 0

        while true {
            await onProgress(0)
            let progressDelegate = UploadProgressDelegate(onProgress: onProgress)
            let data: Data
            let response: URLResponse
            do {
                (data, response) = try await uploadSession.upload(
                    for: authorizedRequest,
                    from: body,
                    delegate: progressDelegate
                )
            } catch is CancellationError {
                throw CancellationError()
            } catch {
                throw DocumentUploadRepositoryError.serviceUnavailable
            }

            guard let httpResponse = response as? HTTPURLResponse else {
                throw DocumentUploadRepositoryError.serviceUnavailable
            }
            if let retry = try await retryRequest(
                authorizedRequest,
                statusCode: httpResponse.statusCode,
                retryCount: retryCount
            ) {
                authorizedRequest = retry
                retryCount += 1
                continue
            }
            guard httpResponse.statusCode == 202 else {
                throw mapError(statusCode: httpResponse.statusCode, data: data)
            }
            await onProgress(1)
            return data
        }
    }

    private func executeData(_ request: URLRequest) async throws -> Data {
        var authorizedRequest = try await authorized(request)
        var retryCount = 0

        while true {
            let data: Data
            let response: URLResponse
            do {
                (data, response) = try await dataSession.response(for: authorizedRequest)
            } catch is CancellationError {
                throw CancellationError()
            } catch {
                throw DocumentUploadRepositoryError.serviceUnavailable
            }

            guard let httpResponse = response as? HTTPURLResponse else {
                throw DocumentUploadRepositoryError.serviceUnavailable
            }
            if let retry = try await retryRequest(
                authorizedRequest,
                statusCode: httpResponse.statusCode,
                retryCount: retryCount
            ) {
                authorizedRequest = retry
                retryCount += 1
                continue
            }
            guard httpResponse.statusCode == 200 else {
                throw mapError(statusCode: httpResponse.statusCode, data: data)
            }
            return data
        }
    }

    private func authorized(_ request: URLRequest) async throws -> URLRequest {
        do {
            return try await authInterceptor.authorize(request)
        } catch {
            throw DocumentUploadRepositoryError.serviceUnavailable
        }
    }

    private func retryRequest(
        _ request: URLRequest,
        statusCode: Int,
        retryCount: Int
    ) async throws -> URLRequest? {
        do {
            return try await authInterceptor.requestForRetry(
                request,
                statusCode: statusCode,
                retryCount: retryCount
            )
        } catch {
            throw DocumentUploadRepositoryError.serviceUnavailable
        }
    }

    private func decode<Response: Decodable>(_ data: Data) throws -> Response {
        do {
            return try decoder.decode(Response.self, from: data)
        } catch {
            throw DocumentUploadRepositoryError.serviceUnavailable
        }
    }

    private func mapError(statusCode: Int, data: Data) -> DocumentUploadRepositoryError {
        let code = try? decoder.decode(DocumentErrorEnvelope.self, from: data).error.code
        switch (statusCode, code) {
        case (415, "UNSUPPORTED_MEDIA_TYPE"):
            return .unsupportedFormat
        case (422, "PDF_PASSWORD_REQUIRED"):
            return .pdfPasswordRequired
        case (422, "INVALID_PDF_PASSWORD"):
            return .invalidPDFPassword
        case (422, _):
            return .validationFailed
        case (429, "RATE_LIMITED"):
            return .rateLimited
        default:
            return .serviceUnavailable
        }
    }
}

private final class UploadProgressDelegate: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    private let onProgress: @Sendable (Double) async -> Void

    init(onProgress: @escaping @Sendable (Double) async -> Void) {
        self.onProgress = onProgress
    }

    func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        didSendBodyData bytesSent: Int64,
        totalBytesSent: Int64,
        totalBytesExpectedToSend: Int64
    ) {
        guard totalBytesExpectedToSend > 0 else {
            return
        }
        let progress = Double(totalBytesSent) / Double(totalBytesExpectedToSend)
        Task { await onProgress(progress) }
    }
}

private struct DocumentUploadResponse: Decodable {
    let documentID: UUID
    let status: String
    let poll: String
    let duplicate: Bool

    enum CodingKeys: String, CodingKey {
        case documentID = "document_id"
        case status
        case poll
        case duplicate
    }
}

private struct DocumentStatusResponse: Decodable {
    let documentID: UUID
    let status: String
    let fileName: String
    let mimeType: String
    let sourceType: String
    let pageCount: Int?
    let uploadedAt: String?

    enum CodingKeys: String, CodingKey {
        case documentID = "document_id"
        case status
        case fileName = "file_name"
        case mimeType = "mime_type"
        case sourceType = "source_type"
        case pageCount = "page_count"
        case uploadedAt = "uploaded_at"
    }
}

private struct DocumentErrorEnvelope: Decodable {
    let error: DocumentAPIError
}

private struct DocumentAPIError: Decodable {
    let code: String
}

private extension Data {
    mutating func appendFormField(name: String, value: String, boundary: String) {
        appendUTF8("--\(boundary)\r\n")
        appendUTF8("Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n")
        appendUTF8("\(value)\r\n")
    }

    mutating func appendUTF8(_ value: String) {
        append(contentsOf: value.utf8)
    }
}
