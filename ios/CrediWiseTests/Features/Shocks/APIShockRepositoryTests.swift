import Foundation
import XCTest
@testable import CrediWise

final class APIShockRepositoryTests: XCTestCase {
    private let baseURL = URL(string: "https://api.crediwise.test")!
    private let assessmentID = UUID(uuidString: "EAD33DE7-4220-4E50-93D4-84100253A714")!

    func testGetPreservesContractEnumsDecimalsAndProjectionOrder() async throws {
        let session = ShockStubSession(responses: [.init(statusCode: 200, body: responseBody())])
        let repository = try await makeRepository(session: session)

        let result = try await repository.shocks(assessmentID: assessmentID.uuidString)

        XCTAssertEqual(result.resilienceScore, Decimal(string: "68.25"))
        XCTAssertEqual(result.resilienceScoreScope, .canonicalBattery)
        XCTAssertEqual(result.band, .moderate)
        XCTAssertEqual(result.scenarios.map(\.kind), [
            .incomeDrop10, .incomeDrop20, .incomeDrop30, .delayedIncome,
            .emergencyExpense, .incomeSourceLoss, .weakestMonthReplay, .custom
        ])
        XCTAssertEqual(result.scenarios.last?.resilienceScoreContribution, Decimal(string: "7.50"))
        XCTAssertEqual(result.scenarios.last?.projectionPoints.map(\.sequence), [0, 1, 2])
        XCTAssertEqual(result.scenarios.last?.projectionPoints.map(\.dayOfMonth), [1, 15, 28])
        XCTAssertEqual(result.scenarios.last?.projectionPoints.map(\.eventType), [
            "OPENING_BALANCE", "CUSTOM_SHOCK", "PERIOD_END"
        ])
        XCTAssertEqual(result.reasons.first?.code, "SHOCK_BUFFER_BREACH")
        XCTAssertFalse(result.reasons[0].isKnown)
        XCTAssertTrue(result.reasons.dropFirst().allSatisfy(\.isKnown))
        XCTAssertTrue(result.scenarios.last?.projectionPoints[0].isKnownEventType == true)
        XCTAssertFalse(result.scenarios.last?.projectionPoints[1].isKnownEventType == true)
        XCTAssertEqual(result.explanation, "Backend explanation")
        XCTAssertEqual(result.modelVersion, "shock-v1")
        XCTAssertEqual(result.configHash, "config-abc")

        let requests = await session.requests()
        let request = try XCTUnwrap(requests.first)
        XCTAssertEqual(request.httpMethod, "GET")
        XCTAssertEqual(
            request.url?.path,
            "/api/v1/assessments/\(assessmentID.uuidString)/shocks"
        )
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-value")
    }

