import SwiftUI

struct AppRootView: View {
    @ObservedObject var coordinator: AppCoordinator
    @ObservedObject private var sessionManager: SessionManager
    @State private var selectedTab = AuthenticatedTab.home

    init(coordinator: AppCoordinator) {
        self.coordinator = coordinator
        _sessionManager = ObservedObject(wrappedValue: coordinator.sessionManager)
    }

    var body: some View {
        Group {
            switch sessionManager.state {
            case .restoring:
                ProgressView("session.restoring")
                    .tint(CrediWiseColors.primary)
            case .restorationFailed:
                restorationError
            case .signedOut:
                unauthenticatedFlow
            case .signedIn:
                authenticatedFlow
            }
        }
        .tint(CrediWiseColors.primary)
        .task {
            await sessionManager.restore()
        }
        .onChange(of: sessionManager.state) { state in
            if state != .signedIn {
                selectedTab = .home
            }
        }
    }

    private var restorationError: some View {
        VStack(spacing: SpacingTokens.large) {
            Image(systemName: "key.slash.fill")
                .font(.system(size: 42, weight: .bold))
                .foregroundStyle(CrediWiseColors.primary)
                .accessibilityHidden(true)

            Text("session.restoration_error")
                .font(TypographyTokens.body)
                .multilineTextAlignment(.center)

            PrimaryButton(title: "common.retry") {
                Task { await sessionManager.retryRestoration() }
            }
        }
        .padding(SpacingTokens.xLarge)
    }

    private var unauthenticatedFlow: some View {
        NavigationStack(path: $coordinator.path) {
            WelcomeView(
                onCreateAccount: coordinator.showRegistration,
                onSignIn: coordinator.showSignIn
            )
            .navigationDestination(for: AppRoute.self) { route in
                destination(for: route)
            }
        }
    }

    private var authenticatedFlow: some View {
        TabView(selection: $selectedTab) {
            NavigationStack(path: $coordinator.path) {
                AuthenticatedHomeView(
                    onStart: startAuthenticatedFlow,
                    showsCycle5Preview: coordinator.shouldOfferSyntheticAssessment
                )
                .navigationDestination(for: AppRoute.self) { route in
                    destination(for: route)
                }
            }
            .tabItem { Label("shell.tab.home", systemImage: "house.fill") }
            .tag(AuthenticatedTab.home)

            shellPlaceholder(
                icon: "doc.text.magnifyingglass",
                eyebrow: "shell.records.eyebrow",
                title: "shell.records.title",
                detail: "shell.records.detail",
                identifier: "shell.records"
            )
            .tabItem { Label("shell.tab.records", systemImage: "folder.fill") }
            .tag(AuthenticatedTab.records)

            shellPlaceholder(
                icon: "chart.bar.xaxis",
                eyebrow: "shell.assessment.eyebrow",
                title: "shell.assessment.title",
                detail: "shell.assessment.detail",
                identifier: "shell.assessment"
            )
            .tabItem { Label("shell.tab.assessment", systemImage: "chart.bar.fill") }
            .tag(AuthenticatedTab.assessment)

            shellPlaceholder(
                icon: "arrow.left.arrow.right.circle.fill",
                eyebrow: "shell.offers.eyebrow",
                title: "shell.offers.title",
                detail: "shell.offers.detail",
                identifier: "shell.offers"
            )
            .tabItem { Label("shell.tab.offers", systemImage: "rectangle.stack.fill") }
            .tag(AuthenticatedTab.offers)

            profileTab
                .tabItem { Label("shell.tab.profile", systemImage: "person.crop.circle.fill") }
                .tag(AuthenticatedTab.profile)
        }
        .toolbarBackground(CrediWiseColors.surface, for: .tabBar)
        .toolbarBackground(.visible, for: .tabBar)
    }

    private var profileTab: some View {
        ZStack {
            CrediWiseColors.surfaceAlt.ignoresSafeArea()
            ScrollView {
                VStack(alignment: .leading, spacing: SpacingTokens.large) {
                    shellPlaceholderCard(
                        icon: "person.crop.circle.fill",
                        eyebrow: "shell.profile.eyebrow",
                        title: "shell.profile.title",
                        detail: "shell.profile.detail"
                    )

                    PrimaryButton(title: "session.sign_out") {
                        Task {
                            selectedTab = .home
                            await coordinator.signOut()
                        }
                    }
                    .accessibilityIdentifier("session.sign_out")

                    DisclaimerFooter()
                }
                .padding(SpacingTokens.large)
            }
        }
        .accessibilityIdentifier("shell.profile")
    }

    private func shellPlaceholder(
        icon: String,
        eyebrow: LocalizedStringKey,
        title: LocalizedStringKey,
        detail: LocalizedStringKey,
        identifier: String
    ) -> some View {
        ZStack {
            CrediWiseColors.surfaceAlt.ignoresSafeArea()
            ScrollView {
                VStack(spacing: SpacingTokens.large) {
                    shellPlaceholderCard(
                        icon: icon,
                        eyebrow: eyebrow,
                        title: title,
                        detail: detail
                    )
                    DisclaimerFooter()
                }
                .padding(SpacingTokens.large)
            }
        }
        .accessibilityIdentifier(identifier)
    }

