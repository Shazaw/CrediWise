import SwiftUI

struct AuthPlaceholderView: View {
    let titleKey: String
    let messageKey: String

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: SpacingTokens.xLarge) {
            Spacer()

            Image(systemName: "person.badge.key.fill")
                .font(.system(size: 56))
                .foregroundStyle(CrediWiseColors.primary)
                .accessibilityHidden(true)

            VStack(spacing: SpacingTokens.medium) {
                Text(LocalizedStringKey(titleKey))
                    .font(TypographyTokens.title)
                    .foregroundStyle(CrediWiseColors.textPrimary)
                    .multilineTextAlignment(.center)
                    .accessibilityIdentifier("auth.placeholder.title")

                Text(LocalizedStringKey(messageKey))
                    .font(TypographyTokens.body)
                    .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
                    .multilineTextAlignment(.center)
            }

            PrimaryButton(title: "common.back") {
                dismiss()
            }

            Spacer()
            DisclaimerFooter()
        }
        .padding(SpacingTokens.xLarge)
        .background(CrediWiseColors.surfaceAlt.ignoresSafeArea())
        .navigationBarBackButtonHidden(true)
        .accessibilityIdentifier("auth.placeholder")
    }
}
