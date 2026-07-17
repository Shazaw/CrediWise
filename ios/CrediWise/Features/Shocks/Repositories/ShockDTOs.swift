import Foundation

struct ShockResultResponseDTO: Decodable {
    let assessmentID: UUID
    let resilienceScore: String?
    let resilienceScoreScope: ResilienceScoreScopeDTO
    let band: ShockResilienceBandDTO?
    let scenarios: [ShockScenarioResponseDTO]
    let proposedInstalment: Int64
    let requiredLiquidityBuffer: Int64
    let reasonCodes: [ReasonCodeDTO]
    let explanation: String
    let modelVersion: String
    let configHash: String

    enum CodingKeys: String, CodingKey {
        case assessmentID = "assessment_id"
        case resilienceScore = "resilience_score"
        case resilienceScoreScope = "resilience_score_scope"
        case band
        case scenarios
        case proposedInstalment = "proposed_instalment"
        case requiredLiquidityBuffer = "required_liquidity_buffer"
        case reasonCodes = "reason_codes"
        case explanation
        case modelVersion = "model_version"
        case configHash = "config_hash"
    }
}

enum ResilienceScoreScopeDTO: String, Decodable {
    case canonicalBattery = "CANONICAL_BATTERY"
}

struct ShockScenarioResponseDTO: Decodable {
    let scenarioType: ShockTypeDTO
    let parameters: [String: JSONValueDTO]
    let projectedCashFlow: Int64
    let minimumProjectedBalance: Int64
    let deficitAmount: Int64
    let affordabilityStatus: AffordabilityStatusDTO
    let resilienceScoreContribution: String
    let requiredLiquidityBuffer: Int64
    let requiredBufferBreached: Bool
    let projectionPoints: [ProjectionPointResponseDTO]

    enum CodingKeys: String, CodingKey {
        case scenarioType = "scenario_type"
        case parameters
        case projectedCashFlow = "projected_cash_flow"
        case minimumProjectedBalance = "minimum_projected_balance"
        case deficitAmount = "deficit_amount"
        case affordabilityStatus = "affordability_status"
        case resilienceScoreContribution = "resilience_score_contribution"
        case requiredLiquidityBuffer = "required_liquidity_buffer"
        case requiredBufferBreached = "required_buffer_breached"
        case projectionPoints = "projection_points"
    }
}

struct ProjectionPointResponseDTO: Decodable {
    let sequence: Int
    let dayOfMonth: Int
    let eventType: String
    let amount: Int64
    let projectedBalance: Int64

    enum CodingKeys: String, CodingKey {
        case sequence
        case dayOfMonth = "day_of_month"
        case eventType = "event_type"
        case amount
        case projectedBalance = "projected_balance"
    }
}

struct ReasonCodeDTO: Decodable {
    let code: String
    let description: String
}

enum ShockResilienceBandDTO: String, Decodable {
    case strong = "STRONG"
    case moderate = "MODERATE"
    case fragile = "FRAGILE"
}

enum ShockTypeDTO: String, Decodable {
    case incomeDrop10 = "INCOME_DROP_10"
    case incomeDrop20 = "INCOME_DROP_20"
    case incomeDrop30 = "INCOME_DROP_30"
    case delayedIncome = "DELAYED_INCOME"
    case emergencyExpense = "EMERGENCY_EXPENSE"
    case incomeSourceLoss = "INCOME_SOURCE_LOSS"
    case weakestMonthReplay = "WEAKEST_MONTH_REPLAY"
    case custom = "CUSTOM"
}

enum AffordabilityStatusDTO: String, Decodable {
    case survivable = "SURVIVABLE"
    case strained = "STRAINED"
    case deficit = "DEFICIT"
}

indirect enum JSONValueDTO: Decodable {
    case string(String)
    case number(Decimal)
    case boolean(Bool)
    case array([JSONValueDTO])
    case object([String: JSONValueDTO])
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .boolean(value)
        } else if let value = try? container.decode(Decimal.self) {
            self = .number(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([JSONValueDTO].self) {
            self = .array(value)
        } else if let value = try? container.decode([String: JSONValueDTO].self) {
            self = .object(value)
        } else {
            throw DecodingError.typeMismatch(
                JSONValueDTO.self,
                .init(codingPath: decoder.codingPath, debugDescription: "Unsupported parameter value")
            )
        }
    }
}

struct SimulateShockRequestDTO: Encodable {
    let incomeDropPercentage: Int
    let emergencyExpense: Int64
    let proposedInstalment: Int64

    enum CodingKeys: String, CodingKey {
        case incomeDropPercentage = "income_drop_pct"
        case emergencyExpense = "emergency_expense"
        case proposedInstalment = "proposed_instalment"
    }
}
