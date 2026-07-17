import SwiftUI

struct OfferDetailView: View {
    @StateObject private var viewModel: OfferDetailViewModel
    @State private var operationTask: Task<Void, Never>?

    init(viewModel: OfferDetailViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel)
    }

    var body: some View {
        ZStack {
            CrediWiseColors.surfaceAlt.ignoresSafeArea()
            ScrollView {
                VStack(alignment: .leading, spacing: SpacingTokens.large) {
                    content
                    DisclaimerFooter()
                }
                .padding(SpacingTokens.large)
            }
        }
        .navigationTitle("offer_detail.navigation_title")
        .navigationBarTitleDisplayMode(.inline)
        .task { await viewModel.load() }
        .onDisappear { operationTask?.cancel() }
        .accessibilityIdentifier("offers.detail.screen")
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            ProgressView("offers.loading")
                .tint(CrediWiseColors.primary)
                .frame(maxWidth: .infinity)
                .padding(SpacingTokens.xxLarge)
        case let .loaded(offer):
            offerContent(offer)
        case let .failed(errorKey):
            VStack(alignment: .leading, spacing: SpacingTokens.medium) {
                Text("offers.error.title")
                    .font(TypographyTokens.cardTitle)
                Text(LocalizedStringKey(errorKey))
                    .font(TypographyTokens.body)
                PrimaryButton(title: "common.retry") {
                    operationTask = Task { await viewModel.retry() }
                }
            }
        }
    }

    private func offerContent(_ offer: SafeOffer) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.large) {
            VStack(alignment: .leading, spacing: SpacingTokens.small) {
                Text(LocalizedStringKey(offer.provider.nameKey))
                    .font(TypographyTokens.title)
                Label("offers.provider.simulated", systemImage: "testtube.2")
                    .font(TypographyTokens.caption.weight(.bold))
                    .foregroundStyle(CrediWiseColors.primary)
                    .accessibilityIdentifier("offers.simulated")
                Text(
                    String(
                        format: NSLocalizedString("offer_detail.score", comment: "Safe Offer Score"),
                        offer.score,
                        NSLocalizedString("offers.band.\(offer.band.rawValue)", comment: "Safety band")
                    )
                )
                .font(TypographyTokens.cardTitle)
            }

            if !offer.warnings.isEmpty {
                warningSection(offer.warnings)
            }

            detailCard(title: "offer_detail.proceeds.title") {
                amountRow("offer_detail.principal", offer.principal)
                amountRow("offer_detail.net_received", offer.netAmountReceived)
                amountRow("offer_detail.instalment", offer.instalment)
                textRow("offer_detail.tenor", tenorText(offer.tenorMonths))
                textRow("offer_detail.frequency", localizedFrequency(offer.paymentFrequency))
                textRow("offer_detail.due_day", dueDayText(offer.dueDayOfMonth))
                textRow("offer_detail.amortization", localizedAmortization(offer.amortizationMethod))
                textRow("offer_detail.nominal_rate", nominalRateText(offer))
                textRow("offer_detail.rate_basis", localizedRateBasis(offer.rateBasis))
                textRow("offer_detail.schedule", paymentScheduleText(offer.scheduledPayments))
            }

            detailCard(title: "offer_detail.costs.title") {
                amountRow("offer_detail.interest", offer.costs.scheduledInterest)
                amountRow("offer_detail.upfront_fees", offer.costs.upfrontFees)
                amountRow("offer_detail.financed_fees", offer.costs.financedFees)
                amountRow("offer_detail.total_repayment", offer.costs.totalScheduledRepayment)
                textRow("offer_detail.effective_cost", effectiveCostText(offer.costs))
                textRow(
                    "offer_detail.penalty_terms",
                    NSLocalizedString(offer.costs.penaltyTermsKey, comment: "Penalty terms")
                )
            }

            detailCard(title: "offer_detail.safety.title") {
                amountRow("offer_detail.essential_coverage", offer.remainingEssentialCoverage)
                textRow(
                    "offer_detail.refinancing_dependency",
                    NSLocalizedString(
                        offer.refinancingDependency ? "common.yes" : "common.no",
                        comment: "Boolean value"
                    )
                )
                ForEach(offer.reasons) { reason in
                    VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                        Text(LocalizedStringKey(reason.titleKey))
                            .font(TypographyTokens.body.weight(.semibold))
                        Text(LocalizedStringKey(reason.detailKey))
                            .font(TypographyTokens.caption)
                            .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
                    }
                }
            }

            Text("offer_detail.lender_notice")
                .font(TypographyTokens.caption)
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))

            Text(
                String(
                    format: NSLocalizedString("offers.model_version", comment: "Offer model version"),
                    offer.modelVersion
                )
            )
            .font(TypographyTokens.caption)
            .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.62))
        }
    }

    private func warningSection(_ warnings: [SafeOffer.Warning]) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium) {
            ForEach(warnings) { warning in
                VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                    Label(LocalizedStringKey(warning.titleKey), systemImage: "exclamationmark.triangle.fill")
                        .font(TypographyTokens.body.weight(.bold))
                    Text(LocalizedStringKey(warning.detailKey))
                        .font(TypographyTokens.caption)
                }
                .accessibilityIdentifier("offers.warning.\(warning.code)")
            }
        }
        .foregroundStyle(CrediWiseColors.danger)
        .padding(SpacingTokens.standard)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(CrediWiseColors.danger.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.button))
    }

    private func detailCard<Content: View>(
        title: LocalizedStringKey,
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium) {
            Text(title)
                .font(TypographyTokens.cardTitle)
            content()
        }
        .padding(SpacingTokens.large)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
    }

    private func amountRow(_ title: LocalizedStringKey, _ amount: Int64) -> some View {
        LabeledContent(title) {
            Text(verbatim: IDRFormatter.string(from: amount))
                .font(TypographyTokens.body.monospacedDigit())
        }
    }

    private func textRow(_ title: LocalizedStringKey, _ value: String) -> some View {
        LabeledContent(title) {
            Text(verbatim: value)
                .multilineTextAlignment(.trailing)
        }
    }

    private func tenorText(_ months: Int) -> String {
        String(format: NSLocalizedString("offer_detail.tenor_value", comment: "Tenor"), months)
    }

    private func localizedFrequency(_ frequency: SafeOffer.PaymentFrequency) -> String {
        NSLocalizedString("offers.frequency.\(frequency.rawValue)", comment: "Payment frequency")
    }

    private func dueDayText(_ day: Int) -> String {
        String(format: NSLocalizedString("offer_detail.due_day_value", comment: "Payment due day"), day)
    }

    private func localizedAmortization(_ method: SafeOffer.AmortizationMethod) -> String {
        NSLocalizedString("offers.amortization.\(method.rawValue)", comment: "Amortization method")
    }

    private func nominalRateText(_ offer: SafeOffer) -> String {
        guard let percentage = offer.nominalAnnualRatePercentage else {
            return NSLocalizedString("dashboard.value.unavailable", comment: "Unavailable value")
        }
        return String(
            format: NSLocalizedString("offer_detail.nominal_rate_value", comment: "Nominal annual rate"),
            percentage
        )
    }

    private func localizedRateBasis(_ basis: SafeOffer.RateBasis?) -> String {
        guard let basis else {
            return NSLocalizedString("dashboard.value.unavailable", comment: "Unavailable value")
        }
        return NSLocalizedString("offers.rate_basis.\(basis.rawValue)", comment: "Rate basis")
    }

    private func paymentScheduleText(_ payments: [SafeOffer.ScheduledPayment]) -> String {
        guard let first = payments.first else {
            return NSLocalizedString("dashboard.value.unavailable", comment: "Unavailable value")
        }
        let amounts = payments.map(\.amount)
        guard amounts.allSatisfy({ $0 == first.amount }) else {
            return String(
                format: NSLocalizedString("offer_detail.schedule_variable", comment: "Variable payment schedule"),
                payments.count,
                IDRFormatter.string(from: amounts.min() ?? 0),
                IDRFormatter.string(from: amounts.max() ?? 0)
            )
        }
        return String(
            format: NSLocalizedString("offer_detail.schedule_value", comment: "Payment schedule"),
            payments.count,
            IDRFormatter.string(from: first.amount)
        )
    }

    private func effectiveCostText(_ costs: SafeOffer.CostBreakdown) -> String {
        guard let percentage = costs.effectiveAnnualCostPercentage else {
            return NSLocalizedString("dashboard.value.unavailable", comment: "Unavailable value")
        }
        return String(
            format: NSLocalizedString("offer_detail.effective_cost_value", comment: "Effective annual cost"),
            percentage
        )
    }
}
