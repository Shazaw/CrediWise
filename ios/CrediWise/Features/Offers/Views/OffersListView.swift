import SwiftUI

struct OffersListView: View {
    @StateObject private var viewModel: OffersViewModel
    @State private var operationTask: Task<Void, Never>?
    let onOpenOffer: (String) -> Void

    init(viewModel: OffersViewModel, onOpenOffer: @escaping (String) -> Void) {
        _viewModel = StateObject(wrappedValue: viewModel)
        self.onOpenOffer = onOpenOffer
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
        .navigationTitle("offers.navigation_title")
        .navigationBarTitleDisplayMode(.inline)
        .task { await viewModel.load() }
        .onDisappear { operationTask?.cancel() }
        .accessibilityIdentifier("offers.screen")
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.small) {
            Text("offers.eyebrow")
                .font(TypographyTokens.caption.weight(.bold))
                .foregroundStyle(CrediWiseColors.primary)
            Text("offers.title")
                .font(TypographyTokens.title)
            Text("offers.subtitle")
                .font(TypographyTokens.body)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
            Label("offers.ranking_notice", systemImage: "shield.lefthalf.filled")
                .font(TypographyTokens.caption.weight(.semibold))
                .foregroundStyle(CrediWiseColors.primary)
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            ProgressView("offers.loading")
                .tint(CrediWiseColors.primary)
                .frame(maxWidth: .infinity)
                .padding(SpacingTokens.xxLarge)
        case let .loaded(offers):
            if offers.isEmpty {
                Text("offers.empty")
                    .font(TypographyTokens.body)
            } else {
                ForEach(offers, id: \.offerID) { offer in
                    OfferRow(offer: offer) {
                        onOpenOffer(offer.offerID)
                    }
                }
            }
        case let .failed(errorKey):
            VStack(alignment: .leading, spacing: SpacingTokens.medium) {
                Text("offers.error.title")
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
