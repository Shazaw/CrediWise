import SwiftUI

struct AssessmentDashboardView: View {
    @StateObject private var viewModel: AssessmentDashboardViewModel
    @StateObject private var shockViewModel: ShockViewModel
    @State private var operationTask: Task<Void, Never>?
    @State private var isConfidenceDetailPresented = false
    private let showsCompleteDashboard: Bool
    private let onOpenShocks: () -> Void
    private let onOpenOffers: () -> Void

    init(
        viewModel: AssessmentDashboardViewModel,
        shockViewModel: ShockViewModel,
        showsCompleteDashboard: Bool = false,
        onOpenShocks: @escaping () -> Void = {},
        onOpenOffers: @escaping () -> Void = {}
    ) {
        _viewModel = StateObject(wrappedValue: viewModel)
        _shockViewModel = StateObject(wrappedValue: shockViewModel)
        self.showsCompleteDashboard = showsCompleteDashboard
        self.onOpenShocks = onOpenShocks
        self.onOpenOffers = onOpenOffers
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
        .navigationTitle("dashboard.navigation_title")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await viewModel.load()
            if showsCompleteDashboard {
                await shockViewModel.load()
            }
        }
        .onDisappear { operationTask?.cancel() }
        .navigationDestination(isPresented: $isConfidenceDetailPresented) {
            if case let .loaded(report) = viewModel.state {
                DataConfidenceDetailView(report: report.dataConfidence)
            }
        }
        .accessibilityIdentifier("dashboard.screen")
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.small) {
            Text("dashboard.eyebrow")
                .font(TypographyTokens.caption.weight(.bold))
                .foregroundStyle(CrediWiseColors.primary)
            Text("dashboard.title")
                .font(TypographyTokens.title)
            Text("dashboard.subtitle")
                .font(TypographyTokens.body)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            ProgressView("dashboard.loading")
                .tint(CrediWiseColors.primary)
                .frame(maxWidth: .infinity)
                .padding(SpacingTokens.xxLarge)
        case let .loaded(report):
            DataConfidenceCard(report: report.dataConfidence) {
                isConfidenceDetailPresented = true
            }
            RiskBandCard(risk: report.risk)
            if let repaymentModel = report.repaymentModel {
                ExperimentalRepaymentModelCard(model: repaymentModel)
            }
            SafeBorrowingCard(recommendation: report.safeBorrowing)
            if showsCompleteDashboard {
                shockContent
                CTAButton(title: "dashboard.offers.action", action: onOpenOffers)
                    .accessibilityIdentifier("dashboard.offers.action")
            }
            DigitalTwinSummaryView(twin: report.twin)
            FinancialHealthPlanView(recommendations: report.recommendations)
            Text(
                String(
                    format: NSLocalizedString("dashboard.model_version", comment: "Model version"),
                    report.modelVersion
                )
            )
            .font(TypographyTokens.caption)
            .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.62))
        case let .failed(errorKey):
            VStack(alignment: .leading, spacing: SpacingTokens.medium) {
                Text("dashboard.error.title")
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

    @ViewBuilder
    private var shockContent: some View {
        switch shockViewModel.state {
        case .idle, .loading:
            ProgressView("shocks.loading")
                .tint(CrediWiseColors.primary)
                .frame(maxWidth: .infinity)
                .padding(SpacingTokens.large)
                .background(CrediWiseColors.surface)
                .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        case let .loaded(report):
            ShockResilienceCard(report: report, onOpen: onOpenShocks)
        case let .invalid(errorKey), let .failed(errorKey):
            VStack(alignment: .leading, spacing: SpacingTokens.small) {
                Text("shocks.card.title")
                    .font(TypographyTokens.cardTitle)
                Text(LocalizedStringKey(errorKey))
                    .font(TypographyTokens.caption)
                Button("common.retry") {
                    operationTask = Task { await shockViewModel.retry() }
                }
                .font(TypographyTokens.body.weight(.semibold))
            }
            .padding(SpacingTokens.large)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(CrediWiseColors.surface)
            .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        }
    }
}

private struct ExperimentalRepaymentModelCard: View {
    let model: AssessmentDashboard.RepaymentModel

    var body: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium) {
            HStack {
                Text("dashboard.ml.title")
                    .font(TypographyTokens.cardTitle)
                Spacer()
                Text("dashboard.ml.badge")
                    .font(TypographyTokens.caption.weight(.bold))
                    .foregroundStyle(CrediWiseColors.primary)
                    .padding(.horizontal, SpacingTokens.small)
                    .padding(.vertical, 4)
                    .background(CrediWiseColors.primary.opacity(0.12))
                    .clipShape(Capsule())
            }
            switch model.status {
            case .complete:
                if let probability = model.adverseOutcomeProbability {
                    Text(
                        String(
                            format: NSLocalizedString(
                                "dashboard.ml.probability",
                                comment: "Experimental adverse outcome estimate"
                            ),
                            Int((probability * 100).rounded())
                        )
                    )
                    .font(TypographyTokens.title)
                }
                Text("dashboard.ml.low_confidence")
                    .font(TypographyTokens.caption.weight(.semibold))
                    .foregroundStyle(CrediWiseColors.warning)
            case .ineligible:
                Text("dashboard.ml.ineligible")
                    .font(TypographyTokens.body)
            case .unavailable:
                Text("dashboard.ml.unavailable")
                    .font(TypographyTokens.body)
            }
            Text("dashboard.ml.scope")
                .font(TypographyTokens.caption)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
            Text("dashboard.ml.notice")
                .font(TypographyTokens.caption)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.62))
        }
        .padding(SpacingTokens.large)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("dashboard.ml.card")
    }
}
