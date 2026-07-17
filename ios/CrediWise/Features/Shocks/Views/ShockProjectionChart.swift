import Charts
import SwiftUI

struct ShockProjectionChart: View {
    let scenario: ShockAssessment.Scenario

    var body: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium) {
            Text("shocks.chart.title")
                .font(TypographyTokens.cardTitle)
            Chart {
                ForEach(scenario.projectionPoints) { point in
                    LineMark(
                        x: .value("Sequence", point.sequence),
                        y: .value("Projected balance", Double(point.projectedBalance))
                    )
                    .foregroundStyle(CrediWiseColors.primary)
                    PointMark(
                        x: .value("Sequence", point.sequence),
                        y: .value("Projected balance", Double(point.projectedBalance))
                    )
                    .foregroundStyle(
                        point.projectedBalance < 0 ? CrediWiseColors.danger : CrediWiseColors.primary
                    )
                }
                RuleMark(y: .value("Required buffer", Double(scenario.requiredLiquidityBuffer)))
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

            ForEach(scenario.projectionPoints) { point in
                Text(pointSummary(point))
                    .font(TypographyTokens.caption)
            }

            Divider()
            metric("shocks.scenario.projected_cash_flow", scenario.projectedCashFlow)
            metric("shocks.scenario.minimum_balance", scenario.minimumProjectedBalance)
            metric("shocks.scenario.required_buffer", scenario.requiredLiquidityBuffer)
            metric("shocks.scenario.deficit", scenario.deficitAmount)
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
        let points = scenario.projectionPoints.map(pointSummary).joined(separator: "; ")
        return String(
            format: NSLocalizedString("shocks.chart.accessibility", comment: "Shock chart summary"),
            scenarioTitle,
            NSLocalizedString("shocks.status.\(scenario.status.rawValue)", comment: "Shock status"),
            points,
            IDRFormatter.string(from: scenario.projectedCashFlow),
            IDRFormatter.string(from: scenario.minimumProjectedBalance),
            IDRFormatter.string(from: scenario.deficitAmount),
            scenario.requiredBufferBreached
                ? NSLocalizedString("shocks.buffer.breached", comment: "Buffer breached")
                : NSLocalizedString("shocks.buffer.preserved", comment: "Buffer preserved")
        )
    }

    private var scenarioTitle: String {
        NSLocalizedString("shocks.scenario.\(scenario.kind.rawValue).title", comment: "Shock scenario")
    }

    private func pointSummary(_ point: ShockAssessment.ProjectionPoint) -> String {
        String(
            format: NSLocalizedString("shocks.chart.point", comment: "Projection point"),
            point.sequence,
            point.dayOfMonth,
            eventDisplayName(point),
            IDRFormatter.string(from: point.amount),
            IDRFormatter.string(from: point.projectedBalance)
        )
    }

    private func eventDisplayName(_ point: ShockAssessment.ProjectionPoint) -> String {
        if point.isKnownEventType {
            return NSLocalizedString(point.eventLabelKey, comment: "Shock timeline event")
        }
        return String(
            format: NSLocalizedString("shocks.event.unknown_value", comment: "Unknown event type"),
            point.eventType
        )
    }

    private func metric(_ title: LocalizedStringKey, _ amount: Int64) -> some View {
        LabeledContent(title) {
            Text(verbatim: IDRFormatter.string(from: amount))
                .font(TypographyTokens.body.monospacedDigit())
        }
    }
}
