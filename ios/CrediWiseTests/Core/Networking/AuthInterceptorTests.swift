import Foundation
import XCTest
@testable import CrediWise

final class AuthInterceptorTests: XCTestCase {
    func testAuthorizeAttachesBearerToken() async throws {
        let store = VolatileTokenStore(tokens: makeTokens(access: "current"))
        let interceptor = makeInterceptor(store: store)

        let request = try await interceptor.authorize(makeRequest())

        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer current")
    }

    func testUnauthorizedResponseRefreshesAndRetriesOnce() async throws {
        let store = VolatileTokenStore(tokens: makeTokens(access: "expired"))
        let probe = RefreshProbe(result: .success(makeTokens(access: "renewed")))
        let interceptor = makeInterceptor(store: store, probe: probe)

        let retry = try await interceptor.requestForRetry(
            makeRequest(),
            statusCode: 401,
            retryCount: 0
        )

        XCTAssertEqual(retry?.value(forHTTPHeaderField: "Authorization"), "Bearer renewed")
        let callCount = await probe.callCount
        XCTAssertEqual(callCount, 1)
    }

    func testTerminalUnauthorizedClearsSessionAndInvalidatesOnce() async throws {
        let store = VolatileTokenStore(tokens: makeTokens())
        let invalidation = InvalidationProbe()
        let interceptor = makeInterceptor(store: store, invalidation: invalidation)

        for _ in 0..<2 {
            do {
                _ = try await interceptor.requestForRetry(
                    makeRequest(),
                    statusCode: 401,
                    retryCount: 1
                )
                XCTFail("Expected terminal unauthorized error")
            } catch {
                XCTAssertEqual(error as? AuthInterceptorError, .unauthorized)
            }
        }

        let storedTokens = try await store.load()
        let invalidationCount = await invalidation.callCount
        XCTAssertNil(storedTokens)
        XCTAssertEqual(invalidationCount, 1)
    }

    func testConcurrentUnauthorizedResponsesShareRefresh() async throws {
        let store = VolatileTokenStore(tokens: makeTokens(access: "expired"))
        let probe = RefreshProbe(result: .success(makeTokens(access: "renewed")), delay: true)
        let invalidation = InvalidationProbe()
        let interceptor = makeInterceptor(store: store, probe: probe, invalidation: invalidation)
        let request = makeRequest()

        async let first = interceptor.requestForRetry(request, statusCode: 401, retryCount: 0)
        async let second = interceptor.requestForRetry(request, statusCode: 401, retryCount: 0)
        _ = try await (first, second)

        async let firstTerminal: URLRequest? = try? await interceptor.requestForRetry(
            request, statusCode: 401, retryCount: 1
        )
        async let secondTerminal: URLRequest? = try? await interceptor.requestForRetry(
            request, statusCode: 401, retryCount: 1
        )
        _ = await (firstTerminal, secondTerminal)

        let callCount = await probe.callCount
        let invalidationCount = await invalidation.callCount
        XCTAssertEqual(callCount, 1)
        XCTAssertEqual(invalidationCount, 1)
    }

    func testRefreshFailureClearsTokensAndInvalidatesSession() async throws {
        let store = VolatileTokenStore(tokens: makeTokens(access: "expired"))
        let probe = RefreshProbe(result: .failure(TestError.refreshFailed))
        let invalidation = InvalidationProbe()
        let interceptor = makeInterceptor(store: store, probe: probe, invalidation: invalidation)

        do {
            _ = try await interceptor.requestForRetry(
                makeRequest(),
                statusCode: 401,
                retryCount: 0
            )
            XCTFail("Expected refresh failure")
        } catch {
            XCTAssertEqual(error as? AuthInterceptorError, .refreshFailed)
        }

        let storedTokens = try await store.load()
        let invalidationCount = await invalidation.callCount
        XCTAssertNil(storedTokens)
        XCTAssertEqual(invalidationCount, 1)
    }

    func testConcurrentRefreshFailureInvalidatesSessionOnce() async throws {
        let store = VolatileTokenStore(tokens: makeTokens(access: "expired"))
        let probe = RefreshProbe(result: .failure(TestError.refreshFailed), delay: true)
        let invalidation = InvalidationProbe()
        let interceptor = makeInterceptor(store: store, probe: probe, invalidation: invalidation)
        let request = makeRequest()

        async let first = interceptor.requestForRetry(request, statusCode: 401, retryCount: 0)
        async let second = interceptor.requestForRetry(request, statusCode: 401, retryCount: 0)
        _ = try? await first
        _ = try? await second

        let refreshCount = await probe.callCount
        let invalidationCount = await invalidation.callCount
        XCTAssertEqual(refreshCount, 1)
        XCTAssertEqual(invalidationCount, 1)
    }

    func testRefreshCancellationPreservesSessionAndDoesNotInvalidate() async throws {
        let tokens = makeTokens(access: "expired")
        let store = VolatileTokenStore(tokens: tokens)
        let probe = RefreshProbe(result: .failure(CancellationError()))
        let invalidation = InvalidationProbe()
        let interceptor = makeInterceptor(store: store, probe: probe, invalidation: invalidation)

        do {
            _ = try await interceptor.requestForRetry(
                makeRequest(),
                statusCode: 401,
                retryCount: 0
            )
            XCTFail("Expected cancellation")
        } catch is CancellationError {
        } catch {
            XCTFail("Expected CancellationError, got \(error)")
        }

        let storedTokens = try await store.load()
        let invalidationCount = await invalidation.callCount
        XCTAssertEqual(storedTokens, tokens)
        XCTAssertEqual(invalidationCount, 0)
    }

    private func makeInterceptor(
        store: VolatileTokenStore,
        probe: RefreshProbe = RefreshProbe(result: .success(
            SessionTokens(accessToken: "renewed", refreshToken: "rotated")
        )),
        invalidation: InvalidationProbe = InvalidationProbe()
    ) -> AuthInterceptor {
        AuthInterceptor(
            tokenStore: store,
            refreshHandler: { refreshToken in
                try await probe.refresh(using: refreshToken)
            },
            unauthorizedHandler: {
                await invalidation.record()
            }
        )
    }

    private func makeRequest() -> URLRequest {
        URLRequest(url: URL(string: "https://example.invalid/api/v1/me")!)
    }

    private func makeTokens(access: String = "access") -> SessionTokens {
        SessionTokens(accessToken: access, refreshToken: "refresh")
    }

    private actor RefreshProbe {
        private(set) var callCount = 0
        private let result: Result<SessionTokens, Error>
        private let delay: Bool

        init(result: Result<SessionTokens, Error>, delay: Bool = false) {
            self.result = result
            self.delay = delay
        }

        func refresh(using refreshToken: String) async throws -> SessionTokens {
            callCount += 1
            if delay {
                try await Task.sleep(nanoseconds: 50_000_000)
            }
            return try result.get()
        }
    }

    private actor InvalidationProbe {
        private(set) var callCount = 0

        func record() {
            callCount += 1
        }
    }

    private enum TestError: Error {
        case refreshFailed
    }
}