    private func shellPlaceholderCard(
        icon: String,
        eyebrow: LocalizedStringKey,
        title: LocalizedStringKey,
        detail: LocalizedStringKey
    ) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.large) {
            ZStack {
                RoundedRectangle(cornerRadius: RadiusTokens.button)
                    .fill(CrediWiseColors.primaryTint)
                    .frame(width: 56, height: 56)

                Image(systemName: icon)
                    .font(.system(size: 24, weight: .semibold))
                    .foregroundStyle(CrediWiseColors.primary)
            }
            .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: SpacingTokens.small) {
                Text(eyebrow)
                    .font(TypographyTokens.caption.weight(.bold))
                    .foregroundStyle(CrediWiseColors.primary)
                Text(title)
                    .font(TypographyTokens.title)
                    .foregroundStyle(CrediWiseColors.textPrimary)
                Text(detail)
                    .font(TypographyTokens.body)
                    .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(SpacingTokens.xLarge)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        .shadow(color: .black.opacity(0.06), radius: 20, y: 8)
        .accessibilityElement(children: .combine)
    }

    @ViewBuilder
    private func destination(for route: AppRoute) -> some View {
        switch route {
        case .registration, .signIn:
            authenticationDestination(for: route)
        case .financingNeed, .upload, .extractionReview, .dataConfidence, .assessmentDashboard:
            assessmentDestination(for: route)
        case .shockSimulation, .offers, .offerDetail:
            cycle6Destination(for: route)
        }
    }

    @ViewBuilder
    private func authenticationDestination(for route: AppRoute) -> some View {
        switch route {
        case .registration:
            AuthenticationView(
                viewModel: coordinator.makeAuthenticationViewModel(mode: .registration),
                onRegistered: coordinator.completeRegistration,
                onSignedIn: coordinator.completeSignIn,
                onSwitchMode: { coordinator.switchAuthenticationMode(from: .registration) }
            )
        case .signIn:
            AuthenticationView(
                viewModel: coordinator.makeAuthenticationViewModel(mode: .signIn),
                onRegistered: coordinator.completeRegistration,
                onSignedIn: coordinator.completeSignIn,
                onSwitchMode: { coordinator.switchAuthenticationMode(from: .signIn) }
            )
        default:
            EmptyView()
        }
    }

    @ViewBuilder
    private func assessmentDestination(for route: AppRoute) -> some View {
        switch route {
        case .financingNeed:
            FinancingNeedView(
                viewModel: coordinator.makeFinancingNeedViewModel(),
                onSaved: coordinator.completeFinancingNeed
            )
        case .upload:
            UploadView(
                viewModel: coordinator.makeUploadViewModel(),
                allowsSyntheticSelection: coordinator.shouldOfferSyntheticUpload,
                isServiceAvailable: coordinator.shouldEnableDocumentUpload,
                onReviewReady: coordinator.showExtractionReview
            )
        case let .extractionReview(documentID):
            ExtractionReviewView(
                viewModel: coordinator.makeExtractionReviewViewModel(documentID: documentID),
                onConfirmed: coordinator.showDataConfidence
            )
        case let .dataConfidence(documentID):
            DataConfidenceView(
                viewModel: coordinator.makeDataConfidenceViewModel(documentID: documentID),
                onContinueToDashboard: {
                    try await coordinator.createAssessment(documentID: documentID)
                }
            )
        case let .assessmentDashboard(assessmentID):
            AssessmentDashboardView(
                viewModel: coordinator.makeAssessmentDashboardViewModel(assessmentID: assessmentID),
                shockViewModel: coordinator.makeShockViewModel(assessmentID: assessmentID),
                showsCompleteDashboard: coordinator.shouldShowCompleteAssessmentFlow,
                onOpenShocks: { coordinator.showShockSimulation(assessmentID: assessmentID) },
                onOpenOffers: { coordinator.showOffers(assessmentID: assessmentID) }
            )
        default:
            EmptyView()
        }
    }

    @ViewBuilder
    private func cycle6Destination(for route: AppRoute) -> some View {
        switch route {
        case let .shockSimulation(assessmentID):
            ShockSimulationView(
                viewModel: coordinator.makeShockViewModel(assessmentID: assessmentID)
            )
        case let .offers(assessmentID):
            OffersListView(
                viewModel: coordinator.makeOffersViewModel(assessmentID: assessmentID),
                onOpenOffer: { offerID in
                    coordinator.showOfferDetail(assessmentID: assessmentID, offerID: offerID)
                }
            )
        case let .offerDetail(assessmentID, offerID):
            OfferDetailView(
                viewModel: coordinator.makeOfferDetailViewModel(
                    assessmentID: assessmentID,
                    offerID: offerID
                )
            )
        default:
            EmptyView()
        }
    }

    private var startAuthenticatedFlow: () -> Void {
        if coordinator.shouldOfferSyntheticUpload && !coordinator.shouldOfferSyntheticAssessment {
            return { coordinator.showUpload() }
        }
        return { coordinator.showFinancingNeed() }
    }
}

private enum AuthenticatedTab: Hashable {
    case home
    case records
    case assessment
    case offers
    case profile
}
