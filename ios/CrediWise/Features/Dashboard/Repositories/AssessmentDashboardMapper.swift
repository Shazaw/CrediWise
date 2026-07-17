enum AssessmentDashboardMapper {
    static func map(
        summary: AssessmentDashboardResponse,
        twin: AssessmentTwinResponse,
        confidence: DataConfidenceReport
    ) throws -> AssessmentDashboard {
        let codes = allCodes(summary)
        return AssessmentDashboard(
            assessmentID: summary.assessmentID.uuidString,
            dataConfidence: try mappedConfidence(summary.dataConfidence, evidence: confidence),
            risk: try mappedRisk(summary, codes: codes),
            safeBorrowing: try mappedSafeBorrowing(summary.safeBorrowing, codes: codes),
            twin: mappedTwin(twin),
            recommendations: recommendations(codes),
            modelVersion: summary.modelVersionID.uuidString,
            repaymentModel: try mappedRepaymentModel(summary.repaymentModel)
        )
    }

    private static func mappedConfidence(
        _ response: AssessmentDataConfidenceResponse,
        evidence: DataConfidenceReport
    ) throws -> DataConfidenceReport {
        guard let score = score(response.score),
              let band = confidenceBand(response.band) else {
            throw AssessmentDashboardRepositoryError.unavailable
        }
        return DataConfidenceReport(
            score: score,
            band: band,
            dimensions: evidence.dimensions,
            reasons: evidence.reasons,
            recommendationKey: evidence.recommendationKey,
            assistanceStatus: evidence.assistanceStatus,
            modelVersion: evidence.modelVersion
        )
    }

    private static func mappedRisk(
        _ response: AssessmentDashboardResponse,
        codes: [AssessmentReasonResponse]
    ) throws -> AssessmentDashboard.Risk {
        guard let band = riskBand(response.riskBand.band),
              let confidence = modelConfidence(response.riskBand.modelConfidence) else {
            throw AssessmentDashboardRepositoryError.unavailable
        }
        let positive = response.riskBand.positiveReasonCodes.filter { $0.code.hasPrefix("RISK_") }
        let warnings = codes.filter { candidate in
            candidate.code.hasPrefix("RISK_")
                && !positive.contains(where: { $0.code == candidate.code })
        }
        return .init(
            band: band,
            modelConfidence: confidence,
            positiveFactors: positive.map(reason),
            riskFactors: warnings.map(reason)
        )
    }

    private static func mappedSafeBorrowing(
        _ response: AssessmentSafeBorrowingResponse,
        codes: [AssessmentReasonResponse]
    ) throws -> AssessmentDashboard.SafeBorrowing {
        guard let amount = response.amount,
              let maxInstalment = response.maxInstalment,
              let requiredLiquidityBuffer = response.requiredLiquidityBuffer,
              let tenor = response.tenorMonths,
              let window = response.dueDateWindow,
              window.count == 2,
              let frequency = frequency(response.frequency) else {
            throw AssessmentDashboardRepositoryError.unavailable
        }
        return .init(
            illustrativeAmount: amount,
            maximumSafeInstalment: maxInstalment,
            recommendedTenorMonths: tenor,
            dueDateStart: window[0],
            dueDateEnd: window[1],
            frequency: frequency,
            requiredLiquidityBuffer: requiredLiquidityBuffer,
            reasons: codes.filter { $0.code.hasPrefix("SAFE_BORROWING_") }.map(reason)
        )
    }

    private static func mappedTwin(_ response: AssessmentTwinResponse) -> AssessmentDashboard.Twin {
        .init(
            medianIncome: response.medianIncome,
            essentialExpenses: response.essentialExpenses,
            discretionaryExpenses: response.discretionaryExpenses,
            existingDebt: response.existingDebt,
            averageFreeCashFlow: response.averageFreeCashFlow,
            weakestMonthCashFlow: response.weakestMonthCashFlow,
            personalIncome: income(response.incomeSources, business: false),
            businessIncome: income(response.incomeSources, business: true),
            coverage: response.coverageFlag == "SUFFICIENT" ? .sufficient : .low
        )
    }

    private static func allCodes(
        _ response: AssessmentDashboardResponse
    ) -> [AssessmentReasonResponse] {
        response.dataConfidence.reasonCodes
            + response.riskBand.positiveReasonCodes
            + response.riskBand.riskReasonCodes
    }

    private static func reason(_ response: AssessmentReasonResponse) -> AssessmentDashboard.Reason {
        let keys: (String, String)
        switch response.code {
        case "RISK_CASH_FLOW_STRONG", "RISK_CASH_FLOW_OK":
            keys = (
                "dashboard.reason.income_consistency.title",
                "dashboard.reason.income_consistency.detail"
            )
        case "RISK_DSTI_EXCELLENT", "RISK_DSTI_GOOD":
            keys = ("dashboard.reason.low_debt.title", "dashboard.reason.low_debt.detail")
        case "RISK_DSTI_CAUTION", "RISK_DSTI_HIGH":
            keys = ("dashboard.reason.debt_watch.title", "dashboard.reason.debt_watch.detail")
        case "RISK_INCOME_VOLATILITY":
            keys = (
                "dashboard.reason.income_variation.title",
                "dashboard.reason.income_variation.detail"
            )
        case "RISK_INCOME_CONCENTRATION":
            keys = (
                "dashboard.reason.income_concentration.title",
                "dashboard.reason.income_concentration.detail"
            )
        case "RISK_CASH_FLOW_WEAK":
            keys = ("dashboard.reason.cash_flow_weak.title", "dashboard.reason.cash_flow_weak.detail")
        case "RISK_DISCRETIONARY_SPENDING":
            keys = (
                "dashboard.reason.discretionary.title",
                "dashboard.reason.discretionary.detail"
            )
        case "RISK_INSUFFICIENT_DATA", "RISK_BEHAVIOUR_NO_INCOME_DATA":
            keys = (
                "dashboard.reason.insufficient_data.title",
                "dashboard.reason.insufficient_data.detail"
            )
        case let code where code.hasPrefix("SAFE_BORROWING_"):
            keys = ("dashboard.reason.safe_limit.title", "dashboard.reason.safe_limit.detail")
        default:
            keys = ("dashboard.reason.server.title", response.description)
        }
        return .init(id: response.code, titleKey: keys.0, detailKey: keys.1)
    }

    private static func recommendations(
        _ codes: [AssessmentReasonResponse]
    ) -> [AssessmentDashboard.Recommendation] {
        var values: [AssessmentDashboard.Recommendation] = []
        if codes.contains(where: { $0.code == "SAFE_BORROWING_ZERO_CAPACITY" }) {
            values.append(
                recommendation(
                    id: "zero-capacity",
                    prefix: "dashboard.plan.zero_capacity"
                )
            )
        } else if codes.contains(where: { $0.code.hasPrefix("SAFE_BORROWING_LIMITED_BY_") }) {
            values.append(recommendation(id: "protect-buffer", prefix: "dashboard.plan.protect_buffer"))
        }
        if codes.contains(where: { $0.code == "RISK_INCOME_CONCENTRATION" }) {
            values.append(recommendation(id: "stabilize-income", prefix: "dashboard.plan.stabilize_income"))
        }
        return values
    }

    private static func mappedRepaymentModel(
        _ response: AssessmentRepaymentModelResponse?
    ) throws -> AssessmentDashboard.RepaymentModel? {
        guard let response else { return nil }
        guard response.mode == "SHADOW_RESEARCH",
              let status = AssessmentDashboard.RepaymentModelStatus(
                  rawValue: response.status.lowercased()
              ) else {
            throw AssessmentDashboardRepositoryError.unavailable
        }
        let probability = response.estimatedAdverseOutcomeProbability.flatMap { Double($0) }
        let confidence = response.modelConfidence.flatMap(modelConfidence)
        if status == .complete && (probability == nil || confidence == nil) {
            throw AssessmentDashboardRepositoryError.unavailable
        }
        return .init(
            status: status,
            adverseOutcomeProbability: probability,
            confidence: confidence,
            modelVersion: response.modelVersion,
            reasonCodes: response.reasonCodes.map(\.code),
            hasOutOfDomainFeatures: !response.outOfDomainFeatures.isEmpty
        )
    }

    private static func recommendation(
        id: String,
        prefix: String
    ) -> AssessmentDashboard.Recommendation {
        .init(
            id: id,
            titleKey: "\(prefix).title",
            detailKey: "\(prefix).detail",
            targetMetricKey: "\(prefix).metric"
        )
    }

    private static func income(
        _ sources: [AssessmentIncomeSourceResponse],
        business: Bool
    ) -> Int64 {
        let businessTypes = ["BUSINESS_REVENUE", "QRIS_SETTLEMENT", "MARKETPLACE_SETTLEMENT"]
        return sources
            .filter { businessTypes.contains($0.sourceType) == business }
            .reduce(0) { $0 + $1.averageAmount }
    }

    private static func score(_ value: String?) -> Int? {
        guard let value, let number = Double(value) else { return nil }
        return min(max(Int(number.rounded()), 0), 100)
    }

    private static func confidenceBand(_ value: String?) -> DataConfidenceReport.Band? {
        value.flatMap { DataConfidenceReport.Band(rawValue: $0.lowercased()) }
    }

    private static func riskBand(_ value: String?) -> AssessmentDashboard.RiskBand? {
        switch value {
        case "A": return .bandA
        case "B": return .bandB
        case "C": return .bandC
        case "D": return .bandD
        case "INSUFFICIENT_DATA": return .insufficientData
        default: return nil
        }
    }

    private static func modelConfidence(_ value: String?) -> AssessmentDashboard.ModelConfidence? {
        value.flatMap { AssessmentDashboard.ModelConfidence(rawValue: $0.lowercased()) }
    }

    private static func frequency(_ value: String?) -> AssessmentDashboard.RepaymentFrequency? {
        value.flatMap { AssessmentDashboard.RepaymentFrequency(rawValue: $0.lowercased()) }
    }
}
