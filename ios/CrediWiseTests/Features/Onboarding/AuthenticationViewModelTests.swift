import XCTest
@testable import CrediWise

@MainActor
final class AuthenticationViewModelTests: XCTestCase {
    func testRegistrationRejectsInvalidFields() async {
        let viewModel = makeViewModel(mode: .registration)
        viewModel.email = "not-an-email"
        viewModel.password = "short"
        viewModel.passwordConfirmation = "different"

        let outcome = await viewModel.submit()

        XCTAssertNil(outcome)
        XCTAssertEqual(viewModel.emailErrorKey, "auth.validation.email")
        XCTAssertEqual(viewModel.passwordErrorKey, "auth.validation.password")
        XCTAssertEqual(
            viewModel.confirmationErrorKey,
            "auth.validation.password_confirmation"
        )
    }

    func testRegistrationMapsDuplicateEmail() async {
        let viewModel = makeViewModel(mode: .registration)
        populateValidFields(viewModel, email: "existing@example.com")

        let outcome = await viewModel.submit()

        XCTAssertNil(outcome)
        XCTAssertEqual(viewModel.state, .error("auth.error.duplicate_email"))
    }

    func testRegistrationDoesNotCreateSession() async {
        let sessionManager = SessionManager(tokenStore: VolatileTokenStore())
        let viewModel = makeViewModel(mode: .registration, sessionManager: sessionManager)
        populateValidFields(viewModel)

        let outcome = await viewModel.submit()

        XCTAssertEqual(outcome, .registered)
        XCTAssertEqual(sessionManager.state, .restoring)
    }

    func testSignInPersistsSession() async {
        let store = VolatileTokenStore()
        let sessionManager = SessionManager(tokenStore: store)
        let viewModel = makeViewModel(mode: .signIn, sessionManager: sessionManager)
        populateValidFields(viewModel)

        let outcome = await viewModel.submit()

        XCTAssertEqual(outcome, .signedIn)
        XCTAssertEqual(sessionManager.state, .signedIn)
        let storedTokens = try? await store.load()
        XCTAssertNotNil(storedTokens)
    }

    func testSignInMapsInvalidCredentials() async {
        let viewModel = makeViewModel(mode: .signIn)
        populateValidFields(viewModel, email: "blocked@example.com")

        let outcome = await viewModel.submit()

        XCTAssertNil(outcome)
        XCTAssertEqual(viewModel.state, .error("auth.error.invalid_credentials"))
    }

    func testUnavailableConcreteContractDoesNotCreateDemoSession() async {
        let sessionManager = SessionManager(tokenStore: VolatileTokenStore())
        let viewModel = AuthenticationViewModel(
            mode: .signIn,
            repository: UnavailableAuthenticationRepository(),
            sessionManager: sessionManager
        )
        populateValidFields(viewModel)

        let outcome = await viewModel.submit()

        XCTAssertNil(outcome)
        XCTAssertEqual(viewModel.state, .error("auth.error.unavailable"))
        XCTAssertEqual(sessionManager.state, .restoring)
    }

    private func makeViewModel(
        mode: AuthenticationMode,
        sessionManager: SessionManager? = nil
    ) -> AuthenticationViewModel {
        AuthenticationViewModel(
            mode: mode,
            repository: MockAuthenticationRepository(),
            sessionManager: sessionManager ?? SessionManager(tokenStore: VolatileTokenStore())
        )
    }

    private func populateValidFields(
        _ viewModel: AuthenticationViewModel,
        email: String = "person@example.com"
    ) {
        viewModel.email = email
        viewModel.password = "safePassword1"
        viewModel.passwordConfirmation = "safePassword1"
    }
}
