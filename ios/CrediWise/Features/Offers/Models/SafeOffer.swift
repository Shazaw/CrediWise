struct SafeOffer: Equatable, Sendable {
    enum SafetyBand: String, Equatable, Sendable {
        case safe
        case caution
        case unsafe
    }

    enum ProviderStatus: String, Equatable, Sendable {
        case simulatedRegulatedProvider
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
        case annualFlat
    }

    struct Provider: Equatable, Sendable {
        let id: String
        let nameKey: String
        let status: ProviderStatus
    }

    struct CostBreakdown: Equatable, Sendable {
        let scheduledInterest: Int64
        let upfrontFees: Int64
        let financedFees: Int64
        let effectiveAnnualCostPercentage: Double?
        let totalScheduledRepayment: Int64
        let penaltyTermsKey: String
    }

    struct Warning: Equatable, Identifiable, Sendable {
        let id: String
        let code: String
        let titleKey: String
        let detailKey: String
    }

    struct ScheduledPayment: Equatable, Identifiable, Sendable {
        let id: Int
        let amount: Int64
    }

    struct Reason: Equatable, Identifiable, Sendable {
        let id: String
        let titleKey: String
        let detailKey: String
    }

    let assessmentID: String
    let offerID: String
    let suppliedRank: Int
    let isSafest: Bool
    let score: Int
    let band: SafetyBand
    let provider: Provider
    let principal: Int64
    let netAmountReceived: Int64
    let instalment: Int64
    let tenorMonths: Int
    let paymentFrequency: PaymentFrequency
    let amortizationMethod: AmortizationMethod
    let nominalAnnualRatePercentage: Double?
    let rateBasis: RateBasis?
    let dueDayOfMonth: Int
    let scheduledPayments: [ScheduledPayment]
    let costs: CostBreakdown
    let remainingEssentialCoverage: Int64
    let refinancingDependency: Bool
    let warnings: [Warning]
    let reasons: [Reason]
    let modelVersion: String
}
