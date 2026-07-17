import Foundation

enum ShockMapper {
    static func map(
        _ response: ShockResultResponseDTO,
        submittedParameters: ShockSimulationParameters? = nil
    ) throws -> ShockAssessment {
        ShockAssessment(
            assessmentID: response.assessmentID.uuidString,
            resilienceScore: try decimal(response.resilienceScore),
            resilienceScoreScope: map(response.resilienceScoreScope),
            band: response.band.map(map),
            scenarios: try response.scenarios.enumerated().map { index, scenario in
                try mapScenario(index, scenario)
            },
            proposedInstalment: response.proposedInstalment,
            requiredLiquidityBuffer: response.requiredLiquidityBuffer,
            reasons: response.reasonCodes.map(mapReason),
            explanation: response.explanation,
            modelVersion: response.modelVersion,
            configHash: response.configHash,
            submittedParameters: submittedParameters
        )
    }

    private static func mapScenario(
        _ index: Int,
        _ response: ShockScenarioResponseDTO
    ) throws -> ShockAssessment.Scenario {
        let kind = map(response.scenarioType)
        return ShockAssessment.Scenario(
            id: "\(response.scenarioType.rawValue)-\(index)",
            kind: kind,
            parameters: response.parameters.mapValues { map($0) },
            projectedCashFlow: response.projectedCashFlow,
            minimumProjectedBalance: response.minimumProjectedBalance,
            deficitAmount: response.deficitAmount,
            status: map(response.affordabilityStatus),
            resilienceScoreContribution: try requiredDecimal(response.resilienceScoreContribution),
            requiredLiquidityBuffer: response.requiredLiquidityBuffer,
            requiredBufferBreached: response.requiredBufferBreached,
            projectionPoints: response.projectionPoints.sorted { $0.sequence < $1.sequence }
                .enumerated().map { pointIndex, point in
                let eventPresentation = eventPresentation(point.eventType)
                return .init(
                    id: "\(response.scenarioType.rawValue)-\(point.sequence)-\(pointIndex)",
                    sequence: point.sequence,
                    dayOfMonth: point.dayOfMonth,
                    eventType: point.eventType,
                    eventLabelKey: eventPresentation.key,
                    isKnownEventType: eventPresentation.isKnown,
                    amount: point.amount,
                    projectedBalance: point.projectedBalance
                )
            }
        )
    }

    private static func decimal(_ value: String?) throws -> Decimal? {
        guard let value else { return nil }
        return try requiredDecimal(value)
    }

    private static func requiredDecimal(_ value: String) throws -> Decimal {
        guard let result = Decimal(string: value, locale: Locale(identifier: "en_US_POSIX")) else {
            throw ShockRepositoryError.unavailable
        }
        return result
    }

    private static func map(_ value: ShockResilienceBandDTO) -> ShockAssessment.ResilienceBand {
        switch value {
        case .strong: return .strong
        case .moderate: return .moderate
        case .fragile: return .fragile
        }
    }

    private static func map(
        _ value: ResilienceScoreScopeDTO
    ) -> ShockAssessment.ResilienceScoreScope {
        switch value {
        case .canonicalBattery: return .canonicalBattery
        }
    }

    private static func map(_ value: ShockTypeDTO) -> ShockAssessment.ScenarioKind {
        switch value {
        case .incomeDrop10: return .incomeDrop10
        case .incomeDrop20: return .incomeDrop20
        case .incomeDrop30: return .incomeDrop30
        case .delayedIncome: return .delayedIncome
        case .emergencyExpense: return .emergencyExpense
        case .incomeSourceLoss: return .incomeSourceLoss
        case .weakestMonthReplay: return .weakestMonthReplay
        case .custom: return .custom
        }
    }

    private static func map(_ value: AffordabilityStatusDTO) -> ShockAssessment.AffordabilityStatus {
        switch value {
        case .survivable: return .survivable
        case .strained: return .strained
        case .deficit: return .deficit
        }
    }

    private static func map(_ value: JSONValueDTO) -> ShockAssessment.ParameterValue {
        switch value {
        case let .string(value): return .string(value)
        case let .number(value): return .number(value)
        case let .boolean(value): return .boolean(value)
        case let .array(value): return .array(value.map { map($0) })
        case let .object(value): return .object(value.mapValues { map($0) })
        case .null: return .null
        }
    }

    private static func mapReason(_ value: ReasonCodeDTO) -> ShockAssessment.Reason {
        let keys: (String, String)?
        switch value.code {
        case "SHOCK_RESILIENCE_STRONG":
            keys = ("shocks.reason.resilience_strong", "shocks.reason.resilience_strong.detail")
        case "SHOCK_RESILIENCE_MODERATE":
            keys = ("shocks.reason.resilience_moderate", "shocks.reason.resilience_moderate.detail")
        case "SHOCK_RESILIENCE_FRAGILE":
            keys = ("shocks.reason.resilience_fragile", "shocks.reason.resilience_fragile.detail")
        case "SHOCK_REQUIRED_BUFFER_COVERAGE":
            keys = ("shocks.reason.required_buffer", "shocks.reason.required_buffer.detail")
        case "SHOCK_TEMPORAL_LIQUIDITY":
            keys = ("shocks.reason.temporal_liquidity", "shocks.reason.temporal_liquidity.detail")
        case let code where code.hasPrefix("SHOCK_DEFICIT_"):
            keys = ("shocks.reason.deficit", "shocks.reason.deficit.detail")
        default: keys = nil
        }
        return .init(
            code: value.code,
            description: value.description,
            titleKey: keys?.0 ?? "shocks.reason.unknown",
            detailKey: keys?.1,
            isKnown: keys != nil
        )
    }

    private static func eventPresentation(_ value: String) -> (key: String, isKnown: Bool) {
        let key: String?
        switch value {
        case "OPENING_BALANCE": key = "shocks.event.opening_balance"
        case "INCOME": key = "shocks.event.income"
        case "ESSENTIAL_EXPENSE": key = "shocks.event.essential_expense"
        case "PROPOSED_INSTALMENT": key = "shocks.event.proposed_instalment"
        case "EMERGENCY_EXPENSE": key = "shocks.event.emergency_expense"
        case "MONTH_END_RECONCILIATION": key = "shocks.event.month_end_reconciliation"
        default: key = nil
        }
        return (key ?? "shocks.event.unknown", key != nil)
    }
}
