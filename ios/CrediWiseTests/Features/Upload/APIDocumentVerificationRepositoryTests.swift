import Foundation
import XCTest
@testable import CrediWise

final class APIDocumentVerificationRepositoryTests: XCTestCase {
    private let baseURL = URL(string: "https://api.crediwise.test")!
    private let documentID = UUID(uuidString: "BFA50DD7-F269-4013-BABF-11FD3EF142FE")!
    private let transactionID = UUID(uuidString: "CC21777F-8DB5-476C-B13A-3C7108F77461")!
    private let modelVersionID = UUID(uuidString: "0F057CAE-2C90-4E4A-92E9-99253610A20A")!

    func testReviewDecodesStatusAndTransactionContract() async throws {
        let session = VerificationStubSession(
            responses: [statusResponse(), transactionResponse()]
        )
        let repository = try await makeRepository(session: session)

        let review = try await repository.review(documentID: documentID.uuidString)

        XCTAssertEqual(review.documentID, documentID.uuidString)
        XCTAssertEqual(review.fileName, "statement.pdf")
        XCTAssertNil(review.accountOwner)
        XCTAssertEqual(review.transactions.count, 1)
        XCTAssertEqual(review.transactions[0].amount.normalized, -875_000)
        XCTAssertEqual(review.transactions[0].description.raw, "TOKO GROSIR MAKMUR")
        XCTAssertEqual(review.transactions[0].description.normalized, "Toko Grosir Makmur")
        XCTAssertEqual(review.transactions[0].category.normalized, .essentialExpense)
        XCTAssertEqual(review.transactions[0].extractionConfidence, 91)

        let requests = await session.allRequests()
        XCTAssertEqual(requests.map { $0.url?.path }, [
            "/api/v1/documents/\(documentID.uuidString)/status",
            "/api/v1/documents/\(documentID.uuidString)/transactions"
        ])
        XCTAssertTrue(requests.allSatisfy {
            $0.value(forHTTPHeaderField: "Authorization") == "Bearer access-value"
        })
        let transactionQuery = URLComponents(
            url: try XCTUnwrap(requests[1].url),
            resolvingAgainstBaseURL: false
        )?.queryItems
        XCTAssertEqual(transactionQuery?.first(where: { $0.name == "limit" })?.value, "500")
    }

