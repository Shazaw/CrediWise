import XCTest

final class WelcomeFlowUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testWelcomeScreenExposesPrimaryActionsAndDisclaimer() {
        let app = launchApp()

        XCTAssertTrue(app.otherElements["welcome.screen"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["welcome.create_account"].exists)
        XCTAssertTrue(app.buttons["welcome.sign_in"].exists)
        XCTAssertTrue(app.staticTexts["positioning.disclaimer"].exists)
    }

    func testCreateAccountActionUsesCoordinatorNavigation() {
        let app = launchApp()

        app.buttons["welcome.create_account"].tap()

        XCTAssertTrue(app.staticTexts["auth.title"].waitForExistence(timeout: 2))
        XCTAssertTrue(app.textFields["auth.email"].exists)
        XCTAssertTrue(app.secureTextFields["auth.password"].exists)
    }

    func testRegistrationShowsInlineValidation() {
        let app = launchApp()
        app.buttons["welcome.create_account"].tap()

        app.buttons["auth.submit"].tap()

        XCTAssertTrue(app.staticTexts["auth.email_error"].waitForExistence(timeout: 2))
        XCTAssertTrue(app.staticTexts["auth.password_error"].exists)
    }

    func testSignInTransitionsToAuthenticatedFlow() {
        let app = launchApp()
        signIn(app)

        XCTAssertTrue(app.staticTexts["session.authenticated.title"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.buttons["session.start_upload"].exists)
        XCTAssertTrue(app.buttons["session.sign_out"].exists)
    }

    func testSyntheticUploadCompletesAccessibleProcessingFlow() {
        let app = launchApp()
        signIn(app)
        XCTAssertTrue(app.buttons["session.start_upload"].waitForExistence(timeout: 3))

        app.buttons["session.start_upload"].tap()

        XCTAssertTrue(app.buttons["upload.choose_file"].waitForExistence(timeout: 2))
        app.buttons["upload.synthetic_fixture"].tap()
        XCTAssertTrue(app.staticTexts["upload.file.name"].waitForExistence(timeout: 2))

        app.buttons["upload.submit"].tap()

        XCTAssertTrue(app.staticTexts["upload.processing.status"].waitForExistence(timeout: 2))
        XCTAssertTrue(app.buttons["upload.another"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.otherElements["upload.processing.stage.0"].waitForExistence(timeout: 2))
        XCTAssertTrue(app.staticTexts["positioning.disclaimer"].exists)
    }

    private func launchApp() -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing"]
        app.launch()
        return app
    }

    private func signIn(_ app: XCUIApplication) {
        app.buttons["welcome.sign_in"].tap()
        app.textFields["auth.email"].tap()
        app.textFields["auth.email"].typeText("person@example.com")
        app.secureTextFields["auth.password"].tap()
        app.secureTextFields["auth.password"].typeText("safePassword1")
        app.swipeUp()
        app.buttons["auth.submit"].tap()
    }
}
