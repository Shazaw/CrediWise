import XCTest
@testable import CrediWise

final class IDRFormatterTests: XCTestCase {
    func testFormatsWholeRupiahWithIndonesianGrouping() {
        XCTAssertEqual(IDRFormatter.string(from: 12_500_000), "Rp12.500.000")
        XCTAssertEqual(IDRFormatter.string(from: -875_000), "Rp-875.000")
        XCTAssertEqual(IDRFormatter.string(from: 0), "Rp0")
    }
}
