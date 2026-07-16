enum AuthenticationMode: Equatable {
    case registration
    case signIn

    var titleKey: String {
        switch self {
        case .registration:
            return "auth.registration.title"
        case .signIn:
            return "auth.sign_in.title"
        }
    }

    var subtitleKey: String {
        switch self {
        case .registration:
            return "auth.registration.subtitle"
        case .signIn:
            return "auth.sign_in.subtitle"
        }
    }

    var submitKey: String {
        switch self {
        case .registration:
            return "auth.registration.submit"
        case .signIn:
            return "auth.sign_in.submit"
        }
    }
}
