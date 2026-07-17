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
        startUpload(app)

        XCTAssertTrue(app.buttons["upload.choose_file"].waitForExistence(timeout: 2))
        app.buttons["upload.synthetic_fixture"].tap()
        XCTAssertTrue(app.staticTexts["upload.file.name"].waitForExistence(timeout: 2))

        app.buttons["upload.submit"].tap()

        XCTAssertTrue(app.staticTexts["upload.processing.status"].waitForExistence(timeout: 2))
        XCTAssertTrue(app.buttons["upload.another"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["positioning.disclaimer"].exists)
    }

    func testSyntheticStatementCanBeReviewedAndExplained() {
        let app = launchApp(arguments: ["--review-flow"])
        signIn(app)
        startUpload(app)
        XCTAssertTrue(app.buttons["upload.synthetic_fixture"].waitForExistence(timeout: 2))
        app.buttons["upload.synthetic_fixture"].tap()
        app.buttons["upload.submit"].tap()

        XCTAssertTrue(app.buttons["upload.review"].waitForExistence(timeout: 5))
        app.buttons["upload.review"].tap()
        XCTAssertTrue(app.staticTexts["review.title"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["review.correction_count"].exists)

        app.swipeUp()
        XCTAssertTrue(app.switches["review.ownership"].waitForExistence(timeout: 2))
        app.switches["review.ownership"].tap()
        app.buttons["review.confirm"].tap()
        XCTAssertTrue(app.buttons["review.show_confidence"].waitForExistence(timeout: 3))
        app.buttons["review.show_confidence"].tap()

        XCTAssertTrue(app.buttons["confidence.card"].waitForExistence(timeout: 3))
        app.buttons["confidence.card"].tap()
        XCTAssertTrue(app.staticTexts["confidence.detail.title"].waitForExistence(timeout: 3))
    }

    func testCycle5FlowShowsSuppliedTwinRiskAndSafeBorrowing() {
        let app = launchApp(arguments: ["--cycle-5-flow"])
        signIn(app)
        startCycle5Upload(app)
        app.buttons["upload.synthetic_fixture"].tap()
        app.buttons["upload.submit"].tap()
        XCTAssertTrue(app.buttons["upload.review"].waitForExistence(timeout: 5))
        app.buttons["upload.review"].tap()
        app.swipeUp()
        XCTAssertTrue(app.switches["review.ownership"].waitForExistence(timeout: 2))
        app.switches["review.ownership"].tap()
        app.buttons["review.confirm"].tap()
        XCTAssertTrue(app.buttons["review.show_confidence"].waitForExistence(timeout: 3))
        app.buttons["review.show_confidence"].tap()

        XCTAssertTrue(app.buttons["confidence.continue_dashboard"].waitForExistence(timeout: 3))
        app.buttons["confidence.continue_dashboard"].tap()

        XCTAssertTrue(app.otherElements["dashboard.screen"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.buttons["dashboard.risk.card"].exists)
        XCTAssertTrue(app.buttons["dashboard.safe.card"].exists)
        app.swipeUp()
        XCTAssertTrue(app.otherElements["dashboard.twin"].waitForExistence(timeout: 2))
        XCTAssertTrue(app.staticTexts["positioning.disclaimer"].exists)
    }

    private func launchApp(arguments: [String] = []) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing"] + arguments
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

    private func startUpload(_ app: XCUIApplication) {
        XCTAssertTrue(app.buttons["session.start_upload"].waitForExistence(timeout: 3))
        app.buttons["session.start_upload"].tap()
        XCTAssertTrue(app.buttons["upload.choose_file"].waitForExistence(timeout: 3))
    }

    private func startCycle5Upload(_ app: XCUIApplication) {
        XCTAssertTrue(app.buttons["session.start_assessment"].waitForExistence(timeout: 3))
        app.buttons["session.start_assessment"].tap()
        XCTAssertTrue(app.textFields["financing_need.amount"].waitForExistence(timeout: 2))
        app.textFields["financing_need.amount"].tap()
        app.textFields["financing_need.amount"].typeText("3500000")
        app.buttons["financing_need.purpose"].tap()
        XCTAssertTrue(
            app.buttons["financing_need.purpose.productiveBusiness"].waitForExistence(timeout: 2)
        )
        app.buttons["financing_need.purpose.productiveBusiness"].tap()
        app.swipeUp()
        app.buttons["financing_need.submit"].tap()
        XCTAssertTrue(app.buttons["upload.choose_file"].waitForExistence(timeout: 3))
    }
}
