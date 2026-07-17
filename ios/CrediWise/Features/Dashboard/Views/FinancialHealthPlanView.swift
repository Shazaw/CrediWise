import SwiftUI

struct FinancialHealthPlanView: View {
    let recommendations: [AssessmentDashboard.Recommendation]

    var body: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium) {
            Text("dashboard.plan.eyebrow")
                .font(TypographyTokens.caption.weight(.bold))
                .foregroundStyle(CrediWiseColors.primary)
            Text("dashboard.plan.title")
                .font(TypographyTokens.title)
            Text("dashboard.plan.subtitle")
                .font(TypographyTokens.body)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.7))

            ForEach(Array(recommendations.enumerated()), id: \.element.id) { index, recommendation in
                HStack(alignment: .top, spacing: SpacingTokens.medium) {
                    Text(verbatim: "\(index + 1)")
                        .font(TypographyTokens.cardTitle.monospacedDigit())
                        .foregroundStyle(CrediWiseColors.textPrimary)
                        .frame(width: 36, height: 36)
                        .background(CrediWiseColors.accent)
                        .clipShape(Circle())
                        .accessibilityHidden(true)

                    VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                        Text(LocalizedStringKey(recommendation.titleKey))
                            .font(TypographyTokens.cardTitle)
                        Text(LocalizedStringKey(recommendation.detailKey))
                            .font(TypographyTokens.body)
                            .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
                        Text(LocalizedStringKey(recommendation.targetMetricKey))
                            .font(TypographyTokens.caption.weight(.semibold))
                            .foregroundStyle(CrediWiseColors.primary)
                    }
                }
                .padding(SpacingTokens.medium)
                .background(CrediWiseColors.surface)
                .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.button))
            }
        }
        .accessibilityIdentifier("dashboard.plan")
    }
}
