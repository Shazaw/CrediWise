import SwiftUI

struct AuthenticatedHomeView: View {
    let onStart: () -> Void
    let showsCycle5Preview: Bool

    var body: some View {
        ZStack {
            CrediWiseColors.surfaceAlt.ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: SpacingTokens.large) {
                    heroCard
                    journeyCard
                    privacyCard
                    DisclaimerFooter()
                }
                .padding(.horizontal, SpacingTokens.large)
                .padding(.top, SpacingTokens.medium)
                .padding(.bottom, SpacingTokens.xxLarge)
            }
        }
        .accessibilityIdentifier("session.authenticated")
    }

    private var heroCard: some View {
        ZStack(alignment: .topTrailing) {
            RoundedRectangle(cornerRadius: RadiusTokens.card)
                .fill(
                    LinearGradient(
                        colors: [CrediWiseColors.primary, CrediWiseColors.primaryDark],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )

            Circle()
                .stroke(CrediWiseColors.accent.opacity(0.18), lineWidth: 22)
                .frame(width: 150, height: 150)
                .offset(x: 48, y: -48)
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: SpacingTokens.large) {
                ViewThatFits(in: .horizontal) {
                    HStack(spacing: SpacingTokens.medium) {
                        brandLockup
                        Spacer(minLength: SpacingTokens.small)
                        readyPill
                    }

                    VStack(alignment: .leading, spacing: SpacingTokens.medium) {
                        brandLockup
                        readyPill
                    }
                }

                VStack(alignment: .leading, spacing: SpacingTokens.medium) {
                    Text("home.eyebrow")
                        .font(TypographyTokens.caption.weight(.bold))
                        .tracking(1.2)
                        .foregroundStyle(CrediWiseColors.accent)

                    Text("home.title")
                        .font(TypographyTokens.hero)
                        .foregroundStyle(CrediWiseColors.textOnPrimary)
                        .fixedSize(horizontal: false, vertical: true)
                        .accessibilityIdentifier("session.authenticated.title")

                    Text("home.subtitle")
                        .font(TypographyTokens.body)
                        .foregroundStyle(CrediWiseColors.textOnPrimary.opacity(0.82))
                        .fixedSize(horizontal: false, vertical: true)
                }

                CTAButton(
                    title: showsCycle5Preview
                        ? "session.start_assessment"
                        : "session.start_upload"
                ) {
                    onStart()
                }
                .accessibilityHint(Text("home.primary_action.hint"))
                .accessibilityIdentifier(
                    showsCycle5Preview
                        ? "session.start_assessment"
                        : "session.start_upload"
                )
            }
            .padding(SpacingTokens.large)
        }
        .fixedSize(horizontal: false, vertical: true)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        .shadow(color: CrediWiseColors.primaryDark.opacity(0.18), radius: 24, y: 12)
    }

    private var brandLockup: some View {
        HStack(spacing: SpacingTokens.medium) {
            ZStack {
                RoundedRectangle(cornerRadius: RadiusTokens.chip)
                    .fill(CrediWiseColors.accent)
                    .frame(width: 42, height: 42)

                Image(systemName: "shield.lefthalf.filled")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundStyle(CrediWiseColors.primaryDark)
            }
            .accessibilityHidden(true)

            Text("app.name")
                .font(TypographyTokens.cardTitle)
                .foregroundStyle(CrediWiseColors.textOnPrimary)
        }
        .accessibilityElement(children: .combine)
    }

    private var readyPill: some View {
        Text("home.status.ready")
            .font(TypographyTokens.caption.weight(.bold))
            .foregroundStyle(CrediWiseColors.primaryDark)
            .padding(.horizontal, SpacingTokens.medium)
            .padding(.vertical, SpacingTokens.small)
            .background(CrediWiseColors.accent)
            .clipShape(Capsule())
    }

    private var journeyCard: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.large) {
            VStack(alignment: .leading, spacing: SpacingTokens.small) {
                Text("home.journey.eyebrow")
                    .font(TypographyTokens.caption.weight(.bold))
                    .foregroundStyle(CrediWiseColors.primary)

                Text("home.journey.title")
                    .font(TypographyTokens.title)
                    .foregroundStyle(CrediWiseColors.textPrimary)

                Text("home.journey.subtitle")
                    .font(TypographyTokens.body)
                    .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.7))
                    .fixedSize(horizontal: false, vertical: true)
            }

            journeyStep(
                number: "1",
                icon: "scope",
                title: "home.journey.need.title",
                detail: "home.journey.need.detail",
                identifier: "home.journey.step.need"
            )
            journeyStep(
                number: "2",
                icon: "doc.text.magnifyingglass",
                title: "home.journey.verify.title",
                detail: "home.journey.verify.detail",
                identifier: "home.journey.step.verify"
            )
            journeyStep(
                number: "3",
                icon: "arrow.left.arrow.right.circle",
                title: "home.journey.compare.title",
                detail: "home.journey.compare.detail",
                identifier: "home.journey.step.compare"
            )
        }
        .padding(SpacingTokens.large)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        .shadow(color: .black.opacity(0.06), radius: 20, y: 8)
        .accessibilityIdentifier("home.journey")
    }

    private var privacyCard: some View {
        HStack(alignment: .top, spacing: SpacingTokens.medium) {
            Image(systemName: "lock.shield.fill")
                .font(.system(size: 22, weight: .semibold))
                .foregroundStyle(CrediWiseColors.primary)
                .frame(width: 32)
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                Text("home.privacy.title")
                    .font(TypographyTokens.cardTitle)
                    .foregroundStyle(CrediWiseColors.textPrimary)

                Text("home.privacy.detail")
                    .font(TypographyTokens.caption)
                    .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(SpacingTokens.large)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(CrediWiseColors.primaryTint)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("home.privacy")
    }

    private func journeyStep(
        number: String,
        icon: String,
        title: LocalizedStringKey,
        detail: LocalizedStringKey,
        identifier: String
    ) -> some View {
        HStack(alignment: .top, spacing: SpacingTokens.medium) {
            ZStack {
                Circle()
                    .fill(CrediWiseColors.primaryTint)
                    .frame(width: 44, height: 44)

                Image(systemName: icon)
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(CrediWiseColors.primary)
            }
            .overlay(alignment: .topLeading) {
                Text(number)
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(CrediWiseColors.textPrimary)
                    .frame(width: 18, height: 18)
                    .background(CrediWiseColors.accent)
                    .clipShape(Circle())
                    .offset(x: -4, y: -4)
            }
            .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(CrediWiseColors.textPrimary)

                Text(detail)
                    .font(TypographyTokens.caption)
                    .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.7))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier(identifier)
    }
}
