import SwiftUI

struct UploadPasswordCard: View {
    @Binding var password: String

    let invalid: Bool
    let onSubmit: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.standard) {
            Image(systemName: "lock.open.fill")
                .font(.system(size: 34, weight: .semibold))
                .foregroundStyle(CrediWiseColors.primary)
                .accessibilityHidden(true)

            Text("upload.password.title")
                .font(TypographyTokens.cardTitle)
                .foregroundStyle(CrediWiseColors.textPrimary)

            Text(invalid ? "upload.password.invalid" : "upload.password.detail")
                .font(TypographyTokens.body)
                .foregroundStyle(invalid ? CrediWiseColors.danger : CrediWiseColors.textPrimary)

            SecureField("upload.password.placeholder", text: $password)
                .textContentType(.password)
                .padding(SpacingTokens.standard)
                .background(CrediWiseColors.surfaceAlt)
                .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.button))
                .accessibilityIdentifier("upload.pdf_password")

            CTAButton(title: "upload.action.unlock") {
                let value = password
                password = ""
                onSubmit(value)
            }
            .disabled(password.isEmpty)
            .accessibilityIdentifier("upload.submit_password")
        }
        .padding(SpacingTokens.large)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
    }
}
