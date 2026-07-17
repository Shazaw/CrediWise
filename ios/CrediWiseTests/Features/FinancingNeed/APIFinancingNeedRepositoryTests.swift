import Foundation
import XCTest
@testable import CrediWise

final class APIFinancingNeedRepositoryTests: XCTestCase {
    private let baseURL = URL(string: "https://api.crediwise.test")!
    private let financingNeedID = UUID(uuidString: "A2F08E53-C537-4935-93EF-6411361959B6")!

    func testSaveEncodesFrozenContractAndReturnsServerIdentity() async throws {
        let session = FinancingNeedStubSession(
            response: .init(
                statusCode: 201,
                body: """
                {
                  "financing_need_id": "\(financingNeedID.uuidString)",
                  "requested_amount": 3500000,
                  "purpose": "PRODUCTIVE_BUSINESS",
                  "preferred_tenor_months": 18,
                  "urgency": "HIGH",
                  "notes": "Inventory restock",
                  "created_at": "2026-07-17T10:00:00Z"
                }
                """
            )
        )
        let repository = try await makeRepository(session: session)

        let receipt = try await repository.save(
            FinancingNeed(
                requestedAmount: 3_500_000,
                purpose: .productiveBusiness,
                preferredTenorMonths: 18,
                urgency: .high,
                notes: "Inventory restock"
            )
        )

        XCTAssertEqual(receipt.financingNeedID, financingNeedID.uuidString)
        let capturedRequest = await session.request()
        let request = try XCTUnwrap(capturedRequest)
        XCTAssertEqual(request.url?.path, "/api/v1/financing-needs")
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-value")
        let body = try XCTUnwrap(request.httpBody)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: body) as? [String: Any])
        XCTAssertEqual(json["requested_amount"] as? Int, 3_500_000)
        XCTAssertEqual(json["purpose"] as? String, "PRODUCTIVE_BUSINESS")
        XCTAssertEqual(json["preferred_tenor_months"] as? Int, 18)
        XCTAssertEqual(json["urgency"] as? String, "HIGH")
        XCTAssertEqual(json["notes"] as? String, "Inventory restock")
    }

    private func makeRepository(
        session: FinancingNeedStubSession
    ) async throws -> APIFinancingNeedRepository {
        let tokenStore = VolatileTokenStore()
        try await tokenStore.save(
            SessionTokens(accessToken: "access-value", refreshToken: "refresh-value")
        )
        return APIFinancingNeedRepository(
            baseURL: baseURL,
            session: session,
            authInterceptor: AuthInterceptor(
                tokenStore: tokenStore,
                refreshHandler: { _ in
                    SessionTokens(accessToken: "new-access", refreshToken: "new-refresh")
                },
                unauthorizedHandler: {}
            )
        )
    }
}

private struct FinancingNeedStubResponse: Sendable {
    let statusCode: Int
    let body: String
}

private actor FinancingNeedStubSession: HTTPDataSession {
    private let responseValue: FinancingNeedStubResponse
    private var capturedRequest: URLRequest?

    init(response: FinancingNeedStubResponse) {
        responseValue = response
    }

    func response(for request: URLRequest) async throws -> (Data, URLResponse) {
        capturedRequest = request
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

    func request() -> URLRequest? {
        capturedRequest
    }
}
