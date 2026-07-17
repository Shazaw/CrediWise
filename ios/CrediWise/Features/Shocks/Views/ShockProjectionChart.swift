import Charts
import SwiftUI

struct ShockProjectionChart: View {
    let scenario: ShockAssessment.Scenario
    let requiredLiquidityBuffer: Int64

    var body: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium) {
            Chart {
                ForEach(scenario.chartPoints) { point in
                    AreaMark(
                        x: .value("Period", NSLocalizedString(point.periodKey, comment: "Projection period")),
                        y: .value("Balance", Double(point.balance))
                    )
                    .foregroundStyle(CrediWiseColors.primary.opacity(0.12))

                    LineMark(
                        x: .value("Period", NSLocalizedString(point.periodKey, comment: "Projection period")),
                        y: .value("Balance", Double(point.balance))
                    )
                    .foregroundStyle(CrediWiseColors.primary)
                    .lineStyle(StrokeStyle(lineWidth: 3, lineCap: .round))

                    PointMark(
                        x: .value("Period", NSLocalizedString(point.periodKey, comment: "Projection period")),
                        y: .value("Balance", Double(point.balance))
                    )
                    .foregroundStyle(point.balance < 0 ? CrediWiseColors.danger : CrediWiseColors.primary)
                }

                RuleMark(y: .value("Required buffer", Double(requiredLiquidityBuffer)))
                    .foregroundStyle(CrediWiseColors.warning)
                    .lineStyle(StrokeStyle(lineWidth: 2, dash: [6, 4]))

                RuleMark(y: .value("Zero", 0.0))
                    .foregroundStyle(CrediWiseColors.danger)
            }
            .frame(height: 220)
            .chartYAxis {
                AxisMarks(position: .leading) { value in
                    AxisGridLine()
                    AxisValueLabel {
                        if let amount = value.as(Double.self) {
                            Text(verbatim: IDRFormatter.string(from: Int64(amount.rounded())))
                        }
                    }
                }
            }
            .accessibilityHidden(true)

            Text(accessibilitySummary)
                .font(TypographyTokens.caption)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
                .accessibilityIdentifier("shocks.chart_summary")

            Divider()
            metric("shocks.scenario.monthly_balance", scenario.monthlyProjectedBalance)
            metric("shocks.scenario.minimum_balance", scenario.minimumTemporalBalance)
            metric("shocks.scenario.deficit", scenario.deficit)
            LabeledContent("shocks.scenario.buffer") {
                Text(
                    LocalizedStringKey(
                        scenario.requiredBufferBreached
                            ? "shocks.buffer.breached"
                            : "shocks.buffer.preserved"
                    )
                )
            }
        }
        .padding(SpacingTokens.standard)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        .accessibilityElement(children: .combine)
        .accessibilityLabel(accessibilitySummary)
        .accessibilityIdentifier("shocks.chart")
    }

    private var accessibilitySummary: String {
        let startingBalance = scenario.chartPoints.first?.balance ?? scenario.minimumTemporalBalance
        let endingBalance = scenario.chartPoints.last?.balance ?? scenario.monthlyProjectedBalance
        return String(
            format: NSLocalizedString("shocks.chart.accessibility", comment: "Shock chart summary"),
            NSLocalizedString(scenario.titleKey, comment: "Shock scenario"),
            NSLocalizedString(statusKey, comment: "Shock status"),
            NSLocalizedString(trendKey, comment: "Balance trend"),
            IDRFormatter.string(from: startingBalance),
            IDRFormatter.string(from: endingBalance),
            IDRFormatter.string(from: scenario.monthlyProjectedBalance),
            IDRFormatter.string(from: scenario.minimumTemporalBalance),
            IDRFormatter.string(from: scenario.deficit),
            scenario.requiredBufferBreached
                ? NSLocalizedString("shocks.buffer.breached", comment: "Buffer breached")
                : NSLocalizedString("shocks.buffer.preserved", comment: "Buffer preserved")
        )
    }

    private var statusKey: String {
        "shocks.status.\(scenario.status.rawValue)"
    }

    private var trendKey: String {
        guard let first = scenario.chartPoints.first?.balance,
              let last = scenario.chartPoints.last?.balance else {
            return "shocks.trend.steady"
        }
        if last > first { return "shocks.trend.rising" }
        if last < first { return "shocks.trend.falling" }
        return "shocks.trend.steady"
    }

    private func metric(_ title: LocalizedStringKey, _ amount: Int64) -> some View {
        LabeledContent(title) {
            Text(verbatim: IDRFormatter.string(from: amount))
                .font(TypographyTokens.body.monospacedDigit())
        }
    }

}
