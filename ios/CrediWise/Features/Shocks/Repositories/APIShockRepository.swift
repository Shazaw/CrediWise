import Foundation

actor APIShockRepository: ShockRepository {
    private let baseURL: URL
    private let session: any HTTPDataSession
    private let authInterceptor: AuthInterceptor
    private let encoder = JSONEncoder()
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

    func shocks(assessmentID: String) async throws -> ShockAssessment {
        let identifier = try validated(assessmentID)
        let response: ShockResultResponseDTO = try await request(
            path: "api/v1/assessments/\(identifier.uuidString)/shocks",
            method: "GET",
            expectedStatus: 200
        )
        guard response.assessmentID == identifier else {
            throw ShockRepositoryError.unavailable
        }
        try validateComplete(response)
        return try ShockMapper.map(response)
    }

    func simulate(
        assessmentID: String,
        parameters: ShockSimulationParameters
    ) async throws -> ShockAssessment {
        guard (0...100).contains(parameters.incomeDropPercentage),
              parameters.emergencyExpense >= 0,
              parameters.proposedInstalment >= 0 else {
            throw ShockRepositoryError.invalidParameters
        }
        let identifier = try validated(assessmentID)
        let body = try encoder.encode(
            SimulateShockRequestDTO(
                incomeDropPercentage: parameters.incomeDropPercentage,
                emergencyExpense: parameters.emergencyExpense,
                proposedInstalment: parameters.proposedInstalment
            )
        )
        let response: ShockResultResponseDTO = try await request(
            path: "api/v1/assessments/\(identifier.uuidString)/simulate",
            method: "POST",
            expectedStatus: 200,
            body: body
        )
        guard response.assessmentID == identifier else {
            throw ShockRepositoryError.unavailable
        }
        try validateComplete(response)
        return try ShockMapper.map(response, submittedParameters: parameters)
    }

    private func validated(_ identifier: String) throws -> UUID {
        guard let value = UUID(uuidString: identifier) else {
            throw ShockRepositoryError.invalidIdentifier
        }
        return value
    }

    private func validateComplete(_ response: ShockResultResponseDTO) throws {
        guard response.resilienceScore != nil,
              response.band != nil,
              !response.scenarios.isEmpty else {
            throw ShockRepositoryError.notReady
        }
    }

    private func request<Response: Decodable>(
        path: String,
        method: String,
        expectedStatus: Int,
        body: Data? = nil
    ) async throws -> Response {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = method
        request.httpBody = body
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if body != nil {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        let data = try await execute(request, expectedStatus: expectedStatus)
        do {
            return try decoder.decode(Response.self, from: data)
        } catch {
            throw ShockRepositoryError.unavailable
        }
    }

    private func execute(_ request: URLRequest, expectedStatus: Int) async throws -> Data {
        var authorizedRequest: URLRequest
        do {
            authorizedRequest = try await authInterceptor.authorize(request)
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            throw ShockRepositoryError.unavailable
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
                throw ShockRepositoryError.unavailable
            }
            guard let httpResponse = response as? HTTPURLResponse else {
                throw ShockRepositoryError.unavailable
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
                throw ShockRepositoryError.unavailable
            }
            guard httpResponse.statusCode == expectedStatus else {
                throw mapError(statusCode: httpResponse.statusCode, data: data)
            }
            return data
        }
    }

    private func mapError(statusCode: Int, data: Data) -> ShockRepositoryError {
        let detail = (try? decoder.decode(APIErrorEnvelopeDTO.self, from: data))?.error
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

private struct APIErrorEnvelopeDTO: Decodable {
    struct Detail: Decodable {
        let code: String
        let message: String
        let details: ShockAPIErrorDetailsDTO
    }
    let error: Detail
}

private struct ShockAPIErrorDetailsDTO: Decodable {
    let status: String?
}
