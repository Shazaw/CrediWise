import XCTest
@testable import CrediWise

@MainActor
final class UploadViewModelTests: XCTestCase {
    func testSuccessfulUploadPollsUntilComplete() async {
        let viewModel = makeViewModel(
            repository: MockDocumentUploadRepository(
                statuses: [.securityCheck, .extracting, .verifying, .complete]
            )
        )
        viewModel.selectSyntheticFile()

        await viewModel.upload()

        guard case let .completed(receipt) = viewModel.state else {
            return XCTFail("Expected completed state, got \(viewModel.state)")
        }
        XCTAssertEqual(receipt.fileName, "synthetic-bca-statement.pdf")
    }

    func testDuplicateReuseIsShownAsNoticeNotSecurityFailure() async {
        let viewModel = makeViewModel(
            repository: MockDocumentUploadRepository(statuses: [.duplicateReused])
        )
        viewModel.selectSyntheticFile()

        await viewModel.upload()

        guard case .duplicate = viewModel.state else {
            return XCTFail("Expected duplicate state, got \(viewModel.state)")
        }
    }

    func testSecurityRejectionOffersConstructiveFailure() async {
        let viewModel = makeViewModel(
            repository: MockDocumentUploadRepository(statuses: [.rejectedSecurity])
        )
        viewModel.selectSyntheticFile()

        await viewModel.upload()

        guard case let .failed(file, errorKey) = viewModel.state else {
            return XCTFail("Expected failed state, got \(viewModel.state)")
        }
        XCTAssertNotNil(file)
        XCTAssertEqual(errorKey, "upload.error.rejected_security")
    }

    func testUnsupportedLayoutDoesNotGetSilentlyInterpreted() async {
        let viewModel = makeViewModel(
            repository: MockDocumentUploadRepository(statuses: [.unsupportedFormat])
        )
        viewModel.selectSyntheticFile()

        await viewModel.upload()

        guard case let .failed(_, errorKey) = viewModel.state else {
            return XCTFail("Expected failed state, got \(viewModel.state)")
        }
        XCTAssertEqual(errorKey, "upload.error.unsupported_format")
    }

    func testPollingStopsAtConfiguredTimeout() async {
        let viewModel = UploadViewModel(
            repository: MockDocumentUploadRepository(statuses: [.extracting]),
            pollingPolicy: DocumentUploadPollingPolicy(
                initialDelaySeconds: 1,
                maximumDelaySeconds: 1,
                timeoutSeconds: 2
            ),
            sleep: { _ in }
        )
        viewModel.selectSyntheticFile()

        await viewModel.upload()

        guard case let .failed(_, errorKey) = viewModel.state else {
            return XCTFail("Expected timeout state, got \(viewModel.state)")
        }
        XCTAssertEqual(errorKey, "upload.error.timeout")
    }

    func testUnavailableRepositoryStatesFileWasNotSent() async {
        let viewModel = makeViewModel(repository: UnavailableDocumentUploadRepository())
        viewModel.selectSyntheticFile()

        await viewModel.upload()

        guard case let .failed(file, errorKey) = viewModel.state else {
            return XCTFail("Expected unavailable state, got \(viewModel.state)")
        }
        XCTAssertNotNil(file)
        XCTAssertEqual(errorKey, "upload.error.unavailable")
    }

    func testProtectedPDFRequestsTransientPassword() async {
        let viewModel = makeViewModel(
            repository: MockDocumentUploadRepository(uploadError: .pdfPasswordRequired)
        )
        viewModel.selectSyntheticFile()

        await viewModel.upload()

        guard case let .passwordRequired(file, invalid) = viewModel.state else {
            return XCTFail("Expected password-required state, got \(viewModel.state)")
        }
        XCTAssertEqual(file.fileName, "synthetic-bca-statement.pdf")
        XCTAssertFalse(invalid)
    }

    func testInvalidPDFPasswordReturnsToPasswordPrompt() async {
        let viewModel = makeViewModel(
            repository: MockDocumentUploadRepository(uploadError: .invalidPDFPassword)
        )
        viewModel.selectSyntheticFile()

        await viewModel.upload(pdfPassword: "wrong-value")

        guard case let .passwordRequired(_, invalid) = viewModel.state else {
            return XCTFail("Expected invalid-password state, got \(viewModel.state)")
        }
        XCTAssertTrue(invalid)
    }

    func testImageSourceSelectionPreservesDeclaredLineage() throws {
        let viewModel = makeViewModel(repository: MockDocumentUploadRepository())
        let imageURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("synthetic-upload-\(UUID().uuidString).png")
        try Data([0x89, 0x50, 0x4E, 0x47]).write(to: imageURL)
        defer { try? FileManager.default.removeItem(at: imageURL) }
        viewModel.selectFile(at: imageURL)

        viewModel.selectImageSourceType(.photo)

        guard case let .selected(file) = viewModel.state else {
            return XCTFail("Expected selected image, got \(viewModel.state)")
        }
        XCTAssertEqual(file.sourceType, .photo)
    }

    func testRetryAfterTimeoutChecksStatusWithoutUploadingAgain() async {
        let repository = MockDocumentUploadRepository(statuses: [.extracting, .complete])
        let viewModel = UploadViewModel(
            repository: repository,
            pollingPolicy: DocumentUploadPollingPolicy(
                initialDelaySeconds: 1,
                maximumDelaySeconds: 1,
                timeoutSeconds: 1
            ),
            sleep: { _ in }
        )
        viewModel.selectSyntheticFile()
        await viewModel.upload()

        await viewModel.retry()

        guard case .completed = viewModel.state else {
            return XCTFail("Expected completed state, got \(viewModel.state)")
        }
        let uploadCallCount = await repository.uploadCallCount()
        XCTAssertEqual(uploadCallCount, 1)
    }

    private func makeViewModel(repository: any DocumentUploadRepository) -> UploadViewModel {
        UploadViewModel(
            repository: repository,
            pollingPolicy: DocumentUploadPollingPolicy(
                initialDelaySeconds: 1,
                maximumDelaySeconds: 1,
                timeoutSeconds: 10
            ),
            sleep: { _ in }
        )
    }
}
