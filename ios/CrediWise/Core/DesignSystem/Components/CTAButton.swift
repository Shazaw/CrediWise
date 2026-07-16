import SwiftUI

struct CTAButton: View {
    let title: LocalizedStringKey
    let action: () -> Void

    @Environment(\.isEnabled) private var isEnabled

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.headline)
                .foregroundStyle(CrediWiseColors.textPrimary)
                .frame(maxWidth: .infinity)
                .padding(.vertical, SpacingTokens.standard)
                .background(CrediWiseColors.accent)
                .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.button))
        }
        .buttonStyle(.plain)
        .opacity(isEnabled ? 1 : 0.55)
    }
}
