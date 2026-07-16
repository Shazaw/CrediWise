import Foundation

protocol HTTPDataSession: Sendable {
    func response(for request: URLRequest) async throws -> (Data, URLResponse)
}

extension URLSession: HTTPDataSession {
    func response(for request: URLRequest) async throws -> (Data, URLResponse) {
        try await data(for: request)
    }
}

actor APIAuthenticationRepository: AuthenticationRepository {
    private let baseURL: URL
    private let session: any HTTPDataSession
    private let tokenStore: any TokenStore
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    init(
        baseURL: URL,
        session: any HTTPDataSession = URLSession.shared,
        tokenStore: any TokenStore
    ) {
        self.baseURL = baseURL
        self.session = session
        self.tokenStore = tokenStore
    }

    func register(email: String, password: String) async throws {
        let data = try await send(
            path: "api/v1/auth/register",
            body: CredentialsRequest(email: email, password: password),
            expectedStatus: 201
        )
        _ = try decode(UserResponse.self, from: data)
    }

    func signIn(email: String, password: String) async throws -> SessionTokens {
        let data = try await send(
            path: "api/v1/auth/login",
            body: CredentialsRequest(email: email, password: password),
            expectedStatus: 200
        )
        return try decode(TokenPairResponse.self, from: data).sessionTokens
    }

    func refresh(refreshToken: String) async throws -> SessionTokens {
        let data = try await send(
            path: "api/v1/auth/refresh",
            body: RefreshTokenRequest(refreshToken: refreshToken),
            expectedStatus: 200
        )
        return try decode(TokenPairResponse.self, from: data).sessionTokens
    }

    func signOut() async throws {
        guard let tokens = try await tokenStore.load() else {
            return
        }

        let data = try encoder.encode(RefreshTokenRequest(refreshToken: tokens.refreshToken))
        var request = request(path: "api/v1/auth/logout")
        request.httpBody = data
        request.setValue("Bearer \(tokens.accessToken)", forHTTPHeaderField: "Authorization")
        _ = try await execute(request, expectedStatus: 204)
    }

    private func send<Body: Encodable>(
        path: String,
        body: Body,
        expectedStatus: Int
    ) async throws -> Data {
        var request = request(path: path)
        request.httpBody = try encoder.encode(body)
        return try await execute(request, expectedStatus: expectedStatus)
    }

    private func request(path: String) -> URLRequest {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        return request
    }

    private func execute(_ request: URLRequest, expectedStatus: Int) async throws -> Data {
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.response(for: request)
        } catch {
            throw AuthenticationRepositoryError.unavailable
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw AuthenticationRepositoryError.unavailable
        }
        guard httpResponse.statusCode == expectedStatus else {
            throw mapError(statusCode: httpResponse.statusCode, data: data)
        }
        return data
    }

    private func decode<Response: Decodable>(
        _ type: Response.Type,
        from data: Data
    ) throws -> Response {
        do {
            return try decoder.decode(type, from: data)
        } catch {
            throw AuthenticationRepositoryError.unavailable
        }
    }

    private func mapError(statusCode: Int, data: Data) -> AuthenticationRepositoryError {
        let code = try? decoder.decode(ErrorEnvelope.self, from: data).error.code
        if statusCode == 409, code == "CONFLICT" {
            return .duplicateEmail
        }
        if statusCode == 401, code == "AUTH_ERROR" {
            return .invalidCredentials
        }
        if statusCode == 429, code == "RATE_LIMITED" {
            return .rateLimited
        }
        return .unavailable
    }
}

private struct CredentialsRequest: Encodable {
    let email: String
    let password: String
}

private struct RefreshTokenRequest: Encodable {
    let refreshToken: String

    enum CodingKeys: String, CodingKey {
        case refreshToken = "refresh_token"
    }
}

private struct UserResponse: Decodable {
    let id: UUID
    let email: String
    let role: String
    let identityStatus: String

    enum CodingKeys: String, CodingKey {
        case id
        case email
        case role
        case identityStatus = "identity_status"
    }
}

private struct TokenPairResponse: Decodable {
    let accessToken: String
    let refreshToken: String
    let tokenType: String
    let expiresIn: Int

    var sessionTokens: SessionTokens {
        SessionTokens(accessToken: accessToken, refreshToken: refreshToken)
    }

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case tokenType = "token_type"
        case expiresIn = "expires_in"
    }
}

private struct ErrorEnvelope: Decodable {
    let error: APIError
}

private struct APIError: Decodable {
    let code: String
}
