import Foundation
import XCTest
@testable import CrediWise

final class APIOfferRepositoryTests: XCTestCase {
    private let assessmentID = UUID(uuidString: "EAD33DE7-4220-4E50-93D4-84100253A714")!

    func testNonEmptyGetPreservesOrderAndDoesNotPost() async throws {
        let body = listBody(offers: [
            offerBody(rank: 2, source: "LENDER_API", providerStatus: "REGULATED"),
            offerBody(rank: 1, source: "SIMULATED", providerStatus: "SIMULATED_REGULATED_PROVIDER")
        ])
        let session = OfferStubSession(responses: [.init(statusCode: 200, body: body)])
        let repository = try await makeRepository(session: session)

        let offers = try await repository.offers(assessmentID: assessmentID.uuidString)

        XCTAssertEqual(offers.map(\.rank), [2, 1])
        XCTAssertEqual(offers.map(\.offerSource), [.lenderAPI, .simulated])
        XCTAssertEqual(offers.map(\.provider.status), [.regulated, .simulatedRegulatedProvider])
        XCTAssertNil(offers[0].simulationNotice)
        XCTAssertEqual(offers[1].simulationNotice, OfferMapper.exactSimulationNotice)
        let requests = await session.requests()
        XCTAssertEqual(requests.map(\.httpMethod), ["GET"])
    }

    func testEmptyGetSeedsWithPost201AndMapsFullContract() async throws {
        let session = OfferStubSession(responses: [
            .init(statusCode: 200, body: listBody(offers: [])),
            .init(
                statusCode: 201,
                body: listBody(offers: [
                    offerBody(
                        rank: 1,
                        source: "MANUAL_LENDER_ENTRY",
                        providerStatus: "UNLISTED",
                        warning: "FUTURE_WARNING"
                    )
                ])
            )
        ])
        let repository = try await makeRepository(session: session)

        let offers = try await repository.offers(assessmentID: assessmentID.uuidString)
        let offer = try XCTUnwrap(offers.first)

        let requests = await session.requests()
        XCTAssertEqual(requests.map(\.httpMethod), ["GET", "POST"])
        XCTAssertEqual(offer.offerSource, .manualLenderEntry)
        XCTAssertEqual(offer.provider.status, .unlisted)
        XCTAssertEqual(offer.provider.displayName, "Backend Display Lender")
        XCTAssertEqual(offer.nominalRate?.ratio, Decimal(string: "0.16"))
        XCTAssertEqual(offer.nominalRate?.displayPercentage, 16)
        XCTAssertEqual(offer.costs.effectiveAnnualRate?.displayPercentage, 38.96)
        XCTAssertEqual(offer.costs.upfrontFee, 50_000)
        XCTAssertEqual(offer.costs.financedFee, 20_000)
        XCTAssertEqual(offer.costs.serviceFee, 15_000)
        XCTAssertEqual(offer.costs.adminFee, 10_000)
        XCTAssertEqual(offer.costs.latePenaltyTerms?.basis, .overdueInstalmentPerDay)
        XCTAssertEqual(offer.paymentSchedule.first?.principalComponent, 250_000)
        XCTAssertEqual(offer.paymentSchedule.first?.interestComponent, 40_000)
        XCTAssertEqual(offer.remainingEssentialExpenseCoverage.ratio, Decimal(string: "0.68"))
        XCTAssertEqual(offer.remainingEssentialExpenseCoverage.displayPercentage, 68)
        XCTAssertEqual(offer.affordabilityStatus, .survivable)
        XCTAssertEqual(offer.shockResilienceStatus, .high)
        XCTAssertEqual(offer.totalCostStatus, .good)
        XCTAssertEqual(offer.timingStatus, .fair)
        XCTAssertTrue(offer.warnings[0].usesGenericCopy)
        XCTAssertEqual(offer.warnings[0].code, "FUTURE_WARNING")
        XCTAssertTrue(offer.reasons[0].isKnown)
        XCTAssertEqual(offer.reasons[0].titleKey, "offers.reason.essential_coverage")
        XCTAssertTrue(offer.reasons.dropLast().allSatisfy(\.isKnown))
        XCTAssertFalse(offer.reasons.last?.isKnown == true)
        XCTAssertNil(offer.simulationNotice)
    }

