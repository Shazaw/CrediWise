import Foundation

struct SafeOffer: Equatable, Sendable {
    enum SafetyBand: String, Equatable, Sendable {
        case safe
        case caution
        case unsafe
    }

    enum ProviderStatus: String, Equatable, Sendable {
        case regulated
        case unlisted
        case simulatedRegulatedProvider
    }

    enum OfferSource: String, Equatable, Sendable {
        case simulated
        case lenderAPI
        case manualLenderEntry
    }

    enum AmortizationMethod: String, Equatable, Sendable {
        case flat
        case reducingBalance
        case fixedSchedule
    }

    enum PaymentFrequency: String, Equatable, Sendable {
        case monthly
        case biweekly
        case weekly
    }

    enum RateBasis: String, Equatable, Sendable {
        case annualNominal
    }

    enum AffordabilityStatus: String, Equatable, Sendable {
        case survivable
        case strained
        case deficit
    }

    enum ConfidenceStatus: String, Equatable, Sendable {
        case high
        case medium
        case low
    }

    enum RatingStatus: String, Equatable, Sendable {
        case good
        case fair
        case poor
    }

    enum PenaltyBasis: String, Equatable, Sendable {
        case overdueInstalmentPerDay
        case overdueInstalmentPerMonth
        case fixed
    }

    struct Provider: Equatable, Sendable {
        let id: String
        let displayName: String
        let logoURL: URL?
        let status: ProviderStatus
    }

    struct Rate: Equatable, Sendable {
        let ratio: Decimal
        let displayPercentage: Double
    }

    struct LatePenaltyTerms: Equatable, Sendable {
        let triggerDays: Int
        let rate: Rate?
        let amount: Int64?
        let basis: PenaltyBasis
    }

    struct CostBreakdown: Equatable, Sendable {
        let scheduledInterest: Int64
        let upfrontFee: Int64
        let financedFee: Int64
        let serviceFee: Int64
        let adminFee: Int64
        let effectiveAnnualRate: Rate?
        let totalScheduledRepayment: Int64
        let latePenaltyTerms: LatePenaltyTerms?
    }

    struct Warning: Equatable, Identifiable, Sendable {
        var id: String { code }
        let code: String
        let titleKey: String
        let detailKey: String
        let usesGenericCopy: Bool
    }

    struct ScheduledPayment: Equatable, Identifiable, Sendable {
        var id: Int { period }
        let period: Int
        let paymentAmount: Int64
        let principalComponent: Int64
        let interestComponent: Int64
        let remainingBalance: Int64
    }

    struct Reason: Equatable, Identifiable, Sendable {
        var id: String { code }
        let code: String
        let description: String
        let titleKey: String
        let detailKey: String?
        let isKnown: Bool
    }

    struct EssentialExpenseCoverage: Equatable, Sendable {
        let amount: Int64
        let ratio: Decimal
        let displayPercentage: Double
    }

    let assessmentID: String
    let offerID: String
    let rank: Int
    let safeOfferScore: Decimal
    let band: SafetyBand
    let provider: Provider
    let offerSource: OfferSource
    let principalAmount: Int64
    let netDisbursedAmount: Int64
    let instalmentAmount: Int64
    let tenorMonths: Int
    let paymentFrequency: PaymentFrequency
    let amortizationMethod: AmortizationMethod
    let nominalRate: Rate?
    let nominalRateBasis: RateBasis
    let dueDayOfMonth: Int
    let paymentSchedule: [ScheduledPayment]
    let costs: CostBreakdown
    let affordabilityStatus: AffordabilityStatus
    let shockResilienceStatus: ConfidenceStatus
    let totalCostStatus: RatingStatus
    let timingStatus: RatingStatus
    let remainingEssentialExpenseCoverage: EssentialExpenseCoverage
    let refinancingDependency: Bool
    let warnings: [Warning]
    let reasons: [Reason]
    let explanation: String
    let modelVersion: String
    let configHash: String
    let simulationNotice: String?
}
