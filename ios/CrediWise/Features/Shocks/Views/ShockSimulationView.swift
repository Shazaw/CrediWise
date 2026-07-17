import SwiftUI

struct ShockSimulationView: View {
    @StateObject private var viewModel: ShockViewModel
    @State private var selectedScenarioID: String?
    @State private var operationTask: Task<Void, Never>?

    init(viewModel: ShockViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel)
    }

    var body: some View {
        ZStack {
            CrediWiseColors.surfaceAlt.ignoresSafeArea()
            ScrollView {
                VStack(alignment: .leading, spacing: SpacingTokens.large) {
                    header
                    controls
                    content
                    DisclaimerFooter()
                }
                .padding(SpacingTokens.large)
            }
        }
        .navigationTitle("shocks.navigation_title")
        .navigationBarTitleDisplayMode(.inline)
        .task { await viewModel.load() }
        .onDisappear { operationTask?.cancel() }
        .accessibilityIdentifier("shocks.screen")
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.small) {
            Text("shocks.eyebrow")
                .font(TypographyTokens.caption.weight(.bold))
                .foregroundStyle(CrediWiseColors.primary)
            Text("shocks.title")
                .font(TypographyTokens.title)
            Text("shocks.subtitle")
                .font(TypographyTokens.body)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
        }
    }

    private var controls: some View {
        VStack(spacing: SpacingTokens.medium) {
            ShockSlider(
                title: "shocks.controls.income_drop",
                valueText: "\(Int(viewModel.incomeDropPercentage.rounded()))%",
                value: $viewModel.incomeDropPercentage,
                range: 0...100,
                step: 5
            )
            .accessibilityIdentifier("shocks.income_drop")

            ShockSlider(
                title: "shocks.controls.emergency_expense",
                valueText: IDRFormatter.string(from: Int64(viewModel.emergencyExpense.rounded())),
                value: $viewModel.emergencyExpense,
                range: 0...5_000_000,
                step: 100_000
            )
            .accessibilityIdentifier("shocks.emergency_expense")

            LabeledContent("shocks.controls.proposed_instalment") {
                TextField(
                    "shocks.controls.proposed_instalment",
                    value: $viewModel.proposedInstalment,
                    format: .number
                )
                .keyboardType(.numberPad)
                .multilineTextAlignment(.trailing)
                .accessibilityIdentifier("shocks.proposed_instalment")
            }

            CTAButton(title: "shocks.controls.simulate") {
                operationTask?.cancel()
                operationTask = Task { await viewModel.simulate() }
            }
            .disabled(viewModel.state == .loading)
            .accessibilityIdentifier("shocks.simulate")
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            ProgressView("shocks.loading")
                .tint(CrediWiseColors.primary)
                .frame(maxWidth: .infinity)
                .padding(SpacingTokens.xxLarge)
        case let .loaded(report):
            reportContent(report)
        case let .invalid(errorKey):
            validationErrorContent(errorKey)
        case let .failed(errorKey):
            serviceErrorContent(errorKey)
        }
    }

    private func reportContent(_ report: ShockAssessment) -> some View {
        let selected = report.scenarios.first(where: { $0.id == selectedScenarioID }) ?? report.scenarios.first
        return VStack(alignment: .leading, spacing: SpacingTokens.large) {
            ShockResilienceCard(report: report, onOpen: nil)

            Text(LocalizedStringKey("shocks.score_scope.\(report.resilienceScoreScope.rawValue)"))
                .font(TypographyTokens.caption)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))

            if let parameters = report.submittedParameters {
                Text(
                    String(
                        format: NSLocalizedString("shocks.applied_parameters", comment: "Applied shock parameters"),
                        parameters.incomeDropPercentage,
                        IDRFormatter.string(from: parameters.emergencyExpense),
                        IDRFormatter.string(from: parameters.proposedInstalment)
                    )
                )
                .font(TypographyTokens.caption)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
            }

            Text("shocks.scenarios.title")
                .font(TypographyTokens.cardTitle)

            ForEach(report.scenarios) { scenario in
                Button {
                    selectedScenarioID = scenario.id
                } label: {
                    scenarioRow(scenario, isSelected: selected?.id == scenario.id)
                }
                .buttonStyle(.plain)
            }

            if let selected {
                ShockProjectionChart(scenario: selected)
            }

            reasonsSection(report.reasons)
            explanationSection()
            modelVersion(report.modelVersion)
        }
    }

    private func reasonsSection(_ reasons: [ShockAssessment.Reason]) -> some View {
        ForEach(reasons) { reason in
            VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                Text(LocalizedStringKey(reason.titleKey))
                    .font(TypographyTokens.body.weight(.semibold))
                if !reason.isKnown {
                    Text(
                        String(
                            format: NSLocalizedString(
                                "shocks.reason.unknown_code",
                                comment: "Unknown shock reason code"
                            ),
                            reason.code
                        )
                    )
                    .font(TypographyTokens.caption.monospaced())
                }
                if let detailKey = reason.detailKey {
                    Text(LocalizedStringKey(detailKey))
                        .font(TypographyTokens.caption)
                        .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
                } else {
                    Text(verbatim: reason.description)
                        .font(TypographyTokens.caption)
                        .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
                }
            }
        }
    }

    private func explanationSection() -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
            Text("shocks.explanation.title")
                .font(TypographyTokens.cardTitle)
            Text("shocks.explanation.context")
                .font(TypographyTokens.caption)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
            Text("shocks.explanation.summary")
                .font(TypographyTokens.body)
        }
    }

    private func modelVersion(_ version: String) -> some View {
        Text(
            String(
                format: NSLocalizedString("shocks.model_version", comment: "Shock model version"),
                version
            )
        )
        .font(TypographyTokens.caption)
        .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.62))
    }

    private func scenarioRow(_ scenario: ShockAssessment.Scenario, isSelected: Bool) -> some View {
        HStack(spacing: SpacingTokens.medium) {
            Image(systemName: statusIcon(scenario.status))
                .foregroundStyle(statusColor(scenario.status))
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                Text(LocalizedStringKey("shocks.scenario.\(scenario.kind.rawValue).title"))
                    .font(TypographyTokens.body.weight(.semibold))
                Text(LocalizedStringKey("shocks.status.\(scenario.status.rawValue)"))
                    .font(TypographyTokens.caption)
                    .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
            }
            Spacer()
            Text(verbatim: IDRFormatter.string(from: scenario.minimumProjectedBalance))
                .font(TypographyTokens.caption.monospacedDigit().weight(.bold))
            Text(
                String(
                    format: NSLocalizedString("shocks.scenario.contribution", comment: "Score contribution"),
                    NSDecimalNumber(decimal: scenario.resilienceScoreContribution).doubleValue
                )
            )
            .font(TypographyTokens.caption)
        }
        .padding(SpacingTokens.standard)
        .background(isSelected ? CrediWiseColors.primaryTint : CrediWiseColors.surface)
        .overlay {
            RoundedRectangle(cornerRadius: RadiusTokens.button)
                .stroke(isSelected ? CrediWiseColors.primary : Color.clear, lineWidth: 2)
        }
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.button))
    }

    private func validationErrorContent(_ errorKey: String) -> some View {
        Text(LocalizedStringKey(errorKey))
            .font(TypographyTokens.body)
            .foregroundStyle(CrediWiseColors.danger)
            .padding(SpacingTokens.standard)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(CrediWiseColors.danger.opacity(0.08))
            .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.button))
    }

    private func serviceErrorContent(_ errorKey: String) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium) {
            Text("shocks.error.title")
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

    private func statusColor(_ status: ShockAssessment.AffordabilityStatus) -> Color {
        switch status {
        case .survivable: return CrediWiseColors.success
        case .strained: return CrediWiseColors.warning
        case .deficit: return CrediWiseColors.danger
        }
    }

    private func statusIcon(_ status: ShockAssessment.AffordabilityStatus) -> String {
        switch status {
        case .survivable: return "checkmark.shield.fill"
        case .strained: return "exclamationmark.triangle.fill"
        case .deficit: return "xmark.octagon.fill"
        }
    }
}