    func testTopLevelSafetyUsesDetailShapeAndAuth() async throws {
        let session = OfferStubSession(responses: [
            .init(statusCode: 200, body: offerBody(rank: 1))
        ])
        let repository = try await makeRepository(session: session)

        let offer = try await repository.offer(
            assessmentID: assessmentID.uuidString,
            offerID: offerContractFixtureID.uuidString
        )

        XCTAssertEqual(offer.assessmentID, assessmentID.uuidString)
        let requests = await session.requests()
        let request = try XCTUnwrap(requests.first)
        XCTAssertEqual(request.httpMethod, "GET")
        XCTAssertEqual(request.url?.path, "/api/v1/offers/\(offerContractFixtureID.uuidString)/safety")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-value")
    }

    func testRefreshRetryAndStatusMapping() async throws {
        let session = OfferStubSession(responses: [
            .init(statusCode: 401, body: errorBody(code: "UNAUTHORIZED")),
            .init(statusCode: 200, body: listBody(offers: [offerBody(rank: 1)]))
        ])
        let repository = try await makeRepository(session: session)
        _ = try await repository.offers(assessmentID: assessmentID.uuidString)
        let requests = await session.requests()
        XCTAssertEqual(
            requests.map { $0.value(forHTTPHeaderField: "Authorization") },
            ["Bearer access-value", "Bearer refreshed"]
        )

        for (status, code, expected) in [
            (404, "NOT_FOUND", OfferRepositoryError.notFound),
            (404, "ASSESSMENT_NOT_READY", .notReady),
            (409, "REASSESSMENT_REQUIRED", .reassessmentRequired),
            (422, "VALIDATION_ERROR", .invalidParameters),
            (429, "RATE_LIMITED", .rateLimited),
            (503, "UNAVAILABLE", .unavailable)
        ] {
            let failure = OfferStubSession(responses: [
                .init(statusCode: status, body: errorBody(code: code))
            ])
            let failingRepository = try await makeRepository(session: failure)
            await assertThrows(expected) {
                _ = try await failingRepository.offers(assessmentID: assessmentID.uuidString)
            }
        }
    }

    func testMalformedEnumDecimalNoticeAndCancellationFailSafely() async throws {
        for replacement in [
            ("SIMULATED_REGULATED_PROVIDER", "UNKNOWN_PROVIDER"),
            ("\"safe_offer_score\":\"86.25\"", "\"safe_offer_score\":\"bad\""),
            (OfferMapper.exactSimulationNotice, "Wrong notice"),
            (
                "\"simulation_notice\":\"\(OfferMapper.exactSimulationNotice)\"",
                "\"simulation_notice\":null"
            ),
            ("\"simulation_notice\":", "\"missing_simulation_notice\":"),
            ("\"rate\":\"0.05\"", "\"missing_rate\":\"0.05\""),
            ("\"amount\":null", "\"missing_amount\":null")
        ] {
            let body = listBody(offers: [offerBody(rank: 1)])
                .replacingOccurrences(of: replacement.0, with: replacement.1)
            let session = OfferStubSession(responses: [.init(statusCode: 200, body: body)])
            let repository = try await makeRepository(session: session)
            await assertThrows(.unavailable) {
                _ = try await repository.offers(assessmentID: assessmentID.uuidString)
            }
        }

        let invalidCombination = listBody(offers: [
            offerBody(rank: 1).replacingOccurrences(
                of: "SIMULATED_REGULATED_PROVIDER",
                with: "REGULATED"
            )
        ])
        let invalidSession = OfferStubSession(responses: [
            .init(statusCode: 200, body: invalidCombination)
        ])
        let invalidRepository = try await makeRepository(session: invalidSession)
        await assertThrows(.unavailable) {
            _ = try await invalidRepository.offers(assessmentID: assessmentID.uuidString)
        }

        let repository = try await makeRepository(session: OfferCancellationSession())
        do {
            _ = try await repository.offers(assessmentID: assessmentID.uuidString)
            XCTFail("Expected cancellation")
        } catch is CancellationError {
        } catch {
            XCTFail("Expected CancellationError, got \(error)")
        }
    }

