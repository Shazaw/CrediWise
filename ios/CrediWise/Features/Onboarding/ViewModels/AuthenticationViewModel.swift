import Combine
import Foundation

@MainActor
final class AuthenticationViewModel: ObservableObject {
    @Published var email = ""
    @Published var password = ""
    @Published var passwordConfirmation = ""
    @Published private(set) var state: AuthenticationViewState = .idle
    @Published private(set) var emailErrorKey: String?
    @Published private(set) var passwordErrorKey: String?
    @Published private(set) var confirmationErrorKey: String?

    let mode: AuthenticationMode

    private let repository: any AuthenticationRepository
    private let sessionManager: SessionManager

    init(
        mode: AuthenticationMode,
        repository: any AuthenticationRepository,
        sessionManager: SessionManager
    ) {
        self.mode = mode
        self.repository = repository
        self.sessionManager = sessionManager
    }

    var isLoading: Bool {
        state == .loading
    }

    func submit() async -> AuthenticationOutcome? {
        guard state != .loading else {
            return nil
        }
        guard validate() else {
            return nil
        }

        state = .loading
        let normalizedEmail = email.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()

        do {
            switch mode {
            case .registration:
                try await repository.register(email: normalizedEmail, password: password)
                state = .idle
                return .registered
            case .signIn:
                let tokens = try await repository.signIn(email: normalizedEmail, password: password)
                try await sessionManager.establish(tokens)
                state = .idle
                return .signedIn
            }
        } catch let error as AuthenticationRepositoryError {
            state = .error(errorKey(for: error))
            return nil
        } catch {
            state = .error("auth.error.unavailable")
            return nil
        }
    }

    @discardableResult
    private func validate() -> Bool {
        emailErrorKey = isValidEmail(email) ? nil : "auth.validation.email"
        passwordErrorKey = isValidPassword(password) ? nil : "auth.validation.password"
        confirmationErrorKey = nil

        if mode == .registration, passwordConfirmation != password {
            confirmationErrorKey = "auth.validation.password_confirmation"
        }

        state = .idle
        return emailErrorKey == nil && passwordErrorKey == nil && confirmationErrorKey == nil
    }

    private func isValidEmail(_ email: String) -> Bool {
        let normalized = email.trimmingCharacters(in: .whitespacesAndNewlines)
        return normalized.range(
            of: #"^[^\s@]+@[^\s@]+\.[^\s@]+$"#,
            options: .regularExpression
        ) != nil
    }

    private func isValidPassword(_ password: String) -> Bool {
        password.count >= 10 &&
            password.rangeOfCharacter(from: .letters) != nil &&
            password.rangeOfCharacter(from: .decimalDigits) != nil
    }

    private func errorKey(for error: AuthenticationRepositoryError) -> String {
        switch error {
        case .duplicateEmail:
            return "auth.error.duplicate_email"
        case .invalidCredentials:
            return "auth.error.invalid_credentials"
        case .rateLimited:
            return "auth.error.rate_limited"
        case .unavailable:
            return "auth.error.unavailable"
        }
    }
}
