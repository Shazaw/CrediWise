actor MockOfferRepository: OfferRepository {
    struct DetailRequest: Equatable, Sendable {
        let assessmentID: String
        let offerID: String
    }

    private struct Fixture {
        let offerID: String
        let rank: Int
        let isSafest: Bool
        let score: Int
        let band: SafeOffer.SafetyBand
        let principal: Int64
        let netAmountReceived: Int64
        let upfrontFees: Int64
        let instalment: Int64
        let scheduledInterest: Int64
        let totalScheduledRepayment: Int64
        let nominalAnnualRatePercentage: Double
        let effectiveAnnualCostPercentage: Double
        let remainingEssentialCoverage: Int64
        let refinancingDependency: Bool
        let warnings: [SafeOffer.Warning]
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
        if let error {
            throw error
        }
        return suppliedOffers.map { offer($0, assessmentID: assessmentID) }
    }

    func offer(assessmentID: String, offerID: String) async throws -> SafeOffer {
        recordedDetailRequests.append(
            DetailRequest(assessmentID: assessmentID, offerID: offerID)
        )
        if let error {
            throw error
        }
        guard let offer = suppliedOffers.first(where: { $0.offerID == offerID }) else {
            throw OfferRepositoryError.unavailable
        }
        return self.offer(offer, assessmentID: assessmentID)
    }

    func listRequests() -> [String] {
        offerAssessmentIDs
    }

    func detailRequests() -> [DetailRequest] {
        recordedDetailRequests
    }

    static func makeOffers() -> [SafeOffer] {
        [makeSafeOffer(), makeCautionOffer(), makeUnsafeOffer()]
    }

    private static func makeSafeOffer() -> SafeOffer {
        makeOffer(
            Fixture(
                offerID: "offer-safe",
                rank: 1,
                isSafest: true,
                score: 86,
                band: .safe,
                principal: 3_000_000,
                netAmountReceived: 2_925_000,
                upfrontFees: 75_000,
                instalment: 290_000,
                scheduledInterest: 480_000,
                totalScheduledRepayment: 3_480_000,
                nominalAnnualRatePercentage: 16,
                effectiveAnnualCostPercentage: 38.96,
                remainingEssentialCoverage: 1_400_000,
                refinancingDependency: false,
                warnings: []
            )
        )
    }

    private static func makeCautionOffer() -> SafeOffer {
        makeOffer(
            Fixture(
                offerID: "offer-caution",
                rank: 2,
                isSafest: false,
                score: 63,
                band: .caution,
                principal: 3_500_000,
                netAmountReceived: 3_350_000,
                upfrontFees: 150_000,
                instalment: 375_000,
                scheduledInterest: 1_000_000,
                totalScheduledRepayment: 4_500_000,
                nominalAnnualRatePercentage: 28.57,
                effectiveAnnualCostPercentage: 76.75,
                remainingEssentialCoverage: 900_000,
                refinancingDependency: false,
                warnings: [
                    .init(
                        id: "buffer-pressure",
                        code: "BUFFER_PRESSURE",
                        titleKey: "offers.warning.buffer_pressure.title",
                        detailKey: "offers.warning.buffer_pressure.detail"
                    )
                ]
            )
        )
    }

    private static func makeUnsafeOffer() -> SafeOffer {
        makeOffer(
            Fixture(
                offerID: "offer-unsafe",
                rank: 3,
                isSafest: false,
                score: 34,
                band: .unsafe,
                principal: 5_000_000,
                netAmountReceived: 4_700_000,
                upfrontFees: 300_000,
                instalment: 620_000,
                scheduledInterest: 2_440_000,
                totalScheduledRepayment: 7_440_000,
                nominalAnnualRatePercentage: 48.8,
                effectiveAnnualCostPercentage: 148.66,
                remainingEssentialCoverage: -250_000,
                refinancingDependency: true,
                warnings: [
                    .init(
                        id: "refinancing-dependency",
                        code: "REFINANCING_DEPENDENCY_RISK",
                        titleKey: "offers.warning.refinancing_dependency.title",
                        detailKey: "offers.warning.refinancing_dependency.detail"
                    ),
                    .init(
                        id: "essential-coverage",
                        code: "INSUFFICIENT_ESSENTIAL_COVERAGE",
                        titleKey: "offers.warning.essential_coverage.title",
                        detailKey: "offers.warning.essential_coverage.detail"
                    )
                ]
            )
        )
    }

    private static func makeOffer(_ fixture: Fixture) -> SafeOffer {
        SafeOffer(
            assessmentID: "synthetic-assessment-id",
            offerID: fixture.offerID,
            suppliedRank: fixture.rank,
            isSafest: fixture.isSafest,
            score: fixture.score,
            band: fixture.band,
            provider: provider(rank: fixture.rank),
            principal: fixture.principal,
            netAmountReceived: fixture.netAmountReceived,
            instalment: fixture.instalment,
            tenorMonths: 12,
            paymentFrequency: .monthly,
            amortizationMethod: .fixedSchedule,
            nominalAnnualRatePercentage: fixture.nominalAnnualRatePercentage,
            rateBasis: .annualFlat,
            dueDayOfMonth: 22,
            scheduledPayments: payments(instalment: fixture.instalment),
            costs: costs(fixture: fixture),
            remainingEssentialCoverage: fixture.remainingEssentialCoverage,
            refinancingDependency: fixture.refinancingDependency,
            warnings: fixture.warnings,
            reasons: reasons(rank: fixture.rank),
            modelVersion: "safe-offer-v1"
        )
    }

    private static func provider(rank: Int) -> SafeOffer.Provider {
        .init(
            id: "simulated-provider-\(rank)",
            nameKey: "offers.provider.simulated_\(rank)",
            status: .simulatedRegulatedProvider
        )
    }

    private static func payments(instalment: Int64) -> [SafeOffer.ScheduledPayment] {
        (1...12).map { .init(id: $0, amount: instalment) }
    }

    private static func costs(fixture: Fixture) -> SafeOffer.CostBreakdown {
        .init(
            scheduledInterest: fixture.scheduledInterest,
            upfrontFees: fixture.upfrontFees,
            financedFees: 0,
            effectiveAnnualCostPercentage: fixture.effectiveAnnualCostPercentage,
            totalScheduledRepayment: fixture.totalScheduledRepayment,
            penaltyTermsKey: "offers.penalty.simulated_standard"
        )
    }

    private static func reasons(rank: Int) -> [SafeOffer.Reason] {
        [
            .init(
                id: "supplied-safety-result-\(rank)",
                titleKey: "offers.reason.safety_result.title",
                detailKey: "offers.reason.safety_result.detail"
            ),
            .init(
                id: "cost-transparency-\(rank)",
                titleKey: "offers.reason.cost_transparency.title",
                detailKey: "offers.reason.cost_transparency.detail"
            ),
            .init(
                id: "essential-coverage-\(rank)",
                titleKey: "offers.reason.essential_coverage.title",
                detailKey: "offers.reason.essential_coverage.detail"
            )
        ]
    }

    private func offer(_ source: SafeOffer, assessmentID: String) -> SafeOffer {
        SafeOffer(
            assessmentID: assessmentID,
            offerID: source.offerID,
            suppliedRank: source.suppliedRank,
            isSafest: source.isSafest,
            score: source.score,
            band: source.band,
            provider: source.provider,
            principal: source.principal,
            netAmountReceived: source.netAmountReceived,
            instalment: source.instalment,
            tenorMonths: source.tenorMonths,
            paymentFrequency: source.paymentFrequency,
            amortizationMethod: source.amortizationMethod,
            nominalAnnualRatePercentage: source.nominalAnnualRatePercentage,
            rateBasis: source.rateBasis,
            dueDayOfMonth: source.dueDayOfMonth,
            scheduledPayments: source.scheduledPayments,
            costs: source.costs,
            remainingEssentialCoverage: source.remainingEssentialCoverage,
            refinancingDependency: source.refinancingDependency,
            warnings: source.warnings,
            reasons: source.reasons,
            modelVersion: source.modelVersion
        )
    }
}
