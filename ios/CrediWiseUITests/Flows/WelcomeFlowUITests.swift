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

        let riskCard = app.descendants(matching: .any)["dashboard.risk.card"]
        let safeCard = app.descendants(matching: .any)["dashboard.safe.card"]
        XCTAssertTrue(riskCard.waitForExistence(timeout: 3))
        XCTAssertTrue(safeCard.exists)

        let twin = app.descendants(matching: .any)["dashboard.twin"]
        for _ in 0..<4 where !twin.exists {
            app.swipeUp()
        }
        XCTAssertTrue(twin.waitForExistence(timeout: 2))
    }

    func testCycle6FlowExplainsShocksAndDangerousSimulatedOffer() {
        let app = launchApp(arguments: ["--cycle-6-flow"])
        signIn(app)
        startCycle5Upload(app)
        completeSyntheticAssessment(app)

        let shockCard = app.buttons["dashboard.shock.card"]
        scrollUntilHittable(shockCard, in: app)
        shockCard.tap()
        XCTAssertTrue(app.otherElements["shocks.screen"].waitForExistence(timeout: 3))

        let simulateButton = app.buttons["shocks.simulate"]
        scrollUntilHittable(simulateButton, in: app)
        simulateButton.tap()
        let chart = app.otherElements["shocks.chart"]
        scrollUntilHittable(chart, in: app, attempts: 8)

        app.navigationBars.buttons.element(boundBy: 0).tap()
        let offersButton = app.buttons["dashboard.offers.action"]
        scrollUntilHittable(offersButton, in: app)
        offersButton.tap()
        XCTAssertTrue(app.otherElements["offers.screen"].waitForExistence(timeout: 3))

        let unsafeOffer = app.buttons["offers.row.offer-unsafe"]
        scrollUntilHittable(unsafeOffer, in: app)
        unsafeOffer.tap()
        XCTAssertTrue(app.otherElements["offers.detail.screen"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.descendants(matching: .any)["offers.simulated"].exists)
        XCTAssertTrue(app.descendants(matching: .any)["offers.warning.REFINANCING_DEPENDENCY_RISK"].exists)
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

    private func completeSyntheticAssessment(_ app: XCUIApplication) {
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
    }

    private func scrollUntilHittable(
        _ element: XCUIElement,
        in app: XCUIApplication,
        attempts: Int = 5
    ) {
        XCTAssertTrue(element.waitForExistence(timeout: 3))
        for _ in 0..<attempts where !element.isHittable {
            app.swipeUp()
        }
        XCTAssertTrue(element.isHittable)
    }
}
