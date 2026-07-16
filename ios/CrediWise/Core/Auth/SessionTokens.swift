import Foundation

struct SessionTokens: Codable, Equatable, Sendable {
    let accessToken: String
    let refreshToken: String
}
