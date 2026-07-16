import Foundation
import SwiftUI

struct ExtractionReviewView: View {
    @StateObject private var viewModel: ExtractionReviewViewModel
    @State private var operationTask: Task<Void, Never>?
    @AccessibilityFocusState private var isResultFocused: Bool

    let onConfirmed: (String) -> Void

    init(
        viewModel: ExtractionReviewViewModel,
        onConfirmed: @escaping (String) -> Void
    ) {
        _viewModel = StateObject(wrappedValue: viewModel)
        self.onConfirmed = onConfirmed
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
        .navigationTitle("review.navigation_title")
        .navigationBarTitleDisplayMode(.inline)
        .task { await viewModel.load() }
        .onDisappear { operationTask?.cancel() }
        .accessibilityIdentifier("review.screen")
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.small) {
            Text("review.eyebrow")
                .font(TypographyTokens.caption.weight(.bold))
                .foregroundStyle(CrediWiseColors.primary)
            Text("review.title")
                .font(TypographyTokens.title)
                .foregroundStyle(CrediWiseColors.textPrimary)
                .accessibilityIdentifier("review.title")
            Text("review.subtitle")
                .font(TypographyTokens.body)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            ProgressView("review.loading")
                .tint(CrediWiseColors.primary)
                .frame(maxWidth: .infinity)
                .padding(SpacingTokens.xxLarge)
        case let .loaded(ready):
            readyContent(ready, isConfirming: false)
        case let .confirming(ready):
            readyContent(ready, isConfirming: true)
        case let .confirmed(documentID):
            confirmedContent(documentID: documentID)
        case let .failed(_, errorKey):
            errorContent(errorKey: errorKey)
        }
    }

    private func readyContent(
        _ ready: ExtractionReviewViewState.Ready,
        isConfirming: Bool
    ) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.large) {
            reviewSummary(ready)

            ForEach(ready.review.transactions) { transaction in
                ExtractionTransactionCard(
                    transaction: transaction,
                    correction: ready.correction(for: transaction.id),
                    onDateChange: { viewModel.proposeDate($0, for: transaction.id) },
                    onDescriptionChange: { viewModel.proposeDescription($0, for: transaction.id) },
                    onAmountChange: { viewModel.proposeAmount($0, for: transaction.id) },
                    onCategoryChange: { viewModel.proposeCategory($0, for: transaction.id) },
                    onInternalTransferChange: { viewModel.proposeInternalTransfer($0, for: transaction.id) },
                    onDuplicateChange: { viewModel.proposeDuplicate($0, for: transaction.id) },
                    onValidityChange: { viewModel.setTransactionInputValid($0, for: transaction.id) }
                )
                .disabled(isConfirming)
            }

            confirmationCard(ready, isConfirming: isConfirming)
        }
    }

    private func reviewSummary(_ ready: ExtractionReviewViewState.Ready) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium) {
            Text(verbatim: ready.review.fileName)
                .font(TypographyTokens.cardTitle)
                .foregroundStyle(CrediWiseColors.textPrimary)
            LabeledContent("review.owner.raw", value: ready.review.accountOwner.raw)
            LabeledContent("review.owner.normalized", value: ready.review.accountOwner.normalized)
            LabeledContent("review.period", value: ready.review.periodLabel)
            Text(
                String(
                    format: NSLocalizedString("review.corrections.count", comment: "Correction count"),
                    ready.corrections.count
                )
            )
            .font(TypographyTokens.caption.weight(.semibold))
            .foregroundStyle(CrediWiseColors.primary)
            .accessibilityIdentifier("review.correction_count")
        }
        .padding(SpacingTokens.large)
        .background(CrediWiseColors.primaryTint)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
    }

    private func confirmationCard(
        _ ready: ExtractionReviewViewState.Ready,
        isConfirming: Bool
    ) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.standard) {
            Text("review.confirmation.title")
                .font(TypographyTokens.cardTitle)
            Text("review.confirmation.detail")
                .font(TypographyTokens.body)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))

            Toggle(
                "review.confirmation.ownership",
                isOn: Binding(
                    get: { ready.confirmsOwnership },
                    set: viewModel.setOwnershipConfirmed
                )
            )
            .accessibilityIdentifier("review.ownership")

            Toggle(
                "review.confirmation.ownership_concern",
                isOn: Binding(
                    get: { ready.reportsOwnershipConcern },
                    set: viewModel.setReportsOwnershipConcern
                )
            )
            .accessibilityIdentifier("review.ownership_concern")

            Toggle(
                "review.confirmation.missing_rows",
                isOn: Binding(
                    get: { ready.reportsMissingRows },
                    set: viewModel.setReportsMissingRows
                )
            )
            .accessibilityIdentifier("review.missing_rows")

            if isConfirming {
                ProgressView("review.confirmation.loading")
                    .frame(maxWidth: .infinity)
            } else {
                if !ready.invalidTransactionIDs.isEmpty {
                    Text("review.confirmation.invalid_fields")
                        .font(TypographyTokens.caption)
                        .foregroundStyle(CrediWiseColors.danger)
                }
                CTAButton(title: "review.confirmation.action") {
                    operationTask = Task { await viewModel.confirm() }
                }
                .disabled(!ready.canConfirm)
                .accessibilityIdentifier("review.confirm")
            }
        }
        .padding(SpacingTokens.large)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
    }

    private func confirmedContent(documentID: String) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.standard) {
            Image(systemName: "checkmark.seal.fill")
                .font(.system(size: 42, weight: .bold))
                .foregroundStyle(CrediWiseColors.success)
                .accessibilityHidden(true)
            Text("review.confirmed.title")
                .font(TypographyTokens.title)
                .accessibilityFocused($isResultFocused)
            Text("review.confirmed.detail")
                .font(TypographyTokens.body)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
            CTAButton(title: "review.confirmed.action") {
                onConfirmed(documentID)
            }
            .accessibilityIdentifier("review.show_confidence")
        }
        .padding(SpacingTokens.large)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        .onAppear { isResultFocused = true }
    }

    private func errorContent(errorKey: String) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.standard) {
            Image(systemName: "arrow.triangle.2.circlepath.circle.fill")
                .font(.system(size: 38, weight: .bold))
                .foregroundStyle(CrediWiseColors.primary)
                .accessibilityHidden(true)
            Text("review.error.title")
                .font(TypographyTokens.cardTitle)
            Text(LocalizedStringKey(errorKey))
                .font(TypographyTokens.body)
            PrimaryButton(title: "common.retry") {
                operationTask = Task { await viewModel.retry() }
            }
        }
        .padding(SpacingTokens.large)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
    }
}
