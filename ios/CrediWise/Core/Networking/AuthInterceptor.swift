import Foundation

actor AuthInterceptor {
    typealias RefreshHandler = @Sendable (String) async throws -> SessionTokens
    typealias UnauthorizedHandler = @Sendable () async -> Void

    private let tokenStore: any TokenStore
    private let refreshHandler: RefreshHandler
    private let unauthorizedHandler: UnauthorizedHandler
    private var refreshTask: Task<SessionTokens, Error>?

    init(
        tokenStore: any TokenStore,
        refreshHandler: @escaping RefreshHandler,
        unauthorizedHandler: @escaping UnauthorizedHandler
    ) {
        self.tokenStore = tokenStore
        self.refreshHandler = refreshHandler
        self.unauthorizedHandler = unauthorizedHandler
    }

    func authorize(_ request: URLRequest) async throws -> URLRequest {
        guard let tokens = try await tokenStore.load() else {
            throw AuthInterceptorError.missingSession
        }
        return attaching(accessToken: tokens.accessToken, to: request)
    }

    func requestForRetry(
        _ request: URLRequest,
        statusCode: Int,
        retryCount: Int
    ) async throws -> URLRequest? {
        guard statusCode == 401, retryCount == 0 else {
            return nil
        }

        let tokens = try await refreshTokens()
        return attaching(accessToken: tokens.accessToken, to: request)
    }

    private func refreshTokens() async throws -> SessionTokens {
        if let refreshTask {
            return try await refreshTask.value
        }

        let tokenStore = tokenStore
        let refreshHandler = refreshHandler
        let unauthorizedHandler = unauthorizedHandler
        let task = Task {
            do {
                guard let refreshToken = try await tokenStore.load()?.refreshToken else {
                    throw AuthInterceptorError.missingSession
                }
                let tokens = try await refreshHandler(refreshToken)
                try await tokenStore.save(tokens)
                return tokens
            } catch let error as AuthInterceptorError {
                try? await tokenStore.clear()
                await unauthorizedHandler()
                throw error
            } catch {
                try? await tokenStore.clear()
                await unauthorizedHandler()
                throw AuthInterceptorError.refreshFailed
            }
        }
        refreshTask = task

        do {
            let tokens = try await task.value
            refreshTask = nil
            return tokens
        } catch {
            refreshTask = nil
            throw error
        }
    }

    private func attaching(accessToken: String, to request: URLRequest) -> URLRequest {
        var authorizedRequest = request
        authorizedRequest.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        return authorizedRequest
    }
}
