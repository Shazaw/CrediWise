import Foundation

actor APIAssessmentDashboardRepository: AssessmentDashboardRepository {
    private let baseURL: URL
    private let session: any HTTPDataSession
    private let authInterceptor: AuthInterceptor
    private let verificationRepository: any DocumentVerificationRepository
    private let pollingPolicy: DocumentUploadPollingPolicy
    private let sleep: @Sendable (UInt64) async throws -> Void
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    init(
        baseURL: URL,
        session: any HTTPDataSession = URLSession.shared,
        authInterceptor: AuthInterceptor,
        verificationRepository: any DocumentVerificationRepository,
        pollingPolicy: DocumentUploadPollingPolicy = DocumentUploadPollingPolicy(),
        sleep: @escaping @Sendable (UInt64) async throws -> Void = { seconds in
            try await Task.sleep(nanoseconds: seconds * 1_000_000_000)
        }
    ) {
        self.baseURL = baseURL
        self.session = session
        self.authInterceptor = authInterceptor
        self.verificationRepository = verificationRepository
        self.pollingPolicy = pollingPolicy
        self.sleep = sleep
    }

    func create(financingNeedID: String, documentID: String) async throws -> String {
        guard let financingNeedUUID = UUID(uuidString: financingNeedID),
              let documentUUID = UUID(uuidString: documentID) else {
            throw AssessmentDashboardRepositoryError.unavailable
        }
        var request = URLRequest(url: baseURL.appendingPathComponent("api/v1/assessments"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        do {
            request.httpBody = try encoder.encode(
                AssessmentCreateRequest(
                    financingNeedID: financingNeedUUID,
                    sourceDocumentIDs: [documentUUID]
                )
            )
            let data = try await execute(request, expectedStatus: 202)
            return try decoder.decode(AssessmentCreateResponse.self, from: data)
                .assessmentID.uuidString
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            throw AssessmentDashboardRepositoryError.unavailable
        }
    }

    func dashboard(assessmentID: String) async throws -> AssessmentDashboard {
        guard let assessmentUUID = UUID(uuidString: assessmentID) else {
            throw AssessmentDashboardRepositoryError.unavailable
        }
        let summary = try await completedSummary(assessmentID: assessmentUUID)
        async let twin: AssessmentTwinResponse = get(
            path: "api/v1/assessments/\(assessmentUUID.uuidString)/twin"
        )
        async let lineage: AssessmentLineageResponse = get(
            path: "api/v1/assessments/\(assessmentUUID.uuidString)/lineage"
        )
        let (twinResponse, lineageResponse) = try await (twin, lineage)
        guard let documentID = lineageResponse.documentIDs.first?.uuidString else {
            throw AssessmentDashboardRepositoryError.unavailable
        }
        let confidence: DataConfidenceReport
        do {
            confidence = try await verificationRepository.dataConfidence(documentID: documentID)
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            throw AssessmentDashboardRepositoryError.unavailable
        }
        return try AssessmentDashboardMapper.map(
            summary: summary,
            twin: twinResponse,
            confidence: confidence
        )
    }

    private func completedSummary(assessmentID: UUID) async throws -> AssessmentDashboardResponse {
        var attempt = 0
        var elapsedSeconds: UInt64 = 0
        while !Task.isCancelled {
            let response: AssessmentDashboardResponse = try await get(
                path: "api/v1/assessments/\(assessmentID.uuidString)/dashboard"
            )
            switch response.status {
            case "COMPLETE" where response.twin != nil:
                return response
            case "FAILED", "HUMAN_REVIEW":
                throw AssessmentDashboardRepositoryError.unavailable
            default:
                break
            }
            let delay = pollingPolicy.delaySeconds(forAttempt: attempt)
            guard elapsedSeconds <= pollingPolicy.timeoutSeconds - min(
                delay,
                pollingPolicy.timeoutSeconds
            ) else {
                throw AssessmentDashboardRepositoryError.unavailable
            }
            try await sleep(delay)
            elapsedSeconds += delay
            attempt += 1
        }
        throw CancellationError()
    }

    private func get<Response: Decodable>(path: String) async throws -> Response {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        let data = try await execute(request, expectedStatus: 200)
        do {
            return try decoder.decode(Response.self, from: data)
        } catch {
            throw AssessmentDashboardRepositoryError.unavailable
        }
    }

    private func execute(_ request: URLRequest, expectedStatus: Int) async throws -> Data {
        var authorizedRequest: URLRequest
        do {
            authorizedRequest = try await authInterceptor.authorize(request)
        } catch {
            throw AssessmentDashboardRepositoryError.unavailable
        }
        var retryCount = 0
        while true {
            let (data, response) = try await response(for: authorizedRequest)
            guard let httpResponse = response as? HTTPURLResponse else {
                throw AssessmentDashboardRepositoryError.unavailable
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
            } catch {
                throw AssessmentDashboardRepositoryError.unavailable
            }
            guard httpResponse.statusCode == expectedStatus else {
                throw AssessmentDashboardRepositoryError.unavailable
            }
            return data
        }
    }

    private func response(for request: URLRequest) async throws -> (Data, URLResponse) {
        do {
            return try await session.response(for: request)
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            throw AssessmentDashboardRepositoryError.unavailable
        }
    }
}
