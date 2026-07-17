import Foundation

struct OffersListResponseDTO: Decodable {
    let assessmentID: UUID
    let offers: [OfferResponseDTO]

    enum CodingKeys: String, CodingKey {
        case assessmentID = "assessment_id"
        case offers
    }
}

struct OfferResponseDTO: Decodable {
    let offerID: UUID
    let lender: LenderResponseDTO
    let offerSource: OfferSourceDTO
    let principalAmount: Int64
    let netDisbursedAmount: Int64
    let instalmentAmount: Int64
    let tenorMonths: Int
    let amortizationMethod: AmortizationMethodDTO
    let nominalRate: OfferRequiredNullableDTO<String>
    let nominalRateBasis: NominalRateBasisDTO
    let effectiveAnnualRate: OfferRequiredNullableDTO<String>
    let interestAmount: Int64
    let upfrontFee: Int64
    let financedFee: Int64
    let serviceFee: Int64
    let adminFee: Int64
    let totalRepayment: Int64
    let latePenaltyTerms: OfferRequiredNullableDTO<LatePenaltyTermsResponseDTO>
    let paymentSchedule: [PaymentScheduleEntryResponseDTO]
    let dueDate: Int
    let frequency: FrequencyDTO
    let safeOfferScore: String
    let safetyBand: OfferSafetyBandDTO
    let rank: Int
    let affordabilityStatus: OfferAffordabilityStatusDTO
    let shockResilienceStatus: ConfidenceStatusDTO
    let totalCostStatus: OfferRatingDTO
    let timingStatus: OfferRatingDTO
    let warningFlags: [String]
    let refinancingDependency: Bool
    let remainingEssentialExpenseCoverage: EssentialExpenseCoverageResponseDTO
    let reasonCodes: [OfferReasonCodeDTO]
    let explanation: String
    let modelVersion: String
    let configHash: String
    let simulationNotice: OfferRequiredNullableDTO<String>

    enum CodingKeys: String, CodingKey {
        case offerID = "offer_id"
        case lender
        case offerSource = "offer_source"
        case principalAmount = "principal_amount"
        case netDisbursedAmount = "net_disbursed_amount"
        case instalmentAmount = "instalment_amount"
        case tenorMonths = "tenor_months"
        case amortizationMethod = "amortization_method"
        case nominalRate = "nominal_rate"
        case nominalRateBasis = "nominal_rate_basis"
        case effectiveAnnualRate = "effective_annual_rate"
        case interestAmount = "interest_amount"
        case upfrontFee = "upfront_fee"
        case financedFee = "financed_fee"
        case serviceFee = "service_fee"
        case adminFee = "admin_fee"
        case totalRepayment = "total_repayment"
        case latePenaltyTerms = "late_penalty_terms"
        case paymentSchedule = "payment_schedule"
        case dueDate = "due_date"
        case frequency
        case safeOfferScore = "safe_offer_score"
        case safetyBand = "safety_band"
        case rank
        case affordabilityStatus = "affordability_status"
        case shockResilienceStatus = "shock_resilience_status"
        case totalCostStatus = "total_cost_status"
        case timingStatus = "timing_status"
        case warningFlags = "warning_flags"
        case refinancingDependency = "refinancing_dependency"
        case remainingEssentialExpenseCoverage = "remaining_essential_expense_coverage"
        case reasonCodes = "reason_codes"
        case explanation
        case modelVersion = "model_version"
        case configHash = "config_hash"
        case simulationNotice = "simulation_notice"
    }
}

struct LenderResponseDTO: Decodable {
    let lenderID: UUID
    let name: String
    let regulatoryStatus: ProviderStatusDTO
    let logoURL: OfferRequiredNullableDTO<String>

    enum CodingKeys: String, CodingKey {
        case lenderID = "lender_id"
        case name
        case regulatoryStatus = "regulatory_status"
        case logoURL = "logo_url"
    }
}

struct LatePenaltyTermsResponseDTO: Decodable {
    let triggerDays: Int
    let rate: OfferRequiredNullableDTO<String>
    let amount: OfferRequiredNullableDTO<Int64>
    let basis: PenaltyBasisDTO

    enum CodingKeys: String, CodingKey {
        case triggerDays = "trigger_days"
        case rate
        case amount
        case basis
    }
}

struct PaymentScheduleEntryResponseDTO: Decodable {
    let period: Int
    let paymentAmount: Int64
    let principalComponent: Int64
    let interestComponent: Int64
    let remainingBalance: Int64

    enum CodingKeys: String, CodingKey {
        case period
        case paymentAmount = "payment_amount"
        case principalComponent = "principal_component"
        case interestComponent = "interest_component"
        case remainingBalance = "remaining_balance"
    }
}

struct EssentialExpenseCoverageResponseDTO: Decodable {
    let amount: Int64
    let ratio: String
}

struct OfferReasonCodeDTO: Decodable {
    let code: String
    let description: String
}

enum OfferAffordabilityStatusDTO: String, Decodable {
    case survivable = "SURVIVABLE"
    case strained = "STRAINED"
    case deficit = "DEFICIT"
}

enum OfferSourceDTO: String, Decodable {
    case simulated = "SIMULATED"
    case lenderAPI = "LENDER_API"
    case manualLenderEntry = "MANUAL_LENDER_ENTRY"
}

enum ProviderStatusDTO: String, Decodable {
    case regulated = "REGULATED"
    case unlisted = "UNLISTED"
    case simulatedRegulatedProvider = "SIMULATED_REGULATED_PROVIDER"
}

enum AmortizationMethodDTO: String, Decodable {
    case flat = "FLAT"
    case reducingBalance = "REDUCING_BALANCE"
    case fixedSchedule = "FIXED_SCHEDULE"
}

enum NominalRateBasisDTO: String, Decodable {
    case annualNominal = "ANNUAL_NOMINAL"
}

enum FrequencyDTO: String, Decodable {
    case monthly = "MONTHLY"
    case biweekly = "BIWEEKLY"
    case weekly = "WEEKLY"
}

enum OfferSafetyBandDTO: String, Decodable {
    case safe = "SAFE"
    case caution = "CAUTION"
    case unsafe = "UNSAFE"
}

enum ConfidenceStatusDTO: String, Decodable {
    case high = "HIGH"
    case medium = "MEDIUM"
    case low = "LOW"
}

enum OfferRatingDTO: String, Decodable {
    case good = "GOOD"
    case fair = "FAIR"
    case poor = "POOR"
}

enum PenaltyBasisDTO: String, Decodable {
    case overdueInstalmentPerDay = "OVERDUE_INSTALMENT_PER_DAY"
    case overdueInstalmentPerMonth = "OVERDUE_INSTALMENT_PER_MONTH"
    case fixed = "FIXED"
}

struct OfferRequiredNullableDTO<Value: Decodable>: Decodable {
    let value: Value?

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        value = container.decodeNil() ? nil : try container.decode(Value.self)
    }
}
