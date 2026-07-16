import SwiftUI

struct PrimaryButton: View {
    let title: LocalizedStringKey
    let action: () -> Void

    @Environment(\.isEnabled) private var isEnabled

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.headline)
                .foregroundStyle(CrediWiseColors.textOnPrimary)
                .frame(maxWidth: .infinity)
                .padding(.vertical, SpacingTokens.standard)
                .background(CrediWiseColors.primary)
                .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.button))
                .overlay {
                    RoundedRectangle(cornerRadius: RadiusTokens.button)
                        .stroke(CrediWiseColors.textOnPrimary.opacity(0.35), lineWidth: 1)
                }
        }
        .buttonStyle(.plain)
        .opacity(isEnabled ? 1 : 0.55)
    }
}
