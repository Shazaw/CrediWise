import SwiftUI

struct DigitalTwinSummaryView: View {
    let twin: AssessmentDashboard.Twin

    var body: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.large) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                    Text("dashboard.twin.eyebrow")
                        .font(TypographyTokens.caption.weight(.bold))
                        .foregroundStyle(CrediWiseColors.primary)
                    Text("dashboard.twin.title")
                        .font(TypographyTokens.title)
                }
                Spacer()
                Text(LocalizedStringKey(coverageKey))
                    .font(TypographyTokens.caption.weight(.bold))
                    .foregroundStyle(twin.coverage == .low ? CrediWiseColors.danger : CrediWiseColors.success)
                    .padding(.horizontal, SpacingTokens.medium)
                    .padding(.vertical, SpacingTokens.small)
                    .background(CrediWiseColors.primaryTint)
                    .clipShape(Capsule())
            }

            VStack(spacing: SpacingTokens.small) {
                metric("dashboard.twin.median_income", twin.medianIncome, emphasized: true)
                metric("dashboard.twin.essential", twin.essentialExpenses)
                metric("dashboard.twin.discretionary", twin.discretionaryExpenses)
                metric("dashboard.twin.debt", twin.existingDebt)
                metric("dashboard.twin.free_cash_flow", twin.averageFreeCashFlow)
                metric("dashboard.twin.weakest_month", twin.weakestMonthCashFlow)
            }

            VStack(alignment: .leading, spacing: SpacingTokens.small) {
                Text("dashboard.twin.income_split")
                    .font(TypographyTokens.cardTitle)
                metric("dashboard.twin.personal", twin.personalIncome)
                metric("dashboard.twin.business", twin.businessIncome)
                Text("dashboard.twin.split_note")
                    .font(TypographyTokens.caption)
                    .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.68))
            }
        }
        .padding(SpacingTokens.large)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("dashboard.twin")
    }

    private var coverageKey: String {
        "dashboard.twin.coverage.\(twin.coverage.rawValue)"
    }

    private func metric(
        _ title: LocalizedStringKey,
        _ amount: Int64,
        emphasized: Bool = false
    ) -> some View {
        HStack(alignment: .firstTextBaseline) {
            Text(title)
                .font(emphasized ? TypographyTokens.cardTitle : TypographyTokens.body)
            Spacer()
            Text(verbatim: IDRFormatter.string(from: amount))
                .font((emphasized ? TypographyTokens.cardTitle : TypographyTokens.body).monospacedDigit())
        }
    }
}