    func testAllStatusValuesMapExactly() async throws {
        let variants = [
            OfferStatusVariant(
                affordability: "SURVIVABLE", shock: "HIGH", cost: "GOOD", timing: "FAIR",
                amortization: "FIXED_SCHEDULE", frequency: "MONTHLY",
                penalty: "OVERDUE_INSTALMENT_PER_DAY", expectedAffordability: .survivable,
                expectedShock: .high, expectedCost: .good, expectedTiming: .fair,
                expectedAmortization: .fixedSchedule, expectedFrequency: .monthly,
                expectedPenalty: .overdueInstalmentPerDay
            ),
            OfferStatusVariant(
                affordability: "STRAINED", shock: "MEDIUM", cost: "FAIR", timing: "POOR",
                amortization: "FLAT", frequency: "BIWEEKLY",
                penalty: "OVERDUE_INSTALMENT_PER_MONTH", expectedAffordability: .strained,
                expectedShock: .medium, expectedCost: .fair, expectedTiming: .poor,
                expectedAmortization: .flat, expectedFrequency: .biweekly,
                expectedPenalty: .overdueInstalmentPerMonth
            ),
            OfferStatusVariant(
                affordability: "DEFICIT", shock: "LOW", cost: "POOR", timing: "GOOD",
                amortization: "REDUCING_BALANCE", frequency: "WEEKLY", penalty: "FIXED",
                expectedAffordability: .deficit, expectedShock: .low, expectedCost: .poor,
                expectedTiming: .good, expectedAmortization: .reducingBalance,
                expectedFrequency: .weekly, expectedPenalty: .fixed
            )
        ]
        for variant in variants {
            try await assertMapping(variant)
        }
    }

    func testNullableRatesAndPenaltyMapExactly() async throws {
        let nullableBody = listBody(offers: [offerBody(rank: 1)])
            .replacingOccurrences(of: "\"nominal_rate\":\"0.16\"", with: "\"nominal_rate\":null")
            .replacingOccurrences(of: "\"effective_annual_rate\":\"0.3896\"", with: "\"effective_annual_rate\":null")
            .replacingOccurrences(
                of: "\"late_penalty_terms\":",
                with: "\"ignored_late_penalty_terms\":"
            )
            .replacingOccurrences(
                of: "\"payment_schedule\":",
                with: "\"late_penalty_terms\":null,\"payment_schedule\":"
            )
        let session = OfferStubSession(responses: [.init(statusCode: 200, body: nullableBody)])
        let repository = try await makeRepository(session: session)
        let offers = try await repository.offers(assessmentID: assessmentID.uuidString)
        let offer = try XCTUnwrap(offers.first)
        XCTAssertNil(offer.nominalRate)
        XCTAssertNil(offer.costs.effectiveAnnualRate)
        XCTAssertNil(offer.costs.latePenaltyTerms)
    }

