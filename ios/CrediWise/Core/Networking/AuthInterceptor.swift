import Foundation

actor AuthInterceptor {
    typealias RefreshHandler = @Sendable (String) async throws -> SessionTokens
    typealias UnauthorizedHandler = @Sendable () async -> Void

    private let tokenStore: any TokenStore
    private let refreshHandler: RefreshHandler
    private let unauthorizedHandler: UnauthorizedHandler
    private var refreshTask: Task<SessionTokens, Error>?
    private var didInvalidateSession = false

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
        didInvalidateSession = false
        return attaching(accessToken: tokens.accessToken, to: request)
    }

    func requestForRetry(
        _ request: URLRequest,
        statusCode: Int,
        retryCount: Int
    ) async throws -> URLRequest? {
        guard statusCode == 401 else {
            return nil
        }
        guard retryCount == 0 else {
            await invalidateSessionOnce()
            throw AuthInterceptorError.unauthorized
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
        let task = Task {
            do {
                guard let refreshToken = try await tokenStore.load()?.refreshToken else {
                    throw AuthInterceptorError.missingSession
                }
                let tokens = try await refreshHandler(refreshToken)
                try await tokenStore.save(tokens)
                return tokens
            } catch is CancellationError {
                throw CancellationError()
            } catch let error as AuthInterceptorError {
                await self.invalidateSessionOnce()
                throw error
            } catch {
                await self.invalidateSessionOnce()
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

    private func invalidateSessionOnce() async {
        guard !didInvalidateSession else { return }
        didInvalidateSession = true
        try? await tokenStore.clear()
        await unauthorizedHandler()
    }

    private func attaching(accessToken: String, to request: URLRequest) -> URLRequest {
        var authorizedRequest = request
        authorizedRequest.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        return authorizedRequest
    }
}
