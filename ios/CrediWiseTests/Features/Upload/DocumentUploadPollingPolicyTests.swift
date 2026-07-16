import XCTest
@testable import CrediWise

final class DocumentUploadPollingPolicyTests: XCTestCase {
    func testBackoffStartsAtOneSecondAndCapsAtEight() {
        let policy = DocumentUploadPollingPolicy()

        XCTAssertEqual((0...5).map(policy.delaySeconds), [1, 2, 4, 8, 8, 8])
        XCTAssertEqual(policy.timeoutSeconds, 90)
    }
}
