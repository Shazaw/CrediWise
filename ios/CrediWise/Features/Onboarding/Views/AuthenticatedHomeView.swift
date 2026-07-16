import SwiftUI

struct AuthenticatedHomeView: View {
    let onSignOut: @MainActor () async -> Void

    var body: some View {
        ZStack {
            CrediWiseColors.surfaceAlt.ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: SpacingTokens.xLarge) {
                    Image(systemName: "checkmark.shield.fill")
                        .font(.system(size: 52, weight: .bold))
                        .foregroundStyle(CrediWiseColors.primary)
                        .accessibilityHidden(true)

                    VStack(alignment: .leading, spacing: SpacingTokens.medium) {
                        Text("session.authenticated.title")
                            .font(TypographyTokens.hero)
                            .foregroundStyle(CrediWiseColors.textPrimary)
                            .accessibilityIdentifier("session.authenticated.title")

                        Text("session.authenticated.message")
                            .font(TypographyTokens.body)
                            .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
                    }

                    PrimaryButton(title: "session.sign_out") {
                        Task { await onSignOut() }
                    }
                    .accessibilityIdentifier("session.sign_out")

                    DisclaimerFooter()
                }
                .padding(SpacingTokens.xLarge)
            }
        }
        .accessibilityIdentifier("session.authenticated")
    }
}
