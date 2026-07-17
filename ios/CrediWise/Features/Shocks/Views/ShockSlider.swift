import SwiftUI

struct ShockSlider: View {
    let title: LocalizedStringKey
    let valueText: String
    @Binding var value: Double
    let range: ClosedRange<Double>
    let step: Double

    var body: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.small) {
            HStack {
                Text(title)
                    .font(TypographyTokens.body.weight(.semibold))
                Spacer()
                Text(verbatim: valueText)
                    .font(TypographyTokens.body.monospacedDigit().weight(.bold))
            }
            Slider(value: $value, in: range, step: step)
                .tint(CrediWiseColors.primary)
                .accessibilityLabel(title)
                .accessibilityValue(Text(verbatim: valueText))
        }
        .padding(SpacingTokens.standard)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.button))
    }
}
