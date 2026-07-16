import SwiftUI

struct UploadSourcePickerCard: View {
    let sourceType: DocumentSourceType?
    let onSelect: (DocumentSourceType) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.small) {
            Text("upload.source.title")
                .font(TypographyTokens.cardTitle)
                .foregroundStyle(CrediWiseColors.textPrimary)

            Text("upload.source.detail")
                .font(TypographyTokens.body)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))

            Picker(
                "upload.source.accessibility_label",
                selection: Binding(
                    get: { sourceType },
                    set: { selectedSource in
                        if let selectedSource {
                            onSelect(selectedSource)
                        }
                    }
                )
            ) {
                Text("upload.source.screenshot")
                    .tag(Optional(DocumentSourceType.screenshot))
                Text("upload.source.photo")
                    .tag(Optional(DocumentSourceType.photo))
            }
            .pickerStyle(.segmented)
            .accessibilityIdentifier("upload.source_type")
        }
        .padding(SpacingTokens.large)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
    }
}
