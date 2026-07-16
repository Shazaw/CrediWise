import SwiftUI

struct UploadResultCard: View {
    let icon: String
    let titleKey: String
    let detailKey: String
    let color: Color
    var fileName: String?

    var body: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium) {
            Image(systemName: icon)
                .font(.system(size: 38, weight: .bold))
                .foregroundStyle(color)
                .accessibilityHidden(true)

            Text(LocalizedStringKey(titleKey))
                .font(TypographyTokens.cardTitle)
                .foregroundStyle(CrediWiseColors.textPrimary)
                .accessibilityIdentifier("upload.result.title")

            Text(LocalizedStringKey(detailKey))
                .font(TypographyTokens.body)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
                .accessibilityIdentifier("upload.result.detail")

            if let fileName {
                Text(verbatim: fileName)
                    .font(TypographyTokens.caption.weight(.semibold))
                    .foregroundStyle(CrediWiseColors.textPrimary)
            }
        }
        .padding(SpacingTokens.large)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
    }
}
