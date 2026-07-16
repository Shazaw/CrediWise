import SwiftUI

struct DataConfidenceDetailView: View {
    let report: DataConfidenceReport

    var body: some View {
        ZStack {
            CrediWiseColors.surfaceAlt.ignoresSafeArea()
            ScrollView {
                VStack(alignment: .leading, spacing: SpacingTokens.large) {
                    Text("confidence.detail.title")
                        .font(TypographyTokens.title)
                    Text("confidence.detail.subtitle")
                        .font(TypographyTokens.body)
                        .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))

                    dimensionCard
                    reasonCard
                    evidenceCard
                    DisclaimerFooter()
                }
                .padding(SpacingTokens.large)
            }
        }
        .navigationTitle("confidence.detail.navigation_title")
        .navigationBarTitleDisplayMode(.inline)
        .accessibilityIdentifier("confidence.detail.screen")
    }

    private var dimensionCard: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.standard) {
            Text("confidence.dimensions.title")
                .font(TypographyTokens.cardTitle)
            ForEach(report.dimensions) { dimension in
                VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                    HStack {
                        Text(LocalizedStringKey(dimension.titleKey))
                        Spacer()
                        Text(verbatim: "\(dimension.score)/100")
                            .font(.subheadline.monospacedDigit().weight(.semibold))
                    }
                    ProgressView(value: Double(dimension.score), total: 100)
                        .tint(color(for: dimension.score))
                        .accessibilityLabel(Text(LocalizedStringKey(dimension.titleKey)))
                        .accessibilityValue(Text(verbatim: "\(dimension.score) / 100"))
                }
            }
        }
        .cardStyle()
        .accessibilityIdentifier("confidence.dimensions")
    }

    private var reasonCard: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.standard) {
            Text("confidence.reasons.title")
                .font(TypographyTokens.cardTitle)
            ForEach(report.reasons) { reason in
                VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                    Text(LocalizedStringKey(reason.titleKey))
                        .font(.subheadline.weight(.semibold))
                    Text(LocalizedStringKey(reason.detailKey))
                        .font(TypographyTokens.body)
                        .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
                    Label(sourceKey(reason.source), systemImage: sourceIcon(reason.source))
                        .font(TypographyTokens.caption.weight(.semibold))
                        .foregroundStyle(CrediWiseColors.primary)
                }
                .padding(SpacingTokens.medium)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(CrediWiseColors.primaryTint)
                .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.chip))
            }
        }
        .cardStyle()
    }

    private var evidenceCard: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium) {
            Text("confidence.evidence.title")
                .font(TypographyTokens.cardTitle)
            Text(LocalizedStringKey(assistanceKey))
                .font(TypographyTokens.body)
            LabeledContent("confidence.model_version", value: report.modelVersion)
                .font(TypographyTokens.caption)
            Text(LocalizedStringKey(report.recommendationKey))
                .font(TypographyTokens.body.weight(.semibold))
                .foregroundStyle(CrediWiseColors.primaryDark)
        }
        .cardStyle()
    }

    private var assistanceKey: String {
        "confidence.assistance.\(report.assistanceStatus.rawValue)"
    }

    private func sourceKey(_ source: DataConfidenceReport.EvidenceSource) -> LocalizedStringKey {
        LocalizedStringKey("confidence.source.\(source.rawValue)")
    }

    private func sourceIcon(_ source: DataConfidenceReport.EvidenceSource) -> String {
        source == .deterministic ? "function" : "eye.fill"
    }

    private func color(for score: Int) -> Color {
        if score >= 80 {
            return CrediWiseColors.success
        }
        if score >= 50 {
            return CrediWiseColors.warning
        }
        return CrediWiseColors.danger
    }
}

private extension View {
    func cardStyle() -> some View {
        padding(SpacingTokens.large)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(CrediWiseColors.surface)
            .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
    }
}
