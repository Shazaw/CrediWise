import Foundation
import SwiftUI

struct UploadFileCard: View {
    let file: SelectedUploadFile
    let progress: Double?

    var body: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.standard) {
            HStack(spacing: SpacingTokens.medium) {
                Image(systemName: "doc.fill")
                    .font(.title2)
                    .foregroundStyle(CrediWiseColors.primary)
                    .accessibilityHidden(true)

                VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                    Text(verbatim: file.fileName)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(CrediWiseColors.textPrimary)
                        .lineLimit(2)
                        .accessibilityIdentifier("upload.file.name")

                    Text(verbatim: "\(formattedSize) | \(file.mimeType)")
                        .font(TypographyTokens.caption)
                        .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.65))
                }
            }

            if let progress {
                ProgressView(value: progress)
                    .tint(CrediWiseColors.primary)
                    .accessibilityLabel(Text("upload.progress.accessibility_label"))
                    .accessibilityValue(Text(progress, format: .percent.precision(.fractionLength(0))))

                Text("upload.progress.detail")
                    .font(TypographyTokens.caption)
                    .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.7))
            }
        }
        .padding(SpacingTokens.large)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("upload.file")
    }

    private var formattedSize: String {
        ByteCountFormatter.string(fromByteCount: file.byteCount, countStyle: .file)
    }
}
