import XCTest
@testable import CrediWise

@MainActor
final class AppCoordinatorTests: XCTestCase {
    func testStartsAtWelcome() {
        let coordinator = AppCoordinator()

        XCTAssertTrue(coordinator.path.isEmpty)
    }

    func testRoutesToRegistration() {
        let coordinator = AppCoordinator()

        coordinator.showRegistration()

        XCTAssertEqual(coordinator.path, [.registration])
    }

    func testRoutesToSignIn() {
        let coordinator = AppCoordinator()

        coordinator.showSignIn()

        XCTAssertEqual(coordinator.path, [.signIn])
    }

    func testReturnsToWelcomeFromNestedRoute() {
        let coordinator = AppCoordinator()
        coordinator.showRegistration()
        coordinator.showSignIn()

        coordinator.returnToWelcome()

        XCTAssertTrue(coordinator.path.isEmpty)
    }

    func testCompletingRegistrationRoutesToSignIn() {
        let coordinator = AppCoordinator()
        coordinator.showRegistration()

        coordinator.completeRegistration()

        XCTAssertEqual(coordinator.path, [.signIn])
    }

    func testSwitchesAuthenticationModeWithoutStackingRoutes() {
        let coordinator = AppCoordinator()
        coordinator.showRegistration()

        coordinator.switchAuthenticationMode(from: .registration)

        XCTAssertEqual(coordinator.path, [.signIn])
    }
}
