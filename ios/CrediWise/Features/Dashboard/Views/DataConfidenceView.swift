import SwiftUI

struct DataConfidenceView: View {
    @StateObject private var viewModel: DataConfidenceViewModel
    @State private var operationTask: Task<Void, Never>?
    @State private var isDetailPresented = false

    init(viewModel: DataConfidenceViewModel) {
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
        .navigationTitle("confidence.navigation_title")
        .navigationBarTitleDisplayMode(.inline)
        .task { await viewModel.load() }
        .onDisappear { operationTask?.cancel() }
        .navigationDestination(isPresented: $isDetailPresented) {
            if case let .loaded(report) = viewModel.state {
                DataConfidenceDetailView(report: report)
            }
        }
        .accessibilityIdentifier("confidence.screen")
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.small) {
            Text("confidence.eyebrow")
                .font(TypographyTokens.caption.weight(.bold))
                .foregroundStyle(CrediWiseColors.primary)
            Text("confidence.title")
                .font(TypographyTokens.title)
            Text("confidence.subtitle")
                .font(TypographyTokens.body)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            ProgressView("confidence.loading")
                .tint(CrediWiseColors.primary)
                .frame(maxWidth: .infinity)
                .padding(SpacingTokens.xxLarge)
        case let .loaded(report):
            DataConfidenceCard(report: report) {
                isDetailPresented = true
            }

            VStack(alignment: .leading, spacing: SpacingTokens.medium) {
                Text("confidence.next.title")
                    .font(TypographyTokens.cardTitle)
                Text(LocalizedStringKey(report.recommendationKey))
                    .font(TypographyTokens.body)
                    .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
            }
            .padding(SpacingTokens.large)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(CrediWiseColors.surface)
            .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        case let .failed(errorKey):
            VStack(alignment: .leading, spacing: SpacingTokens.standard) {
                Text("confidence.error.title")
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
