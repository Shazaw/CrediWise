import SwiftUI

struct ShockResilienceCard: View {
    let report: ShockAssessment
    let onOpen: (() -> Void)?

    @ViewBuilder
    var body: some View {
        if let onOpen {
            Button(action: onOpen) {
                cardContent(showsOpenPrompt: true)
            }
            .buttonStyle(.plain)
            .accessibilityLabel(accessibilityLabel)
            .accessibilityHint(Text("shocks.card.open"))
            .accessibilityIdentifier("dashboard.shock.card")
        } else {
            cardContent(showsOpenPrompt: false)
                .accessibilityElement(children: .ignore)
                .accessibilityLabel(accessibilityLabel)
        }
    }

    private func cardContent(showsOpenPrompt: Bool) -> some View {
        HStack(spacing: SpacingTokens.large) {
            VStack(spacing: 0) {
                Text(verbatim: scoreText)
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
                if showsOpenPrompt {
                    Text("shocks.card.open")
                        .font(TypographyTokens.caption.weight(.semibold))
                        .foregroundStyle(CrediWiseColors.textOnPrimary.opacity(0.8))
                }
            }
            Spacer(minLength: 0)
        }
        .padding(SpacingTokens.large)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(CrediWiseColors.primary)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
    }

    private var bandKey: String {
        report.band.map { "shocks.band.\($0.rawValue)" } ?? "dashboard.value.unavailable"
    }

    private var scoreColor: Color {
        switch report.band {
        case .strong?: return CrediWiseColors.accent
        case .moderate?: return CrediWiseColors.warning
        case .fragile?, nil: return CrediWiseColors.textOnPrimary
        }
    }

    private var scoreText: String {
        guard let score = report.resilienceScore else {
            return NSLocalizedString("dashboard.value.unavailable", comment: "Unavailable score")
        }
        return NSDecimalNumber(decimal: score).stringValue
    }

    private var accessibilityLabel: Text {
        Text(accessibilityLabelText)
    }

    var accessibilityLabelText: String {
        let band = NSLocalizedString(bandKey, comment: "Shock resilience band")
        guard let score = report.resilienceScore else {
            return String(
                format: NSLocalizedString(
                    "shocks.card.accessibility_unavailable",
                    comment: "Unavailable shock score"
                ),
                NSLocalizedString("dashboard.value.unavailable", comment: "Unavailable value"),
                band
            )
        }
        return String(
            format: NSLocalizedString("shocks.card.accessibility", comment: "Shock score"),
            NSDecimalNumber(decimal: score).intValue,
            band
        )
    }
}