    func testSimulateSendsExactBodyAndPreservesSubmittedParameters() async throws {
        let session = ShockStubSession(responses: [.init(statusCode: 200, body: responseBody())])
        let repository = try await makeRepository(session: session)
        let parameters = ShockSimulationParameters(
            incomeDropPercentage: 20,
            emergencyExpense: 1_000_000,
            proposedInstalment: 350_000
        )

        let result = try await repository.simulate(
            assessmentID: assessmentID.uuidString,
            parameters: parameters
        )

        XCTAssertEqual(result.submittedParameters, parameters)
        let requests = await session.requests()
        let request = try XCTUnwrap(requests.first)
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(
            request.url?.path,
            "/api/v1/assessments/\(assessmentID.uuidString)/simulate"
        )
        let body = try XCTUnwrap(request.httpBody)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: body) as? [String: Any])
        XCTAssertEqual(json["income_drop_pct"] as? Int, 20)
        XCTAssertEqual(json["emergency_expense"] as? Int, 1_000_000)
        XCTAssertEqual(json["proposed_instalment"] as? Int, 350_000)
    }

    func testInvalidIdentifierAndParametersFailBeforeNetwork() async throws {
        let session = ShockStubSession(responses: [])
        let repository = try await makeRepository(session: session)

        await assertThrows(.invalidIdentifier) {
            _ = try await repository.shocks(assessmentID: "not-a-uuid")
        }
        await assertThrows(.invalidParameters) {
            _ = try await repository.simulate(
                assessmentID: assessmentID.uuidString,
                parameters: .init(
                    incomeDropPercentage: 101,
                    emergencyExpense: 0,
                    proposedInstalment: 0
                )
            )
        }
        let requests = await session.requests()
        XCTAssertTrue(requests.isEmpty)
    }

    func testStatusAndMalformedResponseMapping() async throws {
        for (status, code, expected) in [
            (404, "NOT_FOUND", ShockRepositoryError.notFound),
            (404, "ASSESSMENT_NOT_READY", .notReady),
            (409, "REASSESSMENT_REQUIRED", .reassessmentRequired),
            (422, "VALIDATION_ERROR", .invalidParameters),
            (429, "RATE_LIMITED", .rateLimited),
            (503, "UNAVAILABLE", .unavailable)
        ] {
            let session = ShockStubSession(responses: [
                .init(statusCode: status, body: errorBody(code: code))
            ])
            let repository = try await makeRepository(session: session)
            await assertThrows(expected) {
                _ = try await repository.shocks(assessmentID: assessmentID.uuidString)
            }
        }

        let malformed = ShockStubSession(responses: [
            .init(statusCode: 200, body: responseBody().replacingOccurrences(of: "CUSTOM", with: "NEW_KIND"))
        ])
        let repository = try await makeRepository(session: malformed)
        await assertThrows(.unavailable) {
            _ = try await repository.shocks(assessmentID: assessmentID.uuidString)
        }
    }

    func testCancellationIsNotSwallowed() async throws {
        let repository = try await makeRepository(session: ShockCancellationSession())
        do {
            _ = try await repository.shocks(assessmentID: assessmentID.uuidString)
            XCTFail("Expected cancellation")
        } catch is CancellationError {
        } catch {
            XCTFail("Expected CancellationError, got \(error)")
        }
    }

    func testIncompletePayloadIsNotReady() async throws {
        let body = responseBody()
            .replacingOccurrences(of: "\"resilience_score\":\"68.25\"", with: "\"resilience_score\":null")
            .replacingOccurrences(of: "\"band\":\"MODERATE\"", with: "\"band\":null")
        let session = ShockStubSession(responses: [.init(statusCode: 200, body: body)])
        let repository = try await makeRepository(session: session)

        await assertThrows(.notReady) {
            _ = try await repository.shocks(assessmentID: assessmentID.uuidString)
        }

        let emptyBody = responseBody().replacingOccurrences(
            of: "\"scenarios\":[",
            with: "\"ignored_scenarios\":["
        ).replacingOccurrences(
            of: "\"proposed_instalment\":350000",
            with: "\"scenarios\":[],\"proposed_instalment\":350000"
        )
        let emptySession = ShockStubSession(responses: [.init(statusCode: 200, body: emptyBody)])
        let emptyRepository = try await makeRepository(session: emptySession)
        await assertThrows(.notReady) {
            _ = try await emptyRepository.shocks(assessmentID: assessmentID.uuidString)
        }
    }

    func testNotCompleteValidationEnvelopeMapsNotReady() async throws {
        let session = ShockStubSession(responses: [
            .init(
                statusCode: 422,
                body: errorBody(
                    code: "VALIDATION_ERROR",
                    message: "Assessment must be COMPLETE before simulation",
                    status: "ANALYZING"
                )
            )
        ])
        let repository = try await makeRepository(session: session)
        await assertThrows(.notReady) {
            _ = try await repository.shocks(assessmentID: assessmentID.uuidString)
        }
    }

    private func makeRepository(session: any HTTPDataSession) async throws -> APIShockRepository {
        let tokenStore = VolatileTokenStore()
        try await tokenStore.save(.init(accessToken: "access-value", refreshToken: "refresh-value"))
        return APIShockRepository(
            baseURL: baseURL,
            session: session,
            authInterceptor: AuthInterceptor(
                tokenStore: tokenStore,
                refreshHandler: { _ in .init(accessToken: "refreshed", refreshToken: "refresh-value") },
                unauthorizedHandler: {}
            )
        )
    }

    private func assertThrows(
        _ expected: ShockRepositoryError,
        operation: () async throws -> Void
    ) async {
        do {
            try await operation()
            XCTFail("Expected \(expected)")
        } catch let error as ShockRepositoryError {
            XCTAssertEqual(error, expected)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
    }

    private func responseBody() -> String {
        let kinds = [
            "INCOME_DROP_10", "INCOME_DROP_20", "INCOME_DROP_30", "DELAYED_INCOME",
            "EMERGENCY_EXPENSE", "INCOME_SOURCE_LOSS", "WEAKEST_MONTH_REPLAY", "CUSTOM"
        ]
        let scenarios = kinds.map { kind in
            """
            {
              "scenario_type":"\(kind)",
              "parameters":{"income_drop_pct":20,"enabled":true,"note":null},
              "projected_cash_flow":1400000,
              "minimum_projected_balance":900000,
              "deficit_amount":0,
              "affordability_status":"STRAINED",
              "resilience_score_contribution":"7.50",
              "required_liquidity_buffer":1250000,
              "required_buffer_breached":true,
              "projection_points":[
                {"sequence":2,"day_of_month":28,"event_type":"PERIOD_END",
                "amount":500000,"projected_balance":1400000},
                {"sequence":0,"day_of_month":1,"event_type":"OPENING_BALANCE",
                "amount":0,"projected_balance":2100000},
                {"sequence":1,"day_of_month":15,"event_type":"CUSTOM_SHOCK",
                "amount":-1200000,"projected_balance":900000}
              ]
            }
            """
        }.joined(separator: ",")
        return """
        {
          "assessment_id":"\(assessmentID.uuidString)",
          "resilience_score":"68.25",
          "resilience_score_scope":"CANONICAL_BATTERY",
          "band":"MODERATE",
          "scenarios":[\(scenarios)],
          "proposed_instalment":350000,
          "required_liquidity_buffer":1250000,
          "reason_codes":[
            {"code":"SHOCK_BUFFER_BREACH","description":"Unknown fixture"},
            {"code":"SHOCK_RESILIENCE_STRONG","description":"Strong"},
            {"code":"SHOCK_RESILIENCE_MODERATE","description":"Moderate"},
            {"code":"SHOCK_RESILIENCE_FRAGILE","description":"Fragile"},
            {"code":"SHOCK_REQUIRED_BUFFER_COVERAGE","description":"Coverage"},
            {"code":"SHOCK_TEMPORAL_LIQUIDITY","description":"Liquidity"},
            {"code":"SHOCK_DEFICIT_CUSTOM","description":"Deficit"}
          ],
          "explanation":"Backend explanation",
          "model_version":"shock-v1",
          "config_hash":"config-abc"
        }
        """
    }

    private func errorBody(
        code: String,
        message: String = "error",
        status: String? = nil
    ) -> String {
        let details = status.map { "{\"status\":\"\($0)\"}" } ?? "{}"
        return """
        {"error":{"code":"\(code)","message":"\(message)",
        "details":\(details),"correlation_id":"test"}}
        """
    }
}

private struct ShockStubResponse: Sendable {
    let statusCode: Int
    let body: String
}

private actor ShockStubSession: HTTPDataSession {
    private var responses: [ShockStubResponse]
    private var capturedRequests: [URLRequest] = []

    init(responses: [ShockStubResponse]) { self.responses = responses }

    func response(for request: URLRequest) async throws -> (Data, URLResponse) {
        capturedRequests.append(request)
        guard !responses.isEmpty else { throw ShockRepositoryError.unavailable }
        let value = responses.removeFirst()
        return (
            Data(value.body.utf8),
            HTTPURLResponse(
                url: request.url!, statusCode: value.statusCode,
                httpVersion: nil, headerFields: nil
            )!
        )
    }

    func requests() -> [URLRequest] { capturedRequests }
}

private struct ShockCancellationSession: HTTPDataSession {
    func response(for request: URLRequest) async throws -> (Data, URLResponse) {
        throw CancellationError()
    }
}
