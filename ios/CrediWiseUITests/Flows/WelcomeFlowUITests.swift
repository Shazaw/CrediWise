import XCTest

final class WelcomeFlowUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testWelcomeScreenExposesPrimaryActionsAndDisclaimer() {
        let app = XCUIApplication()
        app.launch()

        XCTAssertTrue(app.otherElements["welcome.screen"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["welcome.create_account"].exists)
        XCTAssertTrue(app.buttons["welcome.sign_in"].exists)
        XCTAssertTrue(app.staticTexts["positioning.disclaimer"].exists)
    }

    func testCreateAccountActionUsesCoordinatorNavigation() {
        let app = XCUIApplication()
        app.launch()

        app.buttons["welcome.create_account"].tap()

        XCTAssertTrue(app.staticTexts["auth.placeholder.title"].waitForExistence(timeout: 2))
    }
}
