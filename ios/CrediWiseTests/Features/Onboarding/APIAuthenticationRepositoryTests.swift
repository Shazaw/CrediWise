import Foundation
import XCTest
@testable import CrediWise

final class APIAuthenticationRepositoryTests: XCTestCase {
    private let baseURL = URL(string: "https://api.crediwise.test")!

    func testRegisterEncodesRequestAndDecodesCurrentUserContract() async throws {
        let session = StubHTTPDataSession(
            statusCode: 201,
            body: """
            {
              "id": "BFA50DD7-F269-4013-BABF-11FD3EF142FE",
              "email": "ibu.sari@example.com",
              "role": "USER",
              "identity_status": "UNVERIFIED"
            }
            """
        )
        let repository = makeRepository(session: session)

        try await repository.register(email: "ibu.sari@example.com", password: "amanpassword1")

        let capturedRequest = await session.lastRequest()
        let request = try XCTUnwrap(capturedRequest)
        XCTAssertEqual(request.url?.path, "/api/v1/auth/register")
        XCTAssertEqual(request.httpMethod, "POST")
        let body = try XCTUnwrap(request.httpBody)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: body) as? [String: String])
        XCTAssertEqual(json["email"], "ibu.sari@example.com")
        XCTAssertEqual(json["password"], "amanpassword1")
    }

    func testSignInDecodesCurrentTokenContract() async throws {
        let session = StubHTTPDataSession(
            statusCode: 200,
            body: """
            {
              "access_token": "access-value",
              "refresh_token": "refresh-value",
              "token_type": "bearer",
              "expires_in": 900
            }
            """
        )
        let repository = makeRepository(session: session)

        let tokens = try await repository.signIn(
            email: "ibu.sari@example.com",
            password: "amanpassword1"
        )

        XCTAssertEqual(
            tokens,
            SessionTokens(accessToken: "access-value", refreshToken: "refresh-value")
        )
        let capturedRequest = await session.lastRequest()
        let request = try XCTUnwrap(capturedRequest)
        XCTAssertEqual(request.url?.path, "/api/v1/auth/login")
    }

    func testRefreshEncodesRotatingRefreshTokenContract() async throws {
        let session = StubHTTPDataSession(
            statusCode: 200,
            body: """
            {
              "access_token": "new-access",
              "refresh_token": "new-refresh",
              "token_type": "bearer",
              "expires_in": 900
            }
            """
        )
        let repository = makeRepository(session: session)

        let tokens = try await repository.refresh(refreshToken: "old-refresh")

        XCTAssertEqual(tokens.refreshToken, "new-refresh")
        let capturedRequest = await session.lastRequest()
        let request = try XCTUnwrap(capturedRequest)
        let body = try XCTUnwrap(request.httpBody)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: body) as? [String: String])
        XCTAssertEqual(request.url?.path, "/api/v1/auth/refresh")
        XCTAssertEqual(json["refresh_token"], "old-refresh")
    }

    func testSignOutSendsBearerAndRefreshToken() async throws {
        let store = VolatileTokenStore()
        try await store.save(SessionTokens(accessToken: "access-value", refreshToken: "refresh-value"))
        let session = StubHTTPDataSession(statusCode: 204, body: "")
        let repository = APIAuthenticationRepository(
            baseURL: baseURL,
            session: session,
            tokenStore: store
        )

        try await repository.signOut()

        let capturedRequest = await session.lastRequest()
        let request = try XCTUnwrap(capturedRequest)
        XCTAssertEqual(request.url?.path, "/api/v1/auth/logout")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-value")
        let body = try XCTUnwrap(request.httpBody)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: body) as? [String: String])
        XCTAssertEqual(json["refresh_token"], "refresh-value")
    }

    func testBackendErrorCodesMapToStableClientErrors() async throws {
        let session = StubHTTPDataSession(
            statusCode: 409,
            body: """
            {"error":{"code":"CONFLICT","message":"Email already registered","details":{},"correlation_id":"test"}}
            """
        )
        let repository = makeRepository(session: session)

        do {
            try await repository.register(email: "existing@example.com", password: "amanpassword1")
            XCTFail("Expected duplicate email error")
        } catch let error as AuthenticationRepositoryError {
            XCTAssertEqual(error, .duplicateEmail)
        }
    }

    private func makeRepository(session: StubHTTPDataSession) -> APIAuthenticationRepository {
        APIAuthenticationRepository(
            baseURL: baseURL,
            session: session,
            tokenStore: VolatileTokenStore()
        )
    }
}

private actor StubHTTPDataSession: HTTPDataSession {
    private let statusCode: Int
    private let body: Data
    private var requests: [URLRequest] = []

    init(statusCode: Int, body: String) {
        self.statusCode = statusCode
        self.body = Data(body.utf8)
    }

    func response(for request: URLRequest) async throws -> (Data, URLResponse) {
        requests.append(request)
        let response = HTTPURLResponse(
            url: request.url!,
            statusCode: statusCode,
            httpVersion: nil,
            headerFields: ["Content-Type": "application/json"]
        )!
        return (body, response)
    }

    func lastRequest() -> URLRequest? {
        requests.last
    }
}
