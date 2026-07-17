import Foundation

enum OfferMapper {
    static let exactSimulationNotice =
        "SIMULATED offer for comparison only; not a real provider endorsement."

    static func map(_ response: OffersListResponseDTO) throws -> [SafeOffer] {
        try response.offers.map { try map($0, assessmentID: response.assessmentID) }
    }

    static func map(_ response: OfferResponseDTO, assessmentID: UUID) throws -> SafeOffer {
        let source = map(response.offerSource)
        let providerStatus = map(response.lender.regulatoryStatus)
        try validateSource(source, providerStatus, response.simulationNotice.value)
        return SafeOffer(
            assessmentID: assessmentID.uuidString, offerID: response.offerID.uuidString,
            rank: response.rank, safeOfferScore: try decimal(response.safeOfferScore),
            band: map(response.safetyBand), provider: mapProvider(response.lender, providerStatus),
            offerSource: source, principalAmount: response.principalAmount,
            netDisbursedAmount: response.netDisbursedAmount,
            instalmentAmount: response.instalmentAmount, tenorMonths: response.tenorMonths,
            paymentFrequency: map(response.frequency), amortizationMethod: map(response.amortizationMethod),
            nominalRate: try rate(response.nominalRate.value),
            nominalRateBasis: .annualNominal, dueDayOfMonth: response.dueDate,
            paymentSchedule: mapSchedule(response.paymentSchedule), costs: try mapCosts(response),
            affordabilityStatus: map(response.affordabilityStatus),
            shockResilienceStatus: map(response.shockResilienceStatus),
            totalCostStatus: map(response.totalCostStatus), timingStatus: map(response.timingStatus),
            remainingEssentialExpenseCoverage: try coverage(response.remainingEssentialExpenseCoverage),
            refinancingDependency: response.refinancingDependency,
            warnings: response.warningFlags.map(mapWarning), reasons: response.reasonCodes.map(mapReason),
            explanation: response.explanation, modelVersion: response.modelVersion,
            configHash: response.configHash,
            simulationNotice: response.simulationNotice.value
        )
    }

    private static func validateSource(
        _ source: SafeOffer.OfferSource,
        _ providerStatus: SafeOffer.ProviderStatus,
        _ notice: String?
    ) throws {
        let isSimulated = source == .simulated
        let hasValidNotice = isSimulated ? notice == exactSimulationNotice : notice == nil
        guard isSimulated == (providerStatus == .simulatedRegulatedProvider),
              hasValidNotice else {
            throw OfferRepositoryError.unavailable
        }
    }

    private static func mapProvider(
        _ value: LenderResponseDTO,
        _ status: SafeOffer.ProviderStatus
    ) -> SafeOffer.Provider {
        .init(
            id: value.lenderID.uuidString, displayName: value.name,
            logoURL: logoURL(value.logoURL.value), status: status
        )
    }

    private static func mapSchedule(
        _ values: [PaymentScheduleEntryResponseDTO]
    ) -> [SafeOffer.ScheduledPayment] {
        values.map {
            .init(
                period: $0.period, paymentAmount: $0.paymentAmount,
                principalComponent: $0.principalComponent,
                interestComponent: $0.interestComponent, remainingBalance: $0.remainingBalance
            )
        }
    }

    private static func mapCosts(_ value: OfferResponseDTO) throws -> SafeOffer.CostBreakdown {
        .init(
            scheduledInterest: value.interestAmount,
            upfrontFee: value.upfrontFee, financedFee: value.financedFee,
            serviceFee: value.serviceFee, adminFee: value.adminFee,
            effectiveAnnualRate: try rate(value.effectiveAnnualRate.value),
            totalScheduledRepayment: value.totalRepayment,
            latePenaltyTerms: try value.latePenaltyTerms.value.map { try map($0) }
        )
    }

    private static func decimal(_ value: String) throws -> Decimal {
        guard let result = Decimal(string: value, locale: Locale(identifier: "en_US_POSIX")) else {
            throw OfferRepositoryError.unavailable
        }
        return result
    }

    private static func rate(_ value: String?) throws -> SafeOffer.Rate? {
        guard let value else { return nil }
        let ratio = try decimal(value)
        return .init(
            ratio: ratio,
            displayPercentage: NSDecimalNumber(decimal: ratio * 100).doubleValue
        )
    }

    private static func coverage(
        _ value: EssentialExpenseCoverageResponseDTO
    ) throws -> SafeOffer.EssentialExpenseCoverage {
        let ratio = try decimal(value.ratio)
        return .init(
            amount: value.amount,
            ratio: ratio,
            displayPercentage: NSDecimalNumber(decimal: ratio * 100).doubleValue
        )
    }

    private static func logoURL(_ value: String?) -> URL? {
        guard let value else { return nil }
        guard let url = URL(string: value),
              url.scheme?.lowercased() == "https",
              url.host?.isEmpty == false else { return nil }
        return url
    }

    private static func map(_ value: LatePenaltyTermsResponseDTO) throws -> SafeOffer.LatePenaltyTerms {
        .init(
            triggerDays: value.triggerDays,
            rate: try rate(value.rate.value),
            amount: value.amount.value,
            basis: map(value.basis)
        )
    }

