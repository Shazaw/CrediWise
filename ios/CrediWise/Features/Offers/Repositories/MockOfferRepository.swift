import Foundation

actor MockOfferRepository: OfferRepository {
    struct DetailRequest: Equatable, Sendable {
        let assessmentID: String
        let offerID: String
    }

    private let suppliedOffers: [SafeOffer]
    private let error: OfferRepositoryError?
    private var offerAssessmentIDs: [String] = []
    private var recordedDetailRequests: [DetailRequest] = []

    init(
        offers: [SafeOffer] = MockOfferRepository.makeOffers(),
        error: OfferRepositoryError? = nil
    ) {
        suppliedOffers = offers
        self.error = error
    }

    func offers(assessmentID: String) async throws -> [SafeOffer] {
        offerAssessmentIDs.append(assessmentID)
        if let error { throw error }
        return suppliedOffers.map { replacingAssessmentID($0, with: assessmentID) }
    }

    func offer(assessmentID: String, offerID: String) async throws -> SafeOffer {
        recordedDetailRequests.append(.init(assessmentID: assessmentID, offerID: offerID))
        if let error { throw error }
        guard let offer = suppliedOffers.first(where: { $0.offerID == offerID }) else {
            throw OfferRepositoryError.notFound
        }
        return replacingAssessmentID(offer, with: assessmentID)
    }

    func listRequests() -> [String] { offerAssessmentIDs }
    func detailRequests() -> [DetailRequest] { recordedDetailRequests }

    static func makeOffers() -> [SafeOffer] {
        [
            makeOffer(id: "offer-safe", rank: 1, score: 86, band: .safe, warning: nil),
            makeOffer(
                id: "offer-caution", rank: 2, score: 63, band: .caution,
                warning: "EXCEEDS_SAFE_PRINCIPAL"
            ),
            makeOffer(
                id: "offer-unsafe", rank: 3, score: 34, band: .unsafe,
                warning: "REFINANCING_DEPENDENCY_RISK"
            )
        ]
    }

    private static func makeOffer(
        id: String,
        rank: Int,
        score: Decimal,
        band: SafeOffer.SafetyBand,
        warning: String?
    ) -> SafeOffer {
        let instalment: Int64 = 290_000 + Int64((rank - 1) * 100_000)
        let schedule = makeSchedule(instalment: instalment)
        return SafeOffer(
            assessmentID: "synthetic-assessment-id", offerID: id, rank: rank,
            safeOfferScore: score, band: band,
            provider: .init(
                id: "simulated-provider-\(rank)",
                displayName: "Nusantara Modal Demo \(rank)",
                logoURL: nil,
                status: .simulatedRegulatedProvider
            ),
            offerSource: .simulated, principalAmount: 3_000_000,
            netDisbursedAmount: 2_925_000, instalmentAmount: instalment,
            tenorMonths: 12, paymentFrequency: .monthly,
            amortizationMethod: .fixedSchedule,
            nominalRate: .init(ratio: Decimal(string: "0.16") ?? 0, displayPercentage: 16),
            nominalRateBasis: .annualNominal, dueDayOfMonth: 22,
            paymentSchedule: schedule, costs: makeCosts(schedule: schedule),
            affordabilityStatus: rank == 3 ? .deficit : .survivable,
            shockResilienceStatus: rank == 1 ? .high : .medium,
            totalCostStatus: rank == 1 ? .good : .fair, timingStatus: .good,
            remainingEssentialExpenseCoverage: makeCoverage(rank: rank),
            refinancingDependency: rank == 3, warnings: makeWarnings(warning),
            reasons: makeReasons(),
            explanation: "The backend compared affordability, timing, cost, and shock evidence.",
            modelVersion: "safe-offer-v1", configHash: "synthetic-offer-config-v1",
            simulationNotice: OfferMapper.exactSimulationNotice
        )
    }

    private static func makeSchedule(instalment: Int64) -> [SafeOffer.ScheduledPayment] {
        (1...12).map { period in
            .init(
                period: period, paymentAmount: instalment,
                principalComponent: 250_000, interestComponent: instalment - 250_000,
                remainingBalance: Int64(12 - period) * 250_000
            )
        }
    }

    private static func makeCosts(
        schedule: [SafeOffer.ScheduledPayment]
    ) -> SafeOffer.CostBreakdown {
        .init(
            scheduledInterest: schedule.reduce(0) { $0 + $1.interestComponent },
            upfrontFee: 50_000, financedFee: 0, serviceFee: 15_000, adminFee: 10_000,
            effectiveAnnualRate: .init(
                ratio: Decimal(string: "0.3896") ?? 0, displayPercentage: 38.96
            ),
            totalScheduledRepayment: schedule.reduce(0) { $0 + $1.paymentAmount },
            latePenaltyTerms: .init(
                triggerDays: 3,
                rate: .init(ratio: Decimal(string: "0.05") ?? 0, displayPercentage: 5),
                amount: nil,
                basis: .overdueInstalmentPerDay
            )
        )
    }

    private static func makeCoverage(rank: Int) -> SafeOffer.EssentialExpenseCoverage {
        .init(
            amount: rank == 3 ? 250_000 : 1_400_000,
            ratio: rank == 3 ? Decimal(string: "0.12") ?? 0 : Decimal(string: "0.68") ?? 0,
            displayPercentage: rank == 3 ? 12 : 68
        )
    }

    private static func makeWarnings(_ code: String?) -> [SafeOffer.Warning] {
        guard let code else { return [] }
        let isRefinancing = code == "REFINANCING_DEPENDENCY_RISK"
        return [.init(
            code: code,
            titleKey: isRefinancing
                ? "offers.warning.refinancing_dependency.title"
                : "offers.warning.safe_principal.title",
            detailKey: isRefinancing
                ? "offers.warning.refinancing_dependency.detail"
                : "offers.warning.safe_principal.detail",
            usesGenericCopy: false
        )]
    }

    private static func makeReasons() -> [SafeOffer.Reason] {
        [
            .init(
                code: "OFFER_ESSENTIAL_COVERAGE", description: "Essential coverage is supplied.",
                titleKey: "offers.reason.essential_coverage",
                detailKey: "offers.reason.essential_coverage.detail", isKnown: true
            ),
            .init(
                code: "OFFER_SHOCK_SURVIVABILITY", description: "Shock status is supplied.",
                titleKey: "offers.reason.shock_survivability",
                detailKey: "offers.reason.shock_survivability.detail", isKnown: true
            ),
            .init(
                code: "OFFER_SIMULATED_PROVIDER", description: "This is a simulated offer.",
                titleKey: "offers.reason.simulated_provider",
                detailKey: "offers.reason.simulated_provider.detail", isKnown: true
            )
        ]
    }

    private func replacingAssessmentID(_ source: SafeOffer, with assessmentID: String) -> SafeOffer {
        .init(
            assessmentID: assessmentID, offerID: source.offerID, rank: source.rank,
            safeOfferScore: source.safeOfferScore, band: source.band, provider: source.provider,
            offerSource: source.offerSource, principalAmount: source.principalAmount,
            netDisbursedAmount: source.netDisbursedAmount, instalmentAmount: source.instalmentAmount,
            tenorMonths: source.tenorMonths, paymentFrequency: source.paymentFrequency,
            amortizationMethod: source.amortizationMethod, nominalRate: source.nominalRate,
            nominalRateBasis: source.nominalRateBasis, dueDayOfMonth: source.dueDayOfMonth,
            paymentSchedule: source.paymentSchedule, costs: source.costs,
            affordabilityStatus: source.affordabilityStatus,
            shockResilienceStatus: source.shockResilienceStatus,
            totalCostStatus: source.totalCostStatus, timingStatus: source.timingStatus,
            remainingEssentialExpenseCoverage: source.remainingEssentialExpenseCoverage,
            refinancingDependency: source.refinancingDependency, warnings: source.warnings,
            reasons: source.reasons, explanation: source.explanation,
            modelVersion: source.modelVersion, configHash: source.configHash,
            simulationNotice: source.simulationNotice
        )
    }
}
