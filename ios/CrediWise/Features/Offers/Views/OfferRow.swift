import SwiftUI

struct OfferRow: View {
    let offer: SafeOffer
    let onOpen: () -> Void

    var body: some View {
        Button(action: onOpen) {
            VStack(alignment: .leading, spacing: SpacingTokens.medium) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                        Text(LocalizedStringKey(offer.provider.nameKey))
                            .font(TypographyTokens.cardTitle)
                        Text("offers.provider.simulated")
                            .font(TypographyTokens.caption.weight(.bold))
                            .foregroundStyle(CrediWiseColors.primary)
                    }
                    Spacer()
                    Text(LocalizedStringKey(bandKey))
                        .font(TypographyTokens.caption.weight(.bold))
                        .foregroundStyle(bandTextColor)
                        .padding(.horizontal, SpacingTokens.small)
                        .padding(.vertical, SpacingTokens.xSmall)
                        .background(bandColor)
                        .clipShape(Capsule())
                }

                HStack(alignment: .firstTextBaseline) {
                    Text(verbatim: IDRFormatter.string(from: offer.netAmountReceived))
                        .font(TypographyTokens.title.monospacedDigit())
                    Spacer()
                    Text(
                        String(
                            format: NSLocalizedString("offers.row.score", comment: "Offer safety score"),
                            offer.score
                        )
                    )
                    .font(TypographyTokens.body.monospacedDigit().weight(.bold))
                }

                Text(
                    String(
                        format: NSLocalizedString("offers.row.instalment", comment: "Offer instalment"),
                        IDRFormatter.string(from: offer.instalment),
                        offer.tenorMonths
                    )
                )
                .font(TypographyTokens.caption)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))

                if offer.isSafest {
                    Label("offers.row.safest", systemImage: "shield.checkered")
                        .font(TypographyTokens.caption.weight(.bold))
                        .foregroundStyle(CrediWiseColors.success)
                        .accessibilityIdentifier("offers.safest")
                }

                if let warning = offer.warnings.first {
                    Label(LocalizedStringKey(warning.titleKey), systemImage: "exclamationmark.triangle.fill")
                        .font(TypographyTokens.caption.weight(.semibold))
                        .foregroundStyle(CrediWiseColors.danger)
                }
            }
            .padding(SpacingTokens.large)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(CrediWiseColors.surface)
            .overlay {
                RoundedRectangle(cornerRadius: RadiusTokens.card)
                    .stroke(bandColor, lineWidth: 2)
            }
            .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(accessibilityLabel)
        .accessibilityHint(Text("offers.row.open_hint"))
        .accessibilityIdentifier("offers.row.\(offer.offerID)")
    }

    private var bandKey: String {
        "offers.band.\(offer.band.rawValue)"
    }

    private var bandColor: Color {
        switch offer.band {
        case .safe: return CrediWiseColors.accent
        case .caution: return CrediWiseColors.warning
        case .unsafe: return CrediWiseColors.danger
        }
    }

    private var bandTextColor: Color {
        offer.band == .unsafe ? CrediWiseColors.textOnPrimary : CrediWiseColors.textPrimary
    }

    private var accessibilityLabel: Text {
        let safestStatus = NSLocalizedString(
            offer.isSafest ? "offers.row.safest" : "offers.row.not_safest",
            comment: "Safest offer status"
        )
        let warningSummary = offer.warnings.first.map {
            NSLocalizedString($0.titleKey, comment: "Offer warning")
        } ?? NSLocalizedString("offers.row.no_warning", comment: "Offer warning status")
        return Text(
            String(
                format: NSLocalizedString("offers.row.accessibility", comment: "Offer summary"),
                offer.suppliedRank,
                NSLocalizedString(offer.provider.nameKey, comment: "Simulated provider"),
                NSLocalizedString(bandKey, comment: "Safety band"),
                offer.score,
                IDRFormatter.string(from: offer.netAmountReceived),
                IDRFormatter.string(from: offer.instalment),
                offer.tenorMonths,
                safestStatus,
                warningSummary
            )
        )
    }
}
