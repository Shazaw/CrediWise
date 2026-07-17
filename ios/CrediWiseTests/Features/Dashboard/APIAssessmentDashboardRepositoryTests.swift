import Foundation
import XCTest
@testable import CrediWise

final class APIAssessmentDashboardRepositoryTests: XCTestCase {
    private let baseURL = URL(string: "https://api.crediwise.test")!
    private let financingNeedID = UUID(uuidString: "A2F08E53-C537-4935-93EF-6411361959B6")!
    private let documentID = UUID(uuidString: "BFA50DD7-F269-4013-BABF-11FD3EF142FE")!
    private let assessmentID = UUID(uuidString: "EAD33DE7-4220-4E50-93D4-84100253A714")!
    private let modelVersionID = UUID(uuidString: "0F057CAE-2C90-4E4A-92E9-99253610A20A")!

    func testCreatePollAndDashboardPreserveIntegratedContractValues() async throws {
        let session = AssessmentStubSession(responses: responses())
        let repository = try await makeRepository(session: session)

        let createdID = try await repository.create(
            financingNeedID: financingNeedID.uuidString,
            documentID: documentID.uuidString
        )
        let dashboard = try await repository.dashboard(assessmentID: createdID)

        XCTAssertEqual(createdID, assessmentID.uuidString)
        XCTAssertEqual(dashboard.assessmentID, assessmentID.uuidString)
        XCTAssertEqual(dashboard.dataConfidence.score, 91)
        XCTAssertEqual(dashboard.risk.band, .bandB)
        XCTAssertEqual(dashboard.risk.modelConfidence, .high)
        XCTAssertEqual(dashboard.safeBorrowing.illustrativeAmount, 3_500_000)
        XCTAssertEqual(dashboard.safeBorrowing.maximumSafeInstalment, 375_000)
        XCTAssertEqual(dashboard.safeBorrowing.requiredLiquidityBuffer, 1_250_000)
        XCTAssertEqual(dashboard.twin.discretionaryExpenses, 300_000)
        XCTAssertEqual(dashboard.twin.personalIncome, 1_250_000)
        XCTAssertEqual(dashboard.twin.businessIncome, 2_450_000)
        XCTAssertEqual(dashboard.recommendations.map(\.id), ["protect-buffer", "stabilize-income"])
        XCTAssertEqual(dashboard.modelVersion, modelVersionID.uuidString)

        let requests = await session.requests()
        XCTAssertEqual(requests.filter { $0.url?.path.hasSuffix("/dashboard") == true }.count, 2)
        XCTAssertTrue(requests.allSatisfy {
            $0.value(forHTTPHeaderField: "Authorization") == "Bearer access-value"
        })
        let createRequest = try XCTUnwrap(requests.first)
        let body = try XCTUnwrap(createRequest.httpBody)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: body) as? [String: Any])
        XCTAssertEqual(json["financing_need_id"] as? String, financingNeedID.uuidString)
        XCTAssertEqual(json["source_document_ids"] as? [String], [documentID.uuidString])
    }

    private func makeRepository(
        session: AssessmentStubSession
    ) async throws -> APIAssessmentDashboardRepository {
        let tokenStore = VolatileTokenStore()
        try await tokenStore.save(
            SessionTokens(accessToken: "access-value", refreshToken: "refresh-value")
        )
        return APIAssessmentDashboardRepository(
            baseURL: baseURL,
            session: session,
            authInterceptor: AuthInterceptor(
                tokenStore: tokenStore,
                refreshHandler: { _ in
                    SessionTokens(accessToken: "new-access", refreshToken: "new-refresh")
                },
                unauthorizedHandler: {}
            ),
            verificationRepository: MockDocumentVerificationRepository(),
            pollingPolicy: DocumentUploadPollingPolicy(
                initialDelaySeconds: 0,
                maximumDelaySeconds: 0,
                timeoutSeconds: 1
            ),
            sleep: { _ in }
        )
    }

    private func responses() -> [String: [AssessmentStubResponse]] {
        [
            "/api/v1/assessments": [
                .init(
                    statusCode: 202,
                    body: """
                    {
                      "assessment_id":"\(assessmentID.uuidString)",
                      "status":"PENDING",
                      "poll":"/api/v1/assessments/\(assessmentID.uuidString)"
                    }
                    """
                )
            ],
            "/api/v1/assessments/\(assessmentID.uuidString)/dashboard": [
                .init(statusCode: 200, body: dashboardBody(status: "ANALYZING", twin: "null")),
                .init(statusCode: 200, body: dashboardBody(status: "COMPLETE", twin: twinSummary()))
            ],
            "/api/v1/assessments/\(assessmentID.uuidString)/twin": [
                .init(statusCode: 200, body: twinBody())
            ],
            "/api/v1/assessments/\(assessmentID.uuidString)/lineage": [
                .init(
                    statusCode: 200,
                    body: """
                    {
                      "assessment_id":"\(assessmentID.uuidString)",
                      "snapshot_hash":"abc",
                      "document_ids":["\(documentID.uuidString)"],
                      "transaction_ids":[],
                      "parser_versions":{},
                      "categorizer_version":"v1",
                      "engine_config_hash":"def"
                    }
                    """
                )
            ]
        ]
    }

    private func dashboardBody(status: String, twin: String) -> String {
        """
        {
          "assessment_id": "\(assessmentID.uuidString)",
          "status": "\(status)",
          "model_version_id": "\(modelVersionID.uuidString)",
          "positioning_notice": "Estimated assessment",
          "data_confidence": {
            "score": "91.00", "band": "HIGH", "reasons": [],
            "reason_codes": []
          },
          "risk_band": {
            "band": "B", "model_confidence": "HIGH", "positive": [], "risk": [],
            "positive_reason_codes": [
              {"code":"RISK_CASH_FLOW_STRONG","description":"Positive cash flow in most months"}
            ],
            "risk_reason_codes": [
              {"code":"RISK_INCOME_CONCENTRATION","description":"Single source over 80%"},
              {"code":"SAFE_BORROWING_LIMITED_BY_DSTI","description":"Bound by DSTI"}
            ]
          },
          "safe_borrowing": {
            "amount": 3500000, "max_instalment": 375000,
            "required_liquidity_buffer": 1250000,
            "tenor_months": 12, "due_date_window": [20,25], "frequency": "MONTHLY"
          },
          "twin": \(twin)
        }
        """
    }

    private func twinSummary() -> String {
        """
        {
          "median_income":3700000,
          "essential_expenses":2050000,
          "existing_debt":200000,
          "average_free_cash_flow":1150000,
          "weakest_month_cash_flow":475000
        }
        """
    }

    private func twinBody() -> String {
        """
        {
          "assessment_id":"\(assessmentID.uuidString)",
          "average_income":3700000,"median_income":3700000,"income_volatility":"0.12",
          "essential_expenses":2050000,"discretionary_expenses":300000,"existing_debt":200000,
          "average_free_cash_flow":1150000,"minimum_balance":1500000,
          "positive_cash_flow_ratio":"1.0","weakest_month_cash_flow":475000,
          "savings_buffer":1500000,"months_covered":3,"coverage_flag":"SUFFICIENT",
          "monthly_snapshots":[],
          "income_sources":[
            {
              "source_name":"Salary","source_type":"SALARY","average_amount":1250000,
              "frequency":"MONTHLY","volatility":"0.1","concentration_ratio":"0.34",
              "dominant_arrival_day":25,"confidence":"0.9"
            },
            {
              "source_name":"QRIS","source_type":"QRIS_SETTLEMENT","average_amount":2450000,
              "frequency":"WEEKLY","volatility":"0.2","concentration_ratio":"0.66",
              "dominant_arrival_day":5,"confidence":"0.9"
            }
          ],
          "cash_flow_events":[]
        }
        """
    }
}

private struct AssessmentStubResponse: Sendable {
    let statusCode: Int
    let body: String
}

private actor AssessmentStubSession: HTTPDataSession {
    private var responses: [String: [AssessmentStubResponse]]
    private var capturedRequests: [URLRequest] = []

    init(responses: [String: [AssessmentStubResponse]]) {
        self.responses = responses
    }

    func response(for request: URLRequest) async throws -> (Data, URLResponse) {
        capturedRequests.append(request)
        let path = request.url?.path ?? ""
        guard var routeResponses = responses[path], !routeResponses.isEmpty else {
            throw AssessmentDashboardRepositoryError.unavailable
        }
        let responseValue = routeResponses.removeFirst()
        responses[path] = routeResponses
        return (
            Data(responseValue.body.utf8),
            HTTPURLResponse(
                url: request.url!,
                statusCode: responseValue.statusCode,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
        )
    }

    func requests() -> [URLRequest] {
        capturedRequests
    }
}