    func testConfirmationSubmitsStructuredLineageThenConfirms() async throws {
        let session = VerificationStubSession(
            responses: [
                statusResponse(),
                transactionResponse(),
                .init(statusCode: 200, body: "{}"),
                .init(statusCode: 200, body: "{}")
            ]
        )
        let repository = try await makeRepository(session: session)
        _ = try await repository.review(documentID: documentID.uuidString)
        let correction = ExtractionReview.Correction(
            id: transactionID.uuidString,
            proposedCategory: .discretionary,
            proposedInternalTransfer: true
        )
        let submission = ExtractionReview.Submission(
            corrections: [correction],
            confirmsOwnership: true,
            reportsOwnershipConcern: false,
            reportsMissingRows: true
        )

        try await repository.confirm(documentID: documentID.uuidString, submission: submission)

        let requests = await session.allRequests()
        XCTAssertEqual(requests[2].url?.path, "/api/v1/documents/\(documentID.uuidString)/review")
        XCTAssertEqual(requests[3].url?.path, "/api/v1/documents/\(documentID.uuidString)/confirm")
        let body = try XCTUnwrap(requests[2].httpBody)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: body) as? [String: Any])
        let corrections = try XCTUnwrap(json["corrections"] as? [[String: Any]])
        XCTAssertEqual(corrections.count, 3)
        let category = try XCTUnwrap(
            corrections.first { $0["correction_type"] as? String == "WRONG_CATEGORY" }
        )
        XCTAssertEqual(category["raw_extracted_value"] as? String, "UNKNOWN")
        XCTAssertEqual(category["system_normalized_value"] as? String, "ESSENTIAL_EXPENSE")
        XCTAssertEqual(category["user_proposed_value"] as? String, "DISCRETIONARY")
    }

    func testDataConfidenceDecodesSuppliedScoresAndAttribution() async throws {
        let session = VerificationStubSession(responses: [verificationResponse()])
        let repository = try await makeRepository(session: session)

        let report = try await repository.dataConfidence(documentID: documentID.uuidString)

        XCTAssertEqual(report.score, 92)
        XCTAssertEqual(report.band, .high)
        XCTAssertEqual(report.dimensions.count, 7)
        XCTAssertEqual(report.dimensions.first?.id, "provenance")
        XCTAssertEqual(report.reasons.count, 3)
        XCTAssertEqual(report.assistanceStatus, .notUsed)
        XCTAssertEqual(report.modelVersion, modelVersionID.uuidString)
    }

    func testConfirmationWithoutLoadedReviewFailsClosed() async throws {
        let repository = try await makeRepository(session: VerificationStubSession(responses: []))
        let submission = ExtractionReview.Submission(
            corrections: [],
            confirmsOwnership: true,
            reportsOwnershipConcern: false,
            reportsMissingRows: false
        )

        do {
            try await repository.confirm(documentID: documentID.uuidString, submission: submission)
            XCTFail("Expected stale review protection")
        } catch let error as DocumentVerificationRepositoryError {
            XCTAssertEqual(error, .reviewChanged)
        }
    }

    private func makeRepository(
        session: VerificationStubSession
    ) async throws -> APIDocumentVerificationRepository {
        let tokenStore = VolatileTokenStore()
        try await tokenStore.save(
            SessionTokens(accessToken: "access-value", refreshToken: "refresh-value")
        )
        return APIDocumentVerificationRepository(
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

    private func statusResponse() -> VerificationStubResponse {
        .init(
            statusCode: 200,
            body: """
            {
              "document_id": "\(documentID.uuidString)",
              "file_name": "statement.pdf",
              "statement_start_date": "2026-06-01",
              "statement_end_date": "2026-06-30"
            }
            """
        )
    }

    private func transactionResponse() -> VerificationStubResponse {
        .init(
            statusCode: 200,
            body: """
            {
              "items": [{
                "transaction_id": "\(transactionID.uuidString)",
                "transaction_date": "2026-06-05",
                "amount": 875000,
                "direction": "DEBIT",
                "raw_description": "TOKO GROSIR MAKMUR",
                "normalized_description": "Toko Grosir Makmur",
                "category": "ESSENTIAL_EXPENSE",
                "is_internal_transfer": false,
                "is_duplicate": false,
                "extraction_confidence": "0.91"
              }],
              "next_cursor": null
            }
            """
        )
    }

    private func verificationResponse() -> VerificationStubResponse {
        .init(
            statusCode: 200,
            body: """
            {
              "data_confidence_score": "92.00",
              "band": "HIGH",
              "provenance_score": "94.00",
              "consistency_score": "95.00",
              "metadata_score": "96.00",
              "ocr_score": "93.00",
              "visual_score": "90.00",
              "completeness_score": "84.00",
              "ownership_score": "94.00",
              "reason_codes": [
                {"code":"PROVENANCE_ORIGINAL_PDF","description":"Source: Original Pdf"},
                {"code":"CONSISTENCY_MATCHED","description":"Balance sequence consistent"},
                {"code":"OWNERSHIP_MATCH","description":"Account holder name matches profile"}
              ],
              "recommendation": "Keep the original statement available.",
              "model_version_id": "\(modelVersionID.uuidString)",
              "ai_signal": "DISABLED",
              "verified_at": "2026-07-17T10:00:00Z"
            }
            """
        )
    }
}

private struct VerificationStubResponse: Sendable {
    let statusCode: Int
    let body: String
}

private actor VerificationStubSession: HTTPDataSession {
    private var responses: [VerificationStubResponse]
    private var requests: [URLRequest] = []

    init(responses: [VerificationStubResponse]) {
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

    func allRequests() -> [URLRequest] {
        requests
    }
}
