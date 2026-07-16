import SwiftUI

struct WelcomeView: View {
    let onCreateAccount: () -> Void
    let onSignIn: () -> Void

    var body: some View {
        ZStack {
            CrediWiseColors.primaryDark
                .ignoresSafeArea()

            decorativeBackground

            ScrollView {
                VStack(alignment: .leading, spacing: SpacingTokens.xLarge) {
                    brandHeader
                    hero
                    safetyCard
                    actions
                    DisclaimerFooter(foregroundColor: CrediWiseColors.textOnPrimary.opacity(0.78))
                }
                .padding(.horizontal, SpacingTokens.xLarge)
                .padding(.top, SpacingTokens.large)
                .padding(.bottom, SpacingTokens.xLarge)
            }
        }
        .accessibilityIdentifier("welcome.screen")
    }

    private var decorativeBackground: some View {
        GeometryReader { geometry in
            Circle()
                .fill(CrediWiseColors.primary.opacity(0.9))
                .frame(width: geometry.size.width * 1.1)
                .offset(x: geometry.size.width * 0.28, y: -geometry.size.width * 0.55)

            Circle()
                .stroke(CrediWiseColors.accent.opacity(0.22), lineWidth: 28)
                .frame(width: 180, height: 180)
                .offset(x: -105, y: geometry.size.height * 0.58)
        }
        .accessibilityHidden(true)
    }

    private var brandHeader: some View {
        HStack(spacing: SpacingTokens.medium) {
            ZStack {
                RoundedRectangle(cornerRadius: RadiusTokens.chip)
                    .fill(CrediWiseColors.accent)
                    .frame(width: 44, height: 44)

                Image(systemName: "shield.lefthalf.filled")
                    .font(.system(size: 21, weight: .bold))
                    .foregroundStyle(CrediWiseColors.primaryDark)
            }

            Text("app.name")
                .font(TypographyTokens.title)
                .foregroundStyle(CrediWiseColors.textOnPrimary)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(Text("welcome.brand.accessibility_label"))
    }

    private var hero: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium) {
            Text("welcome.eyebrow")
                .font(.caption.weight(.bold))
                .tracking(1.4)
                .foregroundStyle(CrediWiseColors.accent)

            Text("welcome.title")
                .font(TypographyTokens.hero)
                .foregroundStyle(CrediWiseColors.textOnPrimary)
                .minimumScaleFactor(0.8)
                .fixedSize(horizontal: false, vertical: true)

            Text("welcome.subtitle")
                .font(.body)
                .foregroundStyle(CrediWiseColors.textOnPrimary.opacity(0.82))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var safetyCard: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.standard) {
            Text("welcome.safety_card.title")
                .font(TypographyTokens.cardTitle)
                .foregroundStyle(CrediWiseColors.textPrimary)

            featureRow(
                icon: "checkmark.shield.fill",
                title: "welcome.feature.verification.title",
                detail: "welcome.feature.verification.detail"
            )

            featureRow(
                icon: "waveform.path.ecg.rectangle.fill",
                title: "welcome.feature.capacity.title",
                detail: "welcome.feature.capacity.detail"
            )

            featureRow(
                icon: "arrow.left.arrow.right.circle.fill",
                title: "welcome.feature.offer.title",
                detail: "welcome.feature.offer.detail"
            )
        }
        .padding(SpacingTokens.large)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        .shadow(color: .black.opacity(0.08), radius: 24, y: 8)
    }

    private var actions: some View {
        VStack(spacing: SpacingTokens.medium) {
            CTAButton(title: "welcome.primary_action", action: onCreateAccount)
                .accessibilityIdentifier("welcome.create_account")

            PrimaryButton(title: "welcome.secondary_action", action: onSignIn)
                .accessibilityIdentifier("welcome.sign_in")
        }
    }

    private func featureRow(
        icon: String,
        title: LocalizedStringKey,
        detail: LocalizedStringKey
    ) -> some View {
        HStack(alignment: .top, spacing: SpacingTokens.medium) {
            Image(systemName: icon)
                .font(.system(size: 20, weight: .semibold))
                .foregroundStyle(CrediWiseColors.primary)
                .frame(width: 28)
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(CrediWiseColors.textPrimary)

                Text(detail)
                    .font(TypographyTokens.caption)
                    .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .accessibilityElement(children: .combine)
    }
}
