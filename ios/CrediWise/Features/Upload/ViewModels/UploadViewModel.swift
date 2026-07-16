import Combine
import Foundation

@MainActor
final class UploadViewModel: ObservableObject {
    @Published private(set) var state: UploadViewState = .idle

    private let repository: any DocumentUploadRepository
    private let validator: UploadFileValidator
    private let pollingPolicy: DocumentUploadPollingPolicy
    private let sleep: @Sendable (UInt64) async throws -> Void
    private var currentFile: SelectedUploadFile?
    private var currentReceipt: DocumentUploadReceipt?
    private var currentStatus: DocumentProcessingStatus?

    init(
        repository: any DocumentUploadRepository,
        validator: UploadFileValidator = UploadFileValidator(),
        pollingPolicy: DocumentUploadPollingPolicy = DocumentUploadPollingPolicy(),
        sleep: @escaping @Sendable (UInt64) async throws -> Void = { seconds in
            try await Task.sleep(nanoseconds: seconds * 1_000_000_000)
        }
    ) {
        self.repository = repository
        self.validator = validator
        self.pollingPolicy = pollingPolicy
        self.sleep = sleep
    }

    var isBusy: Bool {
        switch state {
        case .uploading, .processing:
            return true
        default:
            return false
        }
    }

    func selectFile(at url: URL) {
        do {
            let file = try validator.validate(url: url)
            currentFile = file
            state = .selected(file)
        } catch let error as UploadFileValidationError {
            currentFile = nil
            state = .failed(nil, errorKey: errorKey(for: error))
        } catch {
            currentFile = nil
            state = .failed(nil, errorKey: "upload.error.unreadable")
        }
    }

    func selectSyntheticFile() {
        let file = SelectedUploadFile(
            url: URL(fileURLWithPath: "/tmp/crediwise-synthetic-statement.pdf"),
            fileName: "synthetic-bca-statement.pdf",
            byteCount: 245_760,
            mimeType: "application/pdf",
            sourceType: .originalPDF
        )
        currentFile = file
        state = .selected(file)
    }

    func handlePickerFailure() {
        currentFile = nil
        state = .failed(nil, errorKey: "upload.error.unreadable")
    }

    func selectImageSourceType(_ sourceType: DocumentSourceType) {
        guard let file = currentFile, file.mimeType.hasPrefix("image/") else {
            return
        }
        let updatedFile = file.with(sourceType: sourceType)
        currentFile = updatedFile
        state = .selected(updatedFile)
    }

    func upload(pdfPassword: String? = nil) async {
        guard !isBusy, let file = currentFile, file.sourceType != nil else {
            return
        }

        state = .uploading(file, progress: 0)
        currentReceipt = nil
        currentStatus = nil
        let hasSecurityScope = file.url.startAccessingSecurityScopedResource()
        defer {
            if hasSecurityScope {
                file.url.stopAccessingSecurityScopedResource()
            }
        }

        do {
            let receipt = try await repository.upload(
                file: file,
                pdfPassword: pdfPassword
            ) { [weak self] progress in
                await self?.updateProgress(for: file, progress: progress)
            }
            currentReceipt = receipt
            currentStatus = receipt.status
            guard !Task.isCancelled else {
                state = .selected(file)
                return
            }
            if apply(receipt: receipt, status: receipt.status) {
                return
            }
            try await poll(receipt: receipt)
        } catch is CancellationError {
            state = .selected(file)
        } catch let error as DocumentUploadRepositoryError {
            switch error {
            case .pdfPasswordRequired:
                state = .passwordRequired(file, invalid: false)
            case .invalidPDFPassword:
                state = .passwordRequired(file, invalid: true)
            default:
                state = .failed(file, errorKey: errorKey(for: error))
            }
        } catch {
            state = .failed(file, errorKey: "upload.error.unavailable")
        }
    }

    func reset() {
        currentFile = nil
        currentReceipt = nil
        currentStatus = nil
        state = .idle
    }

    func retry() async {
        guard !isBusy else {
            return
        }
        guard let receipt = currentReceipt else {
            await upload()
            return
        }

        state = .processing(receipt, status: currentStatus ?? receipt.status)
        do {
            let snapshot = try await repository.status(documentID: receipt.documentID)
            if !apply(receipt: receipt, status: snapshot.status) {
                try await poll(receipt: receipt)
            }
        } catch is CancellationError {
            state = .processing(receipt, status: currentStatus ?? receipt.status)
        } catch let error as DocumentUploadRepositoryError {
            state = .failed(currentFile, errorKey: errorKey(for: error))
        } catch {
            state = .failed(currentFile, errorKey: "upload.error.unavailable")
        }
    }

    private func poll(receipt: DocumentUploadReceipt) async throws {
        var attempt = 0
        var elapsedSeconds: UInt64 = 0

        while !Task.isCancelled {
            let delay = pollingPolicy.delaySeconds(forAttempt: attempt)
            guard elapsedSeconds <= pollingPolicy.timeoutSeconds - min(delay, pollingPolicy.timeoutSeconds) else {
                state = .failed(currentFile, errorKey: "upload.error.timeout")
                return
            }

            try await sleep(delay)
            elapsedSeconds += delay
            let snapshot = try await repository.status(documentID: receipt.documentID)
            if apply(receipt: receipt, status: snapshot.status) {
                return
            }
            attempt += 1
        }
        throw CancellationError()
    }

    private func apply(
        receipt: DocumentUploadReceipt,
        status: DocumentProcessingStatus
    ) -> Bool {
        currentStatus = status
        switch status {
        case .complete:
            state = .completed(receipt)
            return true
        case .duplicateReused:
            state = .duplicate(receipt)
            return true
        case .rejectedSecurity:
            state = .failed(currentFile, errorKey: "upload.error.rejected_security")
            return true
        case .validationFailed:
            state = .failed(currentFile, errorKey: "upload.error.validation_failed")
            return true
        case .unsupportedFormat:
            state = .failed(currentFile, errorKey: "upload.error.unsupported_format")
            return true
        case .reviewPending, .humanReview:
            state = .processing(receipt, status: status)
            return true
        default:
            state = .processing(receipt, status: status)
            return false
        }
    }

    private func updateProgress(for file: SelectedUploadFile, progress: Double) {
        guard case .uploading = state else {
            return
        }
        state = .uploading(file, progress: min(max(progress, 0), 1))
    }

    private func errorKey(for error: UploadFileValidationError) -> String {
        switch error {
        case .emptyFile:
            return "upload.error.empty"
        case .tooLarge:
            return "upload.error.too_large"
        case .unsupportedType:
            return "upload.error.unsupported_type"
        case .unreadable:
            return "upload.error.unreadable"
        }
    }

    private func errorKey(for error: DocumentUploadRepositoryError) -> String {
        switch error {
        case .rejectedSecurity:
            return "upload.error.rejected_security"
        case .validationFailed:
            return "upload.error.validation_failed"
        case .unsupportedFormat:
            return "upload.error.unsupported_format"
        case .pdfPasswordRequired, .invalidPDFPassword:
            return "upload.error.validation_failed"
        case .rateLimited:
            return "upload.error.rate_limited"
        case .serviceUnavailable:
            return "upload.error.unavailable"
        }
    }
}
