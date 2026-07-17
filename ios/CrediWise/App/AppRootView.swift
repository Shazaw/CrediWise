import SwiftUI

struct AppRootView: View {
    @ObservedObject var coordinator: AppCoordinator
    @ObservedObject private var sessionManager: SessionManager

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
        NavigationStack(path: $coordinator.path) {
            AuthenticatedHomeView(
                onStart: coordinator.shouldOfferSyntheticAssessment
                    ? coordinator.showFinancingNeed
                    : coordinator.showUpload,
                showsCycle5Preview: coordinator.shouldOfferSyntheticAssessment,
                onSignOut: coordinator.signOut
            )
            .navigationDestination(for: AppRoute.self) { route in
                destination(for: route)
            }
        }
    }

    @ViewBuilder
    private func destination(for route: AppRoute) -> some View {
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
                onContinueToDashboard: coordinator.shouldOfferSyntheticAssessment
                    ? coordinator.showSyntheticAssessmentDashboard
                    : nil
            )
        case let .assessmentDashboard(assessmentID):
            AssessmentDashboardView(
                viewModel: coordinator.makeAssessmentDashboardViewModel(assessmentID: assessmentID)
            )
        }
    }
}
