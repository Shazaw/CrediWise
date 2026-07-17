import SwiftUI

struct AssessmentDashboardView: View {
    @StateObject private var viewModel: AssessmentDashboardViewModel
    @State private var operationTask: Task<Void, Never>?
    @State private var isConfidenceDetailPresented = false

    init(viewModel: AssessmentDashboardViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel)
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
        .task { await viewModel.load() }
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
            SafeBorrowingCard(recommendation: report.safeBorrowing)
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
}
