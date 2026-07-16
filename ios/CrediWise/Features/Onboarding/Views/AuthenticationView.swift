import SwiftUI

struct AuthenticationView: View {
    @StateObject private var viewModel: AuthenticationViewModel
    @FocusState private var focusedField: Field?
    @AccessibilityFocusState private var focusedError: ErrorField?

    let onRegistered: () -> Void
    let onSignedIn: () -> Void
    let onSwitchMode: () -> Void

    init(
        viewModel: AuthenticationViewModel,
        onRegistered: @escaping () -> Void,
        onSignedIn: @escaping () -> Void,
        onSwitchMode: @escaping () -> Void
    ) {
        _viewModel = StateObject(wrappedValue: viewModel)
        self.onRegistered = onRegistered
        self.onSignedIn = onSignedIn
        self.onSwitchMode = onSwitchMode
    }

    var body: some View {
        ZStack {
            CrediWiseColors.primaryDark.ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: SpacingTokens.large) {
                    header
                    formCard
                    DisclaimerFooter(foregroundColor: CrediWiseColors.textOnPrimary.opacity(0.78))
                }
                .padding(.horizontal, SpacingTokens.large)
                .padding(.vertical, SpacingTokens.xLarge)
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .tint(CrediWiseColors.textOnPrimary)
        .accessibilityIdentifier("auth.screen")
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.small) {
            Image(systemName: "person.badge.key.fill")
                .font(.system(size: 34, weight: .bold))
                .foregroundStyle(CrediWiseColors.accent)
                .accessibilityHidden(true)

            Text(LocalizedStringKey(viewModel.mode.titleKey))
                .font(TypographyTokens.hero)
                .foregroundStyle(CrediWiseColors.textOnPrimary)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityIdentifier("auth.title")

            Text(LocalizedStringKey(viewModel.mode.subtitleKey))
                .font(TypographyTokens.body)
                .foregroundStyle(CrediWiseColors.textOnPrimary.opacity(0.82))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var formCard: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.standard) {
            emailField
            passwordField

            if viewModel.mode == .registration {
                confirmationField
            }

            if case let .error(errorKey) = viewModel.state {
                Text(LocalizedStringKey(errorKey))
                    .font(TypographyTokens.caption)
                    .foregroundStyle(CrediWiseColors.danger)
                    .accessibilityIdentifier("auth.server_error")
                    .accessibilityFocused($focusedError, equals: .server)
            }

            CTAButton(title: LocalizedStringKey(viewModel.mode.submitKey)) {
                submit()
            }
            .disabled(viewModel.isLoading)
            .accessibilityIdentifier("auth.submit")

            Button(action: onSwitchMode) {
                Text(
                    LocalizedStringKey(
                        viewModel.mode == .registration
                            ? "auth.registration.switch"
                            : "auth.sign_in.switch"
                    )
                )
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(CrediWiseColors.primary)
                    .frame(maxWidth: .infinity)
            }
            .accessibilityIdentifier("auth.switch_mode")

            if viewModel.isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity)
                    .tint(CrediWiseColors.primary)
                    .accessibilityLabel(Text("auth.loading"))
            }
        }
        .padding(SpacingTokens.large)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
    }

    private var emailField: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
            Text("auth.email.label")
                .font(.subheadline.weight(.semibold))

            TextField("auth.email.placeholder", text: $viewModel.email)
                .textInputAutocapitalization(.never)
                .keyboardType(.emailAddress)
                .textContentType(.emailAddress)
                .submitLabel(.next)
                .focused($focusedField, equals: .email)
                .onSubmit { focusedField = .password }
                .authFieldStyle()
                .accessibilityIdentifier("auth.email")

            validationText(viewModel.emailErrorKey, identifier: "auth.email_error")
        }
    }

    private var passwordField: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
            Text("auth.password.label")
                .font(.subheadline.weight(.semibold))

            SecureField("auth.password.placeholder", text: $viewModel.password)
                .textContentType(viewModel.mode == .registration ? .newPassword : .password)
                .submitLabel(viewModel.mode == .registration ? .next : .go)
                .focused($focusedField, equals: .password)
                .onSubmit {
                    if viewModel.mode == .registration {
                        focusedField = .confirmation
                    } else {
                        submit()
                    }
                }
                .authFieldStyle()
                .accessibilityIdentifier("auth.password")

            validationText(viewModel.passwordErrorKey, identifier: "auth.password_error")
        }
    }

    private var confirmationField: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
            Text("auth.password_confirmation.label")
                .font(.subheadline.weight(.semibold))

            SecureField("auth.password_confirmation.placeholder", text: $viewModel.passwordConfirmation)
                .textContentType(.newPassword)
                .submitLabel(.go)
                .focused($focusedField, equals: .confirmation)
                .onSubmit { submit() }
                .authFieldStyle()
                .accessibilityIdentifier("auth.password_confirmation")

            validationText(
                viewModel.confirmationErrorKey,
                identifier: "auth.password_confirmation_error"
            )
        }
    }

    @ViewBuilder
    private func validationText(_ key: String?, identifier: String) -> some View {
        if let key {
            Text(LocalizedStringKey(key))
                .font(TypographyTokens.caption)
                .foregroundStyle(CrediWiseColors.danger)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityIdentifier(identifier)
                .accessibilityFocused($focusedError, equals: errorField(for: identifier))
        }
    }

    private func submit() {
        Task {
            let outcome = await viewModel.submit()
            switch outcome {
            case .registered:
                onRegistered()
            case .signedIn:
                onSignedIn()
            case nil:
                focusFirstError()
            }
        }
    }

    private func focusFirstError() {
        if viewModel.emailErrorKey != nil {
            focusedError = .email
        } else if viewModel.passwordErrorKey != nil {
            focusedError = .password
        } else if viewModel.confirmationErrorKey != nil {
            focusedError = .confirmation
        } else if case .error = viewModel.state {
            focusedError = .server
        }
    }

    private func errorField(for identifier: String) -> ErrorField {
        switch identifier {
        case "auth.email_error":
            return .email
        case "auth.password_error":
            return .password
        default:
            return .confirmation
        }
    }

    private enum Field {
        case email
        case password
        case confirmation
    }

    private enum ErrorField: Hashable {
        case email
        case password
        case confirmation
        case server
    }
}

private extension View {
    func authFieldStyle() -> some View {
        padding(SpacingTokens.medium)
            .background(CrediWiseColors.surfaceAlt)
            .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.chip))
            .overlay {
                RoundedRectangle(cornerRadius: RadiusTokens.chip)
                    .stroke(CrediWiseColors.primary.opacity(0.2), lineWidth: 1)
            }
    }
}
