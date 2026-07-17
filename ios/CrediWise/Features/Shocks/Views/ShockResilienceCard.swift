import SwiftUI

struct ShockResilienceCard: View {
    let report: ShockAssessment
    let onOpen: () -> Void

    var body: some View {
        Button(action: onOpen) {
            HStack(spacing: SpacingTokens.large) {
                VStack(spacing: 0) {
                    Text(verbatim: "\(report.score)")
                        .font(TypographyTokens.hero.monospacedDigit())
                    Text("shocks.card.out_of")
                        .font(TypographyTokens.caption)
                }
                .foregroundStyle(scoreColor)
                .frame(width: 96, height: 96)
                .background(CrediWiseColors.surface.opacity(0.12))
                .clipShape(Circle())
                .accessibilityHidden(true)

                VStack(alignment: .leading, spacing: SpacingTokens.small) {
                    Text("shocks.card.title")
                        .font(TypographyTokens.caption.weight(.bold))
                        .foregroundStyle(CrediWiseColors.accent)
                    Text(LocalizedStringKey(bandKey))
                        .font(TypographyTokens.title)
                        .foregroundStyle(CrediWiseColors.textOnPrimary)
                    Text("shocks.card.open")
                        .font(TypographyTokens.caption.weight(.semibold))
                        .foregroundStyle(CrediWiseColors.textOnPrimary.opacity(0.8))
                }
                Spacer(minLength: 0)
            }
            .padding(SpacingTokens.large)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(CrediWiseColors.primary)
            .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        }
        .buttonStyle(.plain)
        .accessibilityLabel(accessibilityLabel)
        .accessibilityHint(Text("shocks.card.open"))
        .accessibilityIdentifier("dashboard.shock.card")
    }

    private var bandKey: String {
        "shocks.band.\(report.band.rawValue)"
    }

    private var scoreColor: Color {
        switch report.band {
        case .strong: return CrediWiseColors.accent
        case .moderate: return CrediWiseColors.warning
        case .fragile: return CrediWiseColors.textOnPrimary
        }
    }

    private var accessibilityLabel: Text {
        Text(
            String(
                format: NSLocalizedString("shocks.card.accessibility", comment: "Shock score"),
                report.score,
                NSLocalizedString(bandKey, comment: "Shock resilience band")
            )
        )
    }
}
