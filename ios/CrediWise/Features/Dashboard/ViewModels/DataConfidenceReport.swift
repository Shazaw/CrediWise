struct DataConfidenceReport: Equatable, Sendable {
    enum Band: String, Equatable, Sendable {
        case high
        case medium
        case low
    }

    enum EvidenceSource: String, Equatable, Sendable {
        case deterministic
        case localAIAssistance
    }

    enum AssistanceStatus: String, Equatable, Sendable {
        case available
        case unavailable
        case notUsed
    }

    struct Dimension: Equatable, Identifiable, Sendable {
        let id: String
        let titleKey: String
        let score: Int
    }

    struct Reason: Equatable, Identifiable, Sendable {
        let id: String
        let titleKey: String
        let detailKey: String
        let source: EvidenceSource
    }

    let score: Int
    let band: Band
    let dimensions: [Dimension]
    let reasons: [Reason]
    let recommendationKey: String
    let assistanceStatus: AssistanceStatus
    let modelVersion: String
}
