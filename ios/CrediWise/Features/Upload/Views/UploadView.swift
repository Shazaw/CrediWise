import Foundation
import SwiftUI
import UniformTypeIdentifiers

struct UploadView: View {
    @StateObject private var viewModel: UploadViewModel
    @State private var isFileImporterPresented = false
    @State private var pdfPassword = ""
    @State private var operationTask: Task<Void, Never>?
    @AccessibilityFocusState private var isResultFocused: Bool

    let allowsSyntheticSelection: Bool
    let isServiceAvailable: Bool
    let onReviewReady: (String) -> Void

    init(
        viewModel: UploadViewModel,
        allowsSyntheticSelection: Bool = false,
        isServiceAvailable: Bool = true,
        onReviewReady: @escaping (String) -> Void = { _ in }
    ) {
        _viewModel = StateObject(wrappedValue: viewModel)
        self.allowsSyntheticSelection = allowsSyntheticSelection
        self.isServiceAvailable = isServiceAvailable
        self.onReviewReady = onReviewReady
    }

    var body: some View {
        ZStack {
            CrediWiseColors.surfaceAlt.ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: SpacingTokens.large) {
                    header
                    content
                    DisclaimerFooter()
                }
                .padding(SpacingTokens.large)
            }
        }
        .navigationTitle("upload.navigation_title")
        .navigationBarTitleDisplayMode(.inline)
        .onDisappear {
            operationTask?.cancel()
        }
        .onChange(of: viewModel.state) { state in
            switch state {
            case .completed, .duplicate, .failed:
                isResultFocused = true
            default:
                break
            }
        }
        .fileImporter(
            isPresented: $isFileImporterPresented,
            allowedContentTypes: [.pdf, .commaSeparatedText, .png, .jpeg],
            allowsMultipleSelection: false,
            onCompletion: handleSelection
        )
        .accessibilityIdentifier("upload.screen")
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium) {
            ZStack {
                RoundedRectangle(cornerRadius: RadiusTokens.card)
                    .fill(CrediWiseColors.primary)
                    .frame(minHeight: 128)

                HStack(spacing: SpacingTokens.standard) {
                    Image(systemName: "doc.badge.arrow.up.fill")
                        .font(.system(size: 44, weight: .bold))
                        .foregroundStyle(CrediWiseColors.accent)
                        .accessibilityHidden(true)

                    VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                        Text("upload.eyebrow")
                            .font(TypographyTokens.caption.weight(.bold))
                            .foregroundStyle(CrediWiseColors.accent)

                        Text("upload.title")
                            .font(TypographyTokens.cardTitle)
                            .foregroundStyle(CrediWiseColors.textOnPrimary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                .padding(SpacingTokens.large)
            }

            Text("upload.subtitle")
                .font(TypographyTokens.body)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle:
            if isServiceAvailable {
                pickerCard
            } else {
                UploadResultCard(
                    icon: "network.slash",
                    titleKey: "upload.unavailable.title",
                    detailKey: "upload.error.unavailable",
                    color: CrediWiseColors.primary
                )
            }
        case let .selected(file):
            UploadFileCard(file: file, progress: nil)
            if file.requiresImageSourceSelection {
                UploadSourcePickerCard(
                    sourceType: file.sourceType,
                    onSelect: viewModel.selectImageSourceType
                )
            }
            CTAButton(title: "upload.action.upload") {
                startOperation { await viewModel.upload() }
            }
            .disabled(file.sourceType == nil)
            .accessibilityIdentifier("upload.submit")
            chooseDifferentFileButton
        case let .passwordRequired(file, invalid):
            UploadFileCard(file: file, progress: nil)
            UploadPasswordCard(password: $pdfPassword, invalid: invalid) { password in
                startOperation { await viewModel.upload(pdfPassword: password) }
            }
        case let .uploading(file, progress):
            UploadFileCard(file: file, progress: progress)
        case let .processing(receipt, status):
            statusBanner(receipt: receipt, status: status)
            ProcessingChecklist(status: status)
            if status == .reviewPending {
                CTAButton(title: "upload.action.review") {
                    onReviewReady(receipt.documentID)
                }
                .accessibilityIdentifier("upload.review")
            } else if status == .humanReview {
                PrimaryButton(title: "upload.action.check_status") {
                    startOperation { await viewModel.retry() }
                }
                .accessibilityIdentifier("upload.check_status")
            }
        case let .completed(receipt):
            UploadResultCard(
                icon: "checkmark.shield.fill",
                titleKey: "upload.complete.title",
                detailKey: "upload.complete.detail",
                color: CrediWiseColors.success,
                fileName: receipt.fileName
            )
            .accessibilityFocused($isResultFocused)
            .accessibilityIdentifier("upload.completion")
            ProcessingChecklist(status: .complete)
            uploadAnotherButton
        case let .duplicate(receipt):
            UploadResultCard(
                icon: "doc.on.doc.fill",
                titleKey: "upload.duplicate.title",
                detailKey: "upload.duplicate.detail",
                color: CrediWiseColors.primary,
                fileName: receipt.fileName
            )
            .accessibilityFocused($isResultFocused)
            uploadAnotherButton
        case let .failed(file, errorKey):
            UploadResultCard(
                icon: "exclamationmark.shield.fill",
                titleKey: "upload.error.title",
                detailKey: errorKey,
                color: CrediWiseColors.danger,
                fileName: file?.fileName
            )
            .accessibilityFocused($isResultFocused)
            if file != nil, isRetryable(errorKey) {
                PrimaryButton(title: "common.retry") {
                    startOperation { await viewModel.retry() }
                }
                .accessibilityIdentifier("upload.retry")
            }
            uploadAnotherButton
        }
    }

    private var pickerCard: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.standard) {
            Image(systemName: "lock.doc.fill")
                .font(.system(size: 34, weight: .semibold))
                .foregroundStyle(CrediWiseColors.primary)
                .accessibilityHidden(true)

            Text("upload.picker.title")
                .font(TypographyTokens.cardTitle)
                .foregroundStyle(CrediWiseColors.textPrimary)

            Text("upload.picker.detail")
                .font(TypographyTokens.body)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.7))

            Label("upload.picker.formats", systemImage: "checkmark.circle.fill")
                .font(TypographyTokens.caption)
                .foregroundStyle(CrediWiseColors.textPrimary)

            Label("upload.picker.size", systemImage: "checkmark.circle.fill")
                .font(TypographyTokens.caption)
                .foregroundStyle(CrediWiseColors.textPrimary)

            CTAButton(title: "upload.action.choose_file") {
                isFileImporterPresented = true
            }
            .accessibilityIdentifier("upload.choose_file")

            if allowsSyntheticSelection {
                Button("upload.action.synthetic_fixture") {
                    viewModel.selectSyntheticFile()
                }
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(CrediWiseColors.primary)
                .frame(maxWidth: .infinity)
                .accessibilityIdentifier("upload.synthetic_fixture")
            }
        }
        .padding(SpacingTokens.large)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
    }

    private func statusBanner(
        receipt: DocumentUploadReceipt,
        status: DocumentProcessingStatus
    ) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.small) {
            Text(verbatim: receipt.fileName)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(CrediWiseColors.textPrimary)

            Text(LocalizedStringKey(statusKey(status)))
                .font(TypographyTokens.cardTitle)
                .foregroundStyle(CrediWiseColors.primary)
                .accessibilityIdentifier("upload.processing.status")

            if status != .reviewPending, status != .humanReview {
                ProgressView()
                    .tint(CrediWiseColors.primary)
                    .accessibilityLabel(Text("upload.processing.accessibility_label"))
            }
        }
        .padding(SpacingTokens.large)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(CrediWiseColors.primaryTint)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
    }

    private var chooseDifferentFileButton: some View {
        Button("upload.action.choose_different") {
            pdfPassword = ""
            isFileImporterPresented = true
        }
        .font(.subheadline.weight(.semibold))
        .foregroundStyle(CrediWiseColors.primary)
        .frame(maxWidth: .infinity)
    }

    private var uploadAnotherButton: some View {
        PrimaryButton(title: "upload.action.another") {
            pdfPassword = ""
            viewModel.reset()
        }
        .accessibilityIdentifier("upload.another")
    }

    private func handleSelection(_ result: Result<[URL], Error>) {
        switch result {
        case let .success(urls):
            guard let url = urls.first else {
                viewModel.handlePickerFailure()
                return
            }
            viewModel.selectFile(at: url)
        case let .failure(error):
            if (error as NSError).code == NSUserCancelledError {
                return
            }
            viewModel.handlePickerFailure()
        }
    }

    private func statusKey(_ status: DocumentProcessingStatus) -> String {
        switch status {
        case .uploaded:
            return "upload.status.uploaded"
        case .securityCheck:
            return "upload.status.security_check"
        case .extracting:
            return "upload.status.extracting"
        case .verifying:
            return "upload.status.verifying"
        case .reviewPending:
            return "upload.status.review_pending"
        case .normalizing:
            return "upload.status.normalizing"
        case .analyzing:
            return "upload.status.analyzing"
        case .humanReview:
            return "upload.status.human_review"
        case .complete:
            return "upload.status.complete"
        case .rejectedSecurity, .validationFailed, .duplicateReused, .unsupportedFormat:
            return "upload.status.finished"
        }
    }

    private func isRetryable(_ errorKey: String) -> Bool {
        [
            "upload.error.rate_limited",
            "upload.error.timeout",
            "upload.error.unavailable"
        ].contains(errorKey)
    }

    private func startOperation(_ operation: @escaping @MainActor () async -> Void) {
        operationTask?.cancel()
        operationTask = Task { await operation() }
    }
}