    private static func mapWarning(_ code: String) -> SafeOffer.Warning {
        let keys: (String, String)?
        switch code {
        case "EXCEEDS_SAFE_INSTALMENT":
            keys = ("offers.warning.safe_instalment.title", "offers.warning.safe_instalment.detail")
        case "EXCEEDS_SAFE_PRINCIPAL":
            keys = ("offers.warning.safe_principal.title", "offers.warning.safe_principal.detail")
        case "MISSING_FEE_DISCLOSURE":
            keys = ("offers.warning.fee_disclosure.title", "offers.warning.fee_disclosure.detail")
        case "REFINANCING_DEPENDENCY_RISK":
            keys = ("offers.warning.refinancing_dependency.title", "offers.warning.refinancing_dependency.detail")
        default:
            keys = nil
        }
        return .init(
            code: code,
            titleKey: keys?.0 ?? "offers.warning.unknown.title",
            detailKey: keys?.1 ?? "offers.warning.unknown.detail",
            usesGenericCopy: keys == nil
        )
    }

    private static func map(_ value: OfferSafetyBandDTO) -> SafeOffer.SafetyBand {
        switch value {
        case .safe: return .safe
        case .caution: return .caution
        case .unsafe: return .unsafe
        }
    }

    private static func map(_ value: ProviderStatusDTO) -> SafeOffer.ProviderStatus {
        switch value {
        case .regulated: return .regulated
        case .unlisted: return .unlisted
        case .simulatedRegulatedProvider: return .simulatedRegulatedProvider
        }
    }

    private static func map(_ value: OfferSourceDTO) -> SafeOffer.OfferSource {
        switch value {
        case .simulated: return .simulated
        case .lenderAPI: return .lenderAPI
        case .manualLenderEntry: return .manualLenderEntry
        }
    }

    private static func map(_ value: FrequencyDTO) -> SafeOffer.PaymentFrequency {
        switch value {
        case .monthly: return .monthly
        case .biweekly: return .biweekly
        case .weekly: return .weekly
        }
    }

    private static func map(_ value: AmortizationMethodDTO) -> SafeOffer.AmortizationMethod {
        switch value {
        case .flat: return .flat
        case .reducingBalance: return .reducingBalance
        case .fixedSchedule: return .fixedSchedule
        }
    }

    private static func map(
        _ value: OfferAffordabilityStatusDTO
    ) -> SafeOffer.AffordabilityStatus {
        switch value {
        case .survivable: return .survivable
        case .strained: return .strained
        case .deficit: return .deficit
        }
    }

    private static func map(_ value: ConfidenceStatusDTO) -> SafeOffer.ConfidenceStatus {
        switch value {
        case .high: return .high
        case .medium: return .medium
        case .low: return .low
        }
    }

    private static func map(_ value: OfferRatingDTO) -> SafeOffer.RatingStatus {
        switch value {
        case .good: return .good
        case .fair: return .fair
        case .poor: return .poor
        }
    }

    private static func map(_ value: PenaltyBasisDTO) -> SafeOffer.PenaltyBasis {
        switch value {
        case .overdueInstalmentPerDay: return .overdueInstalmentPerDay
        case .overdueInstalmentPerMonth: return .overdueInstalmentPerMonth
        case .fixed: return .fixed
        }
    }

    private static func mapReason(_ value: OfferReasonCodeDTO) -> SafeOffer.Reason {
        let keys: (String, String)?
        switch value.code {
        case "OFFER_EXCEEDS_SAFE_INSTALMENT":
            keys = ("offers.reason.exceeds_safe_instalment", "offers.reason.exceeds_safe_instalment.detail")
        case "OFFER_EXCEEDS_SAFE_PRINCIPAL":
            keys = ("offers.reason.exceeds_safe_principal", "offers.reason.exceeds_safe_principal.detail")
        case "OFFER_HIGH_EFFECTIVE_COST":
            keys = ("offers.reason.high_effective_cost", "offers.reason.high_effective_cost.detail")
        case "OFFER_MISSING_FEE_DISCLOSURE":
            keys = ("offers.reason.missing_fee_disclosure", "offers.reason.missing_fee_disclosure.detail")
        case "REFINANCING_DEPENDENCY_RISK":
            keys = ("offers.reason.refinancing_dependency", "offers.reason.refinancing_dependency.detail")
        case "OFFER_ESSENTIAL_COVERAGE":
            keys = ("offers.reason.essential_coverage", "offers.reason.essential_coverage.detail")
        case "OFFER_SHOCK_SURVIVABILITY":
            keys = ("offers.reason.shock_survivability", "offers.reason.shock_survivability.detail")
        case "OFFER_SIMULATED_PROVIDER":
            keys = ("offers.reason.simulated_provider", "offers.reason.simulated_provider.detail")
        default: keys = nil
        }
        return .init(
            code: value.code,
            description: value.description,
            titleKey: keys?.0 ?? "offers.reason.unknown",
            detailKey: keys?.1,
            isKnown: keys != nil
        )
    }
}
