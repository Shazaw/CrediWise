import SwiftUI

struct ProcessingChecklist: View {
    let status: DocumentProcessingStatus

    var body: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.standard) {
            Text("upload.processing.title")
                .font(TypographyTokens.cardTitle)
                .foregroundStyle(CrediWiseColors.textPrimary)

            stageRow(index: 0, titleKey: "upload.stage.received", detailKey: "upload.stage.received.detail")
            stageRow(index: 1, titleKey: "upload.stage.security", detailKey: "upload.stage.security.detail")
            stageRow(index: 2, titleKey: "upload.stage.extraction", detailKey: "upload.stage.extraction.detail")
            stageRow(index: 3, titleKey: "upload.stage.verification", detailKey: "upload.stage.verification.detail")
            stageRow(index: 4, titleKey: "upload.stage.analysis", detailKey: "upload.stage.analysis.detail")
        }
        .padding(SpacingTokens.large)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        .accessibilityIdentifier("upload.processing.checklist")
    }

    private func stageRow(index: Int, titleKey: String, detailKey: String) -> some View {
        let isFailed = failedStage == index
        let isComplete = status == .complete || index < currentStage
        let isActive = index == currentStage && !isFailed && status != .complete

        return HStack(alignment: .top, spacing: SpacingTokens.medium) {
            Image(systemName: iconName(isFailed: isFailed, isComplete: isComplete, isActive: isActive))
                .font(.title3.weight(.semibold))
                .foregroundStyle(iconColor(isFailed: isFailed, isComplete: isComplete, isActive: isActive))
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                Text(LocalizedStringKey(titleKey))
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(CrediWiseColors.textPrimary)

                Text(LocalizedStringKey(detailKey))
                    .font(TypographyTokens.caption)
                    .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.68))

                if isFailed {
                    Text("upload.stage.failed")
                        .font(TypographyTokens.caption.weight(.semibold))
                        .foregroundStyle(CrediWiseColors.danger)
                } else if isComplete {
                    Text("upload.stage.complete")
                        .font(TypographyTokens.caption.weight(.semibold))
                        .foregroundStyle(CrediWiseColors.success)
                } else if isActive {
                    Text("upload.stage.in_progress")
                        .font(TypographyTokens.caption.weight(.semibold))
                        .foregroundStyle(CrediWiseColors.primary)
                }
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("upload.processing.stage.\(index)")
    }

    private var currentStage: Int {
        switch status {
        case .uploaded, .duplicateReused:
            return 0
        case .securityCheck, .rejectedSecurity, .validationFailed:
            return 1
        case .extracting, .unsupportedFormat:
            return 2
        case .verifying, .reviewPending, .humanReview:
            return 3
        case .normalizing, .analyzing:
            return 4
        case .complete:
            return 5
        }
    }

    private var failedStage: Int? {
        switch status {
        case .rejectedSecurity, .validationFailed:
            return 1
        case .unsupportedFormat:
            return 2
        default:
            return nil
        }
    }

    private func iconName(isFailed: Bool, isComplete: Bool, isActive: Bool) -> String {
        if isFailed {
            return "xmark.octagon.fill"
        }
        if isComplete {
            return "checkmark.circle.fill"
        }
        return isActive ? "circle.dotted" : "circle"
    }

    private func iconColor(isFailed: Bool, isComplete: Bool, isActive: Bool) -> Color {
        if isFailed {
            return CrediWiseColors.danger
        }
        if isComplete {
            return CrediWiseColors.success
        }
        return isActive ? CrediWiseColors.primary : CrediWiseColors.textPrimary.opacity(0.28)
    }
}
