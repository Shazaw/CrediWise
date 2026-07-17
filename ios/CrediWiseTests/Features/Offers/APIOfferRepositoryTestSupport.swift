import Foundation
@testable import CrediWise

let offerContractFixtureID = UUID(uuidString: "BFA50DD7-F269-4013-BABF-11FD3EF142FE")!

struct OfferStatusVariant {
    let affordability: String
    let shock: String
    let cost: String
    let timing: String
    let amortization: String
    let frequency: String
    let penalty: String
    let expectedAffordability: SafeOffer.AffordabilityStatus
    let expectedShock: SafeOffer.ConfidenceStatus
    let expectedCost: SafeOffer.RatingStatus
    let expectedTiming: SafeOffer.RatingStatus
    let expectedAmortization: SafeOffer.AmortizationMethod
    let expectedFrequency: SafeOffer.PaymentFrequency
    let expectedPenalty: SafeOffer.PenaltyBasis
}

extension APIOfferRepositoryTests {
    func listBody(offers: [String]) -> String {
        """
        {"assessment_id":"EAD33DE7-4220-4E50-93D4-84100253A714",\
        "offers":[\(offers.joined(separator: ","))]}
        """
    }

    func offerBody(
        rank: Int,
        source: String = "SIMULATED",
        providerStatus: String = "SIMULATED_REGULATED_PROVIDER",
        warning: String = "EXCEEDS_SAFE_INSTALMENT"
    ) -> String {
        let notice = source == "SIMULATED"
            ? "\"\(OfferMapper.exactSimulationNotice)\""
            : "null"
        let simulatedReason = source == "SIMULATED"
            ? "{\"code\":\"OFFER_SIMULATED_PROVIDER\",\"description\":\"Simulation\"},"
            : ""
        return """
        {
          "offer_id":"BFA50DD7-F269-4013-BABF-11FD3EF142FE",
          "lender":{"lender_id":"A2F08E53-C537-4935-93EF-6411361959B6",
          "name":"Backend Display Lender","regulatory_status":"\(providerStatus)",
          "logo_url":"https://cdn.example.test/logo.png"},
          "offer_source":"\(source)",
          "principal_amount":3000000,"net_disbursed_amount":2925000,
          "instalment_amount":290000,"tenor_months":12,"amortization_method":"FIXED_SCHEDULE",
          "nominal_rate":"0.16","nominal_rate_basis":"ANNUAL_NOMINAL",
          "effective_annual_rate":"0.3896","interest_amount":480000,
          "upfront_fee":50000,"financed_fee":20000,"service_fee":15000,
          "admin_fee":10000,"total_repayment":3480000,
          "late_penalty_terms":{"trigger_days":3,"rate":"0.05","amount":null,
          "basis":"OVERDUE_INSTALMENT_PER_DAY"},
          "payment_schedule":[{"period":1,"payment_amount":290000,
          "principal_component":250000,"interest_component":40000,
          "remaining_balance":2750000}],
          "due_date":22,"frequency":"MONTHLY","safe_offer_score":"86.25",
          "safety_band":"SAFE","rank":\(rank),"affordability_status":"SURVIVABLE",
          "shock_resilience_status":"HIGH","total_cost_status":"GOOD","timing_status":"FAIR",
          "warning_flags":["\(warning)"],"refinancing_dependency":false,
          "remaining_essential_expense_coverage":{"amount":1400000,"ratio":"0.68"},
          "reason_codes":[
          {"code":"OFFER_ESSENTIAL_COVERAGE","description":"Coverage"},
          {"code":"OFFER_EXCEEDS_SAFE_INSTALMENT","description":"Instalment"},
          {"code":"OFFER_EXCEEDS_SAFE_PRINCIPAL","description":"Principal"},
          {"code":"OFFER_HIGH_EFFECTIVE_COST","description":"Cost"},
          {"code":"OFFER_MISSING_FEE_DISCLOSURE","description":"Disclosure"},
          {"code":"REFINANCING_DEPENDENCY_RISK","description":"Refinancing"},
          {"code":"OFFER_SHOCK_SURVIVABILITY","description":"Shock"},
          \(simulatedReason)
          {"code":"FUTURE_OFFER_REASON","description":"Future"}],
          "explanation":"Backend explanation","model_version":"offer-v1",
          "config_hash":"config-def","simulation_notice":\(notice)
        }
        """
    }

    func errorBody(
        code: String,
        message: String = "error",
        status: String? = nil
    ) -> String {
        let details = status.map { "{\"status\":\"\($0)\"}" } ?? "{}"
        return """
        {"error":{"code":"\(code)","message":"\(message)",
        "details":\(details),"correlation_id":"test"}}
        """
    }
}

struct OfferStubResponse: Sendable {
    let statusCode: Int
    let body: String
}

actor OfferStubSession: HTTPDataSession {
    private var responses: [OfferStubResponse]
    private var capturedRequests: [URLRequest] = []

    init(responses: [OfferStubResponse]) { self.responses = responses }

    func response(for request: URLRequest) async throws -> (Data, URLResponse) {
        capturedRequests.append(request)
        guard !responses.isEmpty else { throw OfferRepositoryError.unavailable }
        let value = responses.removeFirst()
        return (
            Data(value.body.utf8),
            HTTPURLResponse(
                url: request.url!, statusCode: value.statusCode,
                httpVersion: nil, headerFields: nil
            )!
        )
    }

    func requests() -> [URLRequest] { capturedRequests }
}

struct OfferCancellationSession: HTTPDataSession {
    func response(for request: URLRequest) async throws -> (Data, URLResponse) {
        throw CancellationError()
    }
}
