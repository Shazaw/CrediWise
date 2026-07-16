import SwiftUI

struct DisclaimerFooter: View {
    var foregroundColor: Color = CrediWiseColors.textPrimary.opacity(0.7)

    var body: some View {
        Text(PositioningStrings.estimatedAssessmentNotice)
            .font(TypographyTokens.caption)
            .foregroundStyle(foregroundColor)
            .multilineTextAlignment(.center)
            .fixedSize(horizontal: false, vertical: true)
            .accessibilityIdentifier("positioning.disclaimer")
    }
}
