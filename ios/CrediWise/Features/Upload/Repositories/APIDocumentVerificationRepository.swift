import Foundation

actor APIDocumentVerificationRepository: DocumentVerificationRepository {
    private let baseURL: URL
    private let session: any HTTPDataSession
    private let authInterceptor: AuthInterceptor
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()
    private var reviews: [String: ExtractionReview] = [:]

    init(
        baseURL: URL,
        session: any HTTPDataSession = URLSession.shared,
        authInterceptor: AuthInterceptor
    ) {
        self.baseURL = baseURL
        self.session = session
        self.authInterceptor = authInterceptor
    }

    func review(documentID: String) async throws -> ExtractionReview {
        let documentUUID = try validatedID(documentID)
        let status: VerificationStatusResponse = try await get(
            path: "api/v1/documents/\(documentUUID.uuidString)/status"
        )
        var transactions: [VerificationTransactionResponse] = []
        var cursor: UUID?
        repeat {
            let page: VerificationTransactionListResponse = try await get(
                path: "api/v1/documents/\(documentUUID.uuidString)/transactions",
                queryItems: transactionQueryItems(cursor: cursor)
            )
            transactions.append(contentsOf: page.items)
            cursor = page.nextCursor
        } while cursor != nil

        let review = DocumentVerificationMapper.review(status: status, transactions: transactions)
        reviews[documentID] = review
        return review
    }

    func confirm(
        documentID: String,
        submission: ExtractionReview.Submission
    ) async throws {
        let documentUUID = try validatedID(documentID)
        guard let review = reviews[documentID] else {
            throw DocumentVerificationRepositoryError.reviewChanged
        }
        let request = VerificationReviewRequest(
            corrections: DocumentVerificationMapper.correctionRequests(
                submission: submission,
                review: review
            )
        )
        do {
            try await post(
                path: "api/v1/documents/\(documentUUID.uuidString)/review",
                body: request
            )
        } catch DocumentVerificationRepositoryError.alreadyConfirmed {
            throw DocumentVerificationRepositoryError.reviewChanged
        }
        try await postWithoutBody(
            path: "api/v1/documents/\(documentUUID.uuidString)/confirm"
        )
        reviews[documentID] = nil
    }

    func dataConfidence(documentID: String) async throws -> DataConfidenceReport {
        let documentUUID = try validatedID(documentID)
        let response: VerificationResponse = try await get(
            path: "api/v1/documents/\(documentUUID.uuidString)/verification"
        )
        return DocumentVerificationMapper.confidence(response)
    }

    private func get<Response: Decodable>(
        path: String,
        queryItems: [URLQueryItem] = []
    ) async throws -> Response {
        var components = URLComponents(
            url: baseURL.appendingPathComponent(path),
            resolvingAgainstBaseURL: false
        )
        components?.queryItems = queryItems.isEmpty ? nil : queryItems
        guard let url = components?.url else {
            throw DocumentVerificationRepositoryError.unavailable
        }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        let data = try await execute(request, expectedStatus: 200)
        do {
            return try decoder.decode(Response.self, from: data)
        } catch {
            throw DocumentVerificationRepositoryError.unavailable
        }
    }

    private func post<Body: Encodable>(path: String, body: Body) async throws {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = "POST"
        request.httpBody = try encoder.encode(body)
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        _ = try await execute(request, expectedStatus: 200)
    }

    private func postWithoutBody(path: String) async throws {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        _ = try await execute(request, expectedStatus: 200)
    }

    private func execute(_ request: URLRequest, expectedStatus: Int) async throws -> Data {
        var authorizedRequest = try await authorized(request)
        var retryCount = 0
        while true {
            let data: Data
            let response: URLResponse
            do {
                (data, response) = try await session.response(for: authorizedRequest)
            } catch is CancellationError {
                throw CancellationError()
            } catch {
                throw DocumentVerificationRepositoryError.unavailable
            }
            guard let httpResponse = response as? HTTPURLResponse else {
                throw DocumentVerificationRepositoryError.unavailable
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
            guard httpResponse.statusCode == expectedStatus else {
                throw mapError(statusCode: httpResponse.statusCode, data: data)
            }
            return data
        }
    }

    private func authorized(_ request: URLRequest) async throws -> URLRequest {
        do {
            return try await authInterceptor.authorize(request)
        } catch {
            throw DocumentVerificationRepositoryError.unavailable
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
            throw DocumentVerificationRepositoryError.unavailable
        }
    }

    private func mapError(statusCode: Int, data: Data) -> DocumentVerificationRepositoryError {
        let envelope = try? decoder.decode(VerificationErrorEnvelope.self, from: data)
        if statusCode == 422, envelope?.error.details?.status != "REVIEW_PENDING" {
            return .alreadyConfirmed
        }
        if statusCode == 409 {
            return .reviewChanged
        }
        return .unavailable
    }

    private func validatedID(_ documentID: String) throws -> UUID {
        guard let documentUUID = UUID(uuidString: documentID) else {
            throw DocumentVerificationRepositoryError.unavailable
        }
        return documentUUID
    }

    private func transactionQueryItems(cursor: UUID?) -> [URLQueryItem] {
        var items = [URLQueryItem(name: "limit", value: "500")]
        if let cursor {
            items.append(URLQueryItem(name: "cursor", value: cursor.uuidString))
        }
        return items
    }
}
