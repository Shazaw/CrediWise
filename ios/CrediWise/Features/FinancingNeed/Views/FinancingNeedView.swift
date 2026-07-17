import SwiftUI

struct FinancingNeedView: View {
    @StateObject private var viewModel: FinancingNeedViewModel
    @State private var submissionTask: Task<Void, Never>?

    let onSaved: (FinancingNeedReceipt) -> Void

    init(
        viewModel: FinancingNeedViewModel,
        onSaved: @escaping (FinancingNeedReceipt) -> Void
    ) {
        _viewModel = StateObject(wrappedValue: viewModel)
        self.onSaved = onSaved
    }

    var body: some View {
        ZStack {
            CrediWiseColors.surfaceAlt.ignoresSafeArea()
            ScrollView {
                VStack(alignment: .leading, spacing: SpacingTokens.large) {
                    header
                    amountCard
                    purposeCard
                    tenorCard
                    notesCard
                    submissionContent
                    DisclaimerFooter()
                }
                .padding(SpacingTokens.large)
            }
        }
        .navigationTitle("financing_need.navigation_title")
        .navigationBarTitleDisplayMode(.inline)
        .onDisappear { submissionTask?.cancel() }
        .accessibilityIdentifier("financing_need.screen")
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.small) {
            Text("financing_need.eyebrow")
                .font(TypographyTokens.caption.weight(.bold))
                .foregroundStyle(CrediWiseColors.primary)
            Text("financing_need.title")
                .font(TypographyTokens.title)
                .foregroundStyle(CrediWiseColors.textPrimary)
            Text("financing_need.subtitle")
                .font(TypographyTokens.body)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
        }
    }

    private var amountCard: some View {
        formCard {
            Text("financing_need.amount.title")
                .font(TypographyTokens.cardTitle)
            TextField(
                "financing_need.amount.placeholder",
                text: Binding(
                    get: { viewModel.amountText },
                    set: viewModel.setAmountText
                )
            )
            .keyboardType(.numberPad)
            .textFieldStyle(.roundedBorder)
            .accessibilityIdentifier("financing_need.amount")

            if let formattedAmount = viewModel.formattedAmount, viewModel.isAmountValid {
                Text(verbatim: formattedAmount)
                    .font(TypographyTokens.title.monospacedDigit())
                    .foregroundStyle(CrediWiseColors.primary)
            }
            if viewModel.hasAttemptedSubmission, !viewModel.isAmountValid {
                validationText("financing_need.validation.amount")
            }
        }
    }

    private var purposeCard: some View {
        formCard {
            Text("financing_need.purpose.title")
                .font(TypographyTokens.cardTitle)
            Menu {
                ForEach(FinancingNeed.Purpose.allCases, id: \.self) { purpose in
                    Button(LocalizedStringKey(purpose.titleKey)) {
                        viewModel.setPurpose(purpose)
                    }
                    .accessibilityIdentifier("financing_need.purpose.\(purpose.rawValue)")
                }
            } label: {
                HStack {
                    Text(LocalizedStringKey(viewModel.purpose?.titleKey ?? "financing_need.purpose.placeholder"))
                    Spacer()
                    Image(systemName: "chevron.up.chevron.down")
                        .accessibilityHidden(true)
                }
                .foregroundStyle(CrediWiseColors.textPrimary)
                .padding(SpacingTokens.standard)
                .background(CrediWiseColors.primaryTint)
                .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.button))
            }
            .accessibilityIdentifier("financing_need.purpose")
            if viewModel.hasAttemptedSubmission, viewModel.purpose == nil {
                validationText("financing_need.validation.purpose")
            }
        }
    }

    private var tenorCard: some View {
        formCard {
            Text("financing_need.tenor.title")
                .font(TypographyTokens.cardTitle)
            Stepper(value: $viewModel.preferredTenorMonths, in: 1...36) {
                Text(
                    String(
                        format: NSLocalizedString("financing_need.tenor.value", comment: "Tenor months"),
                        viewModel.preferredTenorMonths
                    )
                )
                .font(TypographyTokens.body.weight(.semibold))
            }
            .accessibilityIdentifier("financing_need.tenor")
        }
    }

    private var notesCard: some View {
        formCard {
            Text("financing_need.notes.title")
                .font(TypographyTokens.cardTitle)
            TextField("financing_need.notes.placeholder", text: $viewModel.notes, axis: .vertical)
                .lineLimit(3...6)
                .textFieldStyle(.roundedBorder)
                .accessibilityIdentifier("financing_need.notes")
        }
    }

    @ViewBuilder
    private var submissionContent: some View {
        if case let .failed(errorKey) = viewModel.state {
            formCard {
                Text("financing_need.error.title")
                    .font(TypographyTokens.cardTitle)
                Text(LocalizedStringKey(errorKey))
                    .font(TypographyTokens.body)
                PrimaryButton(title: "common.retry", action: viewModel.retry)
            }
        }

        CTAButton(title: actionTitle) {
            submissionTask = Task {
                if let receipt = await viewModel.submit() {
                    onSaved(receipt)
                }
            }
        }
        .disabled(!viewModel.canSubmit)
        .accessibilityIdentifier("financing_need.submit")
    }

    private var actionTitle: LocalizedStringKey {
        viewModel.state == .submitting
            ? "financing_need.action.submitting"
            : "financing_need.action.continue"
    }

    private func formCard<Content: View>(
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium, content: content)
            .padding(SpacingTokens.large)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(CrediWiseColors.surface)
            .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
    }

    private func validationText(_ key: LocalizedStringKey) -> some View {
        Text(key)
            .font(TypographyTokens.caption)
            .foregroundStyle(CrediWiseColors.danger)
            .accessibilityIdentifier("financing_need.validation")
    }
}
