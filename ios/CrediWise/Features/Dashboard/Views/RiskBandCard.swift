import SwiftUI

struct RiskBandCard: View {
    let risk: AssessmentDashboard.Risk

    @State private var isExpanded = false

    var body: some View {
        DisclosureGroup(isExpanded: $isExpanded) {
            VStack(alignment: .leading, spacing: SpacingTokens.medium) {
                reasonSection("dashboard.risk.positive", reasons: risk.positiveFactors)
                reasonSection("dashboard.risk.watch", reasons: risk.riskFactors)
            }
            .padding(.top, SpacingTokens.medium)
        } label: {
            HStack(alignment: .center, spacing: SpacingTokens.large) {
                Text(LocalizedStringKey(bandKey))
                    .font(TypographyTokens.hero.monospaced())
                    .foregroundStyle(CrediWiseColors.textOnPrimary)
                    .frame(width: 64, height: 64)
                    .background(bandColor)
                    .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.button))
                    .accessibilityHidden(true)

                VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                    Text("dashboard.risk.title")
                        .font(TypographyTokens.caption.weight(.bold))
                        .foregroundStyle(CrediWiseColors.accent)
                    Text(LocalizedStringKey(labelKey))
                        .font(TypographyTokens.cardTitle)
                        .foregroundStyle(CrediWiseColors.textOnPrimary)
                    Text(LocalizedStringKey(confidenceKey))
                        .font(TypographyTokens.caption)
                        .foregroundStyle(CrediWiseColors.textOnPrimary.opacity(0.8))
                }
            }
        }
        .tint(CrediWiseColors.textOnPrimary)
        .padding(SpacingTokens.large)
        .background(CrediWiseColors.primaryDark)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        .accessibilityElement(children: isExpanded ? .contain : .ignore)
        .accessibilityLabel(accessibilityLabel)
        .accessibilityHint(Text("dashboard.card.open_hint"))
        .accessibilityIdentifier("dashboard.risk.card")
    }

    private var bandKey: String {
        "dashboard.risk.band.\(bandToken)"
    }

    private var labelKey: String {
        "dashboard.risk.label.\(bandToken)"
    }

    private var bandToken: String {
        switch risk.band {
        case .bandA: return "a"
        case .bandB: return "b"
        case .bandC: return "c"
        case .bandD: return "d"
        case .insufficientData: return "insufficientData"
        }
    }

    private var confidenceKey: String {
        "dashboard.risk.confidence.\(risk.modelConfidence.rawValue)"
    }

    private var bandColor: Color {
        switch risk.band {
        case .bandA, .bandB: return CrediWiseColors.success
        case .bandC: return CrediWiseColors.warning
        case .bandD, .insufficientData: return CrediWiseColors.danger
        }
    }

    private var accessibilityLabel: Text {
        Text(
            String(
                format: NSLocalizedString("dashboard.risk.accessibility", comment: "Risk summary"),
                NSLocalizedString(bandKey, comment: "Risk band"),
                NSLocalizedString(confidenceKey, comment: "Model confidence")
            )
        )
    }

    private func reasonSection(
        _ title: LocalizedStringKey,
        reasons: [AssessmentDashboard.Reason]
    ) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.small) {
            Text(title)
                .font(TypographyTokens.caption.weight(.bold))
                .foregroundStyle(CrediWiseColors.textOnPrimary.opacity(0.78))
            ForEach(reasons) { reason in
                VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                    Text(LocalizedStringKey(reason.titleKey))
                        .font(TypographyTokens.body.weight(.semibold))
                    Text(LocalizedStringKey(reason.detailKey))
                        .font(TypographyTokens.caption)
                        .opacity(0.78)
                }
                .foregroundStyle(CrediWiseColors.textOnPrimary)
            }
        }
    }
}
