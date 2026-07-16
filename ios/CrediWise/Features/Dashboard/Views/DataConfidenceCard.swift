import Foundation
import SwiftUI

struct DataConfidenceCard: View {
    let report: DataConfidenceReport
    let onOpen: () -> Void

    var body: some View {
        Button(action: onOpen) {
            HStack(spacing: SpacingTokens.large) {
                ZStack {
                    Circle()
                        .stroke(CrediWiseColors.textOnPrimary.opacity(0.2), lineWidth: 10)
                    Circle()
                        .trim(from: 0, to: Double(report.score) / 100)
                        .stroke(
                            CrediWiseColors.accent,
                            style: StrokeStyle(lineWidth: 10, lineCap: .round)
                        )
                        .rotationEffect(.degrees(-90))
                    VStack(spacing: 0) {
                        Text(verbatim: "\(report.score)")
                            .font(TypographyTokens.hero.monospacedDigit())
                        Text("confidence.card.out_of")
                            .font(TypographyTokens.caption)
                    }
                    .foregroundStyle(CrediWiseColors.textOnPrimary)
                }
                .frame(width: 116, height: 116)
                .accessibilityHidden(true)

                VStack(alignment: .leading, spacing: SpacingTokens.small) {
                    Text("confidence.card.title")
                        .font(TypographyTokens.caption.weight(.bold))
                        .foregroundStyle(CrediWiseColors.accent)
                    Text(LocalizedStringKey(bandKey))
                        .font(TypographyTokens.title)
                        .foregroundStyle(CrediWiseColors.textOnPrimary)
                    Text("confidence.card.open")
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
        .accessibilityHint(Text("confidence.card.open"))
        .accessibilityIdentifier("confidence.card")
    }

    private var bandKey: String {
        "confidence.band.\(report.band.rawValue)"
    }

    private var accessibilityLabel: Text {
        Text(
            String(
                format: NSLocalizedString("confidence.card.accessibility_label", comment: "Confidence score"),
                report.score,
                NSLocalizedString(bandKey, comment: "Confidence band")
            )
        )
    }
}
