import SwiftUI

struct SafeBorrowingCard: View {
    let recommendation: AssessmentDashboard.SafeBorrowing

    @State private var isExpanded = false

    var body: some View {
        DisclosureGroup(isExpanded: $isExpanded) {
            VStack(alignment: .leading, spacing: SpacingTokens.medium) {
                metric("dashboard.safe.max_instalment", recommendation.maximumSafeInstalment)
                metric("dashboard.safe.required_buffer", recommendation.requiredLiquidityBuffer)
                LabeledContent("dashboard.safe.tenor") {
                    Text(tenorText)
                }
                LabeledContent("dashboard.safe.due_date") {
                    Text(dueDateText)
                }
                LabeledContent("dashboard.safe.frequency") {
                    Text(LocalizedStringKey(frequencyKey))
                }
                ForEach(recommendation.reasons) { reason in
                    VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                        Text(LocalizedStringKey(reason.titleKey))
                            .font(TypographyTokens.body.weight(.semibold))
                        Text(LocalizedStringKey(reason.detailKey))
                            .font(TypographyTokens.caption)
                            .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.7))
                    }
                }
            }
            .padding(.top, SpacingTokens.medium)
        } label: {
            VStack(alignment: .leading, spacing: SpacingTokens.small) {
                Text("dashboard.safe.title")
                    .font(TypographyTokens.caption.weight(.bold))
                    .foregroundStyle(CrediWiseColors.primary)
                Text(amountText)
                    .font(TypographyTokens.hero.monospacedDigit())
                    .foregroundStyle(CrediWiseColors.textPrimary)
                Text(
                    LocalizedStringKey(
                    recommendation.illustrativeAmount > 0
                        ? "dashboard.safe.illustrative"
                        : "dashboard.safe.zero"
                    )
                )
                .font(TypographyTokens.caption)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
            }
        }
        .tint(CrediWiseColors.primary)
        .padding(SpacingTokens.large)
        .background(CrediWiseColors.accent.opacity(0.82))
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        .accessibilityElement(children: isExpanded ? .contain : .ignore)
        .accessibilityLabel(accessibilityLabel)
        .accessibilityHint(Text("dashboard.card.open_hint"))
        .accessibilityIdentifier("dashboard.safe.card")
    }

    private var amountText: String {
        IDRFormatter.string(from: recommendation.illustrativeAmount)
    }

    private var tenorText: String {
        String(
            format: NSLocalizedString("dashboard.safe.tenor_value", comment: "Tenor"),
            recommendation.recommendedTenorMonths
        )
    }

    private var dueDateText: String {
        String(
            format: NSLocalizedString("dashboard.safe.due_date_value", comment: "Due date window"),
            recommendation.dueDateStart,
            recommendation.dueDateEnd
        )
    }

    private var frequencyKey: String {
        "dashboard.safe.frequency.\(recommendation.frequency.rawValue)"
    }

    private var accessibilityLabel: Text {
        Text(
            String(
                format: NSLocalizedString("dashboard.safe.accessibility", comment: "Safe amount"),
                amountText,
                IDRFormatter.string(from: recommendation.maximumSafeInstalment)
            )
        )
    }

    private func metric(_ title: LocalizedStringKey, _ amount: Int64) -> some View {
        LabeledContent(title) {
            Text(verbatim: IDRFormatter.string(from: amount))
                .font(.body.monospacedDigit())
        }
    }
}