    private func assertMapping(_ variant: OfferStatusVariant) async throws {
        let body = listBody(offers: [offerBody(rank: 1)])
            .replacingOccurrences(
                of: "\"affordability_status\":\"SURVIVABLE\"",
                with: "\"affordability_status\":\"\(variant.affordability)\""
            )
            .replacingOccurrences(
                of: "\"shock_resilience_status\":\"HIGH\"",
                with: "\"shock_resilience_status\":\"\(variant.shock)\""
            )
            .replacingOccurrences(
                of: "\"total_cost_status\":\"GOOD\"",
                with: "\"total_cost_status\":\"\(variant.cost)\""
            )
            .replacingOccurrences(
                of: "\"timing_status\":\"FAIR\"",
                with: "\"timing_status\":\"\(variant.timing)\""
            )
            .replacingOccurrences(
                of: "\"amortization_method\":\"FIXED_SCHEDULE\"",
                with: "\"amortization_method\":\"\(variant.amortization)\""
            )
            .replacingOccurrences(
                of: "\"frequency\":\"MONTHLY\"",
                with: "\"frequency\":\"\(variant.frequency)\""
            )
            .replacingOccurrences(
                of: "\"basis\":\"OVERDUE_INSTALMENT_PER_DAY\"",
                with: "\"basis\":\"\(variant.penalty)\""
            )
        let session = OfferStubSession(responses: [.init(statusCode: 200, body: body)])
        let repository = try await makeRepository(session: session)
        let offer = try XCTUnwrap(
            try await repository.offers(assessmentID: assessmentID.uuidString).first
        )
        XCTAssertEqual(offer.affordabilityStatus, variant.expectedAffordability)
        XCTAssertEqual(offer.shockResilienceStatus, variant.expectedShock)
        XCTAssertEqual(offer.totalCostStatus, variant.expectedCost)
        XCTAssertEqual(offer.timingStatus, variant.expectedTiming)
        XCTAssertEqual(offer.amortizationMethod, variant.expectedAmortization)
        XCTAssertEqual(offer.paymentFrequency, variant.expectedFrequency)
        XCTAssertEqual(offer.costs.latePenaltyTerms?.basis, variant.expectedPenalty)
    }

    func testNotCompleteValidationEnvelopeMapsNotReady() async throws {
        let session = OfferStubSession(responses: [
            .init(
                statusCode: 422,
                body: errorBody(
                    code: "VALIDATION_ERROR",
                    message: "Assessment must be COMPLETE before offers can be seeded",
                    status: "ANALYZING"
                )
            )
        ])
        let repository = try await makeRepository(session: session)
        await assertThrows(.notReady) {
            _ = try await repository.offers(assessmentID: assessmentID.uuidString)
        }
    }

    func testInvalidLogoURLsAreOmittedWithoutDiscardingOffer() async throws {
        for invalidURL in ["http://insecure.test/logo.png", "relative/logo.png"] {
            let body = listBody(offers: [offerBody(rank: 1)])
                .replacingOccurrences(
                    of: "https://cdn.example.test/logo.png",
                    with: invalidURL
                )
            let session = OfferStubSession(responses: [.init(statusCode: 200, body: body)])
            let repository = try await makeRepository(session: session)
            let offers = try await repository.offers(assessmentID: assessmentID.uuidString)
            XCTAssertNil(offers.first?.provider.logoURL)
        }
    }

    private func makeRepository(session: any HTTPDataSession) async throws -> APIOfferRepository {
        let tokenStore = VolatileTokenStore()
        try await tokenStore.save(.init(accessToken: "access-value", refreshToken: "refresh-value"))
        return APIOfferRepository(
            baseURL: URL(string: "https://api.crediwise.test")!,
            session: session,
            authInterceptor: AuthInterceptor(
                tokenStore: tokenStore,
                refreshHandler: { _ in .init(accessToken: "refreshed", refreshToken: "refresh-value") },
                unauthorizedHandler: {}
            )
        )
    }

    private func assertThrows(
        _ expected: OfferRepositoryError,
        operation: () async throws -> Void
    ) async {
        do {
            try await operation()
            XCTFail("Expected \(expected)")
        } catch let error as OfferRepositoryError {
            XCTAssertEqual(error, expected)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
    }

}
