import Foundation

actor APIOfferRepository: OfferRepository {
    private let baseURL: URL
    private let session: any HTTPDataSession
    private let authInterceptor: AuthInterceptor
    private let decoder = JSONDecoder()

    init(
        baseURL: URL,
        session: any HTTPDataSession = URLSession.shared,
        authInterceptor: AuthInterceptor
    ) {
        self.baseURL = baseURL
        self.session = session
        self.authInterceptor = authInterceptor
    }

    func offers(assessmentID: String) async throws -> [SafeOffer] {
        let identifier = try validated(assessmentID)
        let path = "api/v1/assessments/\(identifier.uuidString)/offers"
        let existing: OffersListResponseDTO = try await request(
            path: path,
            method: "GET",
            expectedStatus: 200
        )
        guard existing.assessmentID == identifier else {
            throw OfferRepositoryError.unavailable
        }
        guard existing.offers.isEmpty else {
            return try OfferMapper.map(existing)
        }
        let seeded: OffersListResponseDTO = try await request(
            path: path,
            method: "POST",
            expectedStatus: 201
        )
        guard seeded.assessmentID == identifier else {
            throw OfferRepositoryError.unavailable
        }
        return try OfferMapper.map(seeded)
    }

    func offer(assessmentID: String, offerID: String) async throws -> SafeOffer {
        let assessmentIdentifier = try validated(assessmentID)
        let offerIdentifier = try validated(offerID)
        let response: OfferResponseDTO = try await request(
            path: "api/v1/offers/\(offerIdentifier.uuidString)/safety",
            method: "GET",
            expectedStatus: 200
        )
        return try OfferMapper.map(response, assessmentID: assessmentIdentifier)
    }

    private func validated(_ identifier: String) throws -> UUID {
        guard let value = UUID(uuidString: identifier) else {
            throw OfferRepositoryError.invalidIdentifier
        }
        return value
    }

    private func request<Response: Decodable>(
        path: String,
        method: String,
        expectedStatus: Int
    ) async throws -> Response {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        let data = try await execute(request, expectedStatus: expectedStatus)
        do {
            return try decoder.decode(Response.self, from: data)
        } catch {
            throw OfferRepositoryError.unavailable
        }
    }

    private func execute(_ request: URLRequest, expectedStatus: Int) async throws -> Data {
        var authorizedRequest: URLRequest
        do {
            authorizedRequest = try await authInterceptor.authorize(request)
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            throw OfferRepositoryError.unavailable
        }
        var retryCount = 0
        while true {
            let data: Data
            let response: URLResponse
            do {
                (data, response) = try await session.response(for: authorizedRequest)
            } catch is CancellationError {
                throw CancellationError()
            } catch {
                throw OfferRepositoryError.unavailable
            }
            guard let httpResponse = response as? HTTPURLResponse else {
                throw OfferRepositoryError.unavailable
            }
            do {
                if let retry = try await authInterceptor.requestForRetry(
                    authorizedRequest,
                    statusCode: httpResponse.statusCode,
                    retryCount: retryCount
                ) {
                    authorizedRequest = retry
                    retryCount += 1
                    continue
                }
            } catch is CancellationError {
                throw CancellationError()
            } catch {
                throw OfferRepositoryError.unavailable
            }
            guard httpResponse.statusCode == expectedStatus else {
                throw mapError(statusCode: httpResponse.statusCode, data: data)
            }
            return data
        }
    }

    private func mapError(statusCode: Int, data: Data) -> OfferRepositoryError {
        let detail = (try? decoder.decode(OfferAPIErrorEnvelopeDTO.self, from: data))?.error
        let code = detail?.code
        let message = detail?.message.lowercased() ?? ""
        let status = detail?.details.status?.uppercased()
        switch statusCode {
        case 409 where code == "REASSESSMENT_REQUIRED": return .reassessmentRequired
        case 404 where code?.contains("NOT_READY") == true
            || message.contains("not ready")
            || message.contains("available yet"):
            return .notReady
        case 404: return .notFound
        case 422 where status != nil && status != "COMPLETE": return .notReady
        case 422 where message.contains("assessment") && message.contains("complete"):
            return .notReady
        case 422: return .invalidParameters
        case 429: return .rateLimited
        default: return .unavailable
        }
    }
}

private struct OfferAPIErrorEnvelopeDTO: Decodable {
    struct Detail: Decodable {
        let code: String
        let message: String
        let details: OfferAPIErrorDetailsDTO
    }
    let error: Detail
}

private struct OfferAPIErrorDetailsDTO: Decodable {
    let status: String?
}
