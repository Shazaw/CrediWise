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
        case let .loaded(offer):
            offerContent(offer)
        case let .failed(errorKey):
            VStack(alignment: .leading, spacing: SpacingTokens.medium) {
                Text("offers.error.title").font(TypographyTokens.cardTitle)
                Text(LocalizedStringKey(errorKey))
                PrimaryButton(title: "common.retry") {
                    operationTask = Task { await viewModel.retry() }
                }
            }
        }
    }

    private func offerContent(_ offer: SafeOffer) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.large) {
            offerHeader(offer)
            if offer.offerSource == .simulated {
                if offer.simulationNotice != nil {
                    Text("offers.simulation_notice")
                        .font(TypographyTokens.caption.weight(.bold))
                        .foregroundStyle(CrediWiseColors.primary)
                        .accessibilityIdentifier("offers.simulated")
                }
            }
            if !offer.warnings.isEmpty { warningSection(offer.warnings) }
            proceedsCard(offer)
            costsCard(offer)
            scheduleCard(offer)
            safetyCard(offer)
            VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                Text("offers.explanation.title")
                    .font(TypographyTokens.cardTitle)
                Text("offers.explanation.context")
                    .font(TypographyTokens.caption)
                    .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.72))
                Text("offers.explanation.summary")
                    .font(TypographyTokens.body)
            }
            Text("offer_detail.lender_notice")
                .font(TypographyTokens.caption)
            lineage(offer)
        }
    }

    private func offerHeader(_ offer: SafeOffer) -> some View {
        HStack(alignment: .top, spacing: SpacingTokens.medium) {
            if let logoURL = offer.provider.logoURL {
                AsyncImage(url: logoURL) { image in
                    image.resizable().scaledToFit()
                } placeholder: {
                    ProgressView()
                }
                .frame(width: 48, height: 48)
                .accessibilityHidden(true)
            }
            VStack(alignment: .leading, spacing: SpacingTokens.small) {
                Text(verbatim: offer.provider.displayName).font(TypographyTokens.title)
                Text(LocalizedStringKey("offers.source.\(offer.offerSource.rawValue)"))
                    .font(TypographyTokens.caption.weight(.bold))
                Text(LocalizedStringKey("offers.provider_status.\(offer.provider.status.rawValue)"))
                    .font(TypographyTokens.caption)
                Text(
                    String(
                        format: NSLocalizedString("offer_detail.score", comment: "Safe Offer Score"),
                        NSDecimalNumber(decimal: offer.safeOfferScore).doubleValue,
                        NSLocalizedString("offers.band.\(offer.band.rawValue)", comment: "Safety band")
                    )
                )
                .font(TypographyTokens.cardTitle)
            }
        }
    }

    private func proceedsCard(_ offer: SafeOffer) -> some View {
        detailCard(title: "offer_detail.proceeds.title") {
            amountRow("offer_detail.principal", offer.principalAmount)
            amountRow("offer_detail.net_received", offer.netDisbursedAmount)
            amountRow("offer_detail.instalment", offer.instalmentAmount)
            textRow("offer_detail.tenor", format("offer_detail.tenor_value", offer.tenorMonths))
            textRow("offer_detail.frequency", localized("offers.frequency.\(offer.paymentFrequency.rawValue)"))
            textRow("offer_detail.due_day", format("offer_detail.due_day_value", offer.dueDayOfMonth))
            textRow("offer_detail.amortization", localized("offers.amortization.\(offer.amortizationMethod.rawValue)"))
            textRow("offer_detail.nominal_rate", percentage(offer.nominalRate))
            textRow("offer_detail.rate_basis", localized("offers.rate_basis.\(offer.nominalRateBasis.rawValue)"))
        }
    }

    private func costsCard(_ offer: SafeOffer) -> some View {
        detailCard(title: "offer_detail.costs.title") {
            amountRow("offer_detail.interest", offer.costs.scheduledInterest)
            amountRow("offer_detail.upfront_fees", offer.costs.upfrontFee)
            amountRow("offer_detail.financed_fees", offer.costs.financedFee)
            amountRow("offer_detail.service_fee", offer.costs.serviceFee)
            amountRow("offer_detail.admin_fee", offer.costs.adminFee)
            amountRow("offer_detail.total_repayment", offer.costs.totalScheduledRepayment)
            textRow("offer_detail.effective_cost", percentage(offer.costs.effectiveAnnualRate))
            textRow("offer_detail.penalty_terms", penaltyText(offer.costs.latePenaltyTerms))
        }
    }

    private func scheduleCard(_ offer: SafeOffer) -> some View {
        detailCard(title: "offer_detail.schedule.title") {
            ForEach(offer.paymentSchedule) { payment in
                VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                    Text(format("offer_detail.schedule.period", payment.period))
                        .font(TypographyTokens.body.weight(.semibold))
                    amountRow("offer_detail.schedule.payment", payment.paymentAmount)
                    amountRow("offer_detail.schedule.principal", payment.principalComponent)
                    amountRow("offer_detail.schedule.interest", payment.interestComponent)
                    amountRow("offer_detail.schedule.balance", payment.remainingBalance)
                }
                Divider()
            }
        }
    }

    private func safetyCard(_ offer: SafeOffer) -> some View {
        detailCard(title: "offer_detail.safety.title") {
            textRow(
                "offer_detail.affordability_status",
                localized("offers.affordability.\(offer.affordabilityStatus.rawValue)")
            )
            textRow(
                "offer_detail.shock_status",
                localized("offers.confidence.\(offer.shockResilienceStatus.rawValue)")
            )
            textRow("offer_detail.cost_status", localized("offers.rating.\(offer.totalCostStatus.rawValue)"))
            textRow("offer_detail.timing_status", localized("offers.rating.\(offer.timingStatus.rawValue)"))
            amountRow("offer_detail.essential_coverage", offer.remainingEssentialExpenseCoverage.amount)
            textRow(
                "offer_detail.essential_coverage_ratio",
                String(
                    format: localized("offer_detail.rate_value"),
                    offer.remainingEssentialExpenseCoverage.displayPercentage
                )
            )
            textRow(
                "offer_detail.refinancing_dependency",
                localized(offer.refinancingDependency ? "common.yes" : "common.no")
            )
            if offer.refinancingDependency {
                Text("offers.warning.refinancing_dependency.detail")
                    .font(TypographyTokens.caption.weight(.semibold))
                    .foregroundStyle(CrediWiseColors.danger)
            }
            ForEach(offer.reasons) { reason in
                VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                    Text(LocalizedStringKey(reason.titleKey))
                        .font(TypographyTokens.body.weight(.semibold))
                    if !reason.isKnown {
                        Text(
                            String(
                                format: localized("offers.reason.unknown_code"),
                                reason.code
                            )
                        )
                        .font(TypographyTokens.caption.monospaced())
                    }
                    if let detailKey = reason.detailKey {
                        Text(LocalizedStringKey(detailKey)).font(TypographyTokens.caption)
                    } else {
                        Text(verbatim: reason.description).font(TypographyTokens.caption)
                    }
                }
            }
        }
    }

    private func warningSection(_ warnings: [SafeOffer.Warning]) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium) {
            ForEach(warnings) { warning in
                VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                    Label(LocalizedStringKey(warning.titleKey), systemImage: "exclamationmark.triangle.fill")
                        .font(TypographyTokens.body.weight(.bold))
                    Text(LocalizedStringKey(warning.detailKey)).font(TypographyTokens.caption)
                    if warning.usesGenericCopy {
                        Text(verbatim: warning.code).font(TypographyTokens.caption.monospaced())
                    }
                }
                .accessibilityIdentifier("offers.warning.\(warning.code)")
            }
        }
        .foregroundStyle(CrediWiseColors.danger)
        .padding(SpacingTokens.standard)
        .background(CrediWiseColors.danger.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.button))
    }

    private func lineage(_ offer: SafeOffer) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
            Text(String(format: localized("offers.model_version"), offer.modelVersion))
        }
        .font(TypographyTokens.caption)
        .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.62))
    }

    private func detailCard<Content: View>(
        title: LocalizedStringKey,
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium) {
            Text(title).font(TypographyTokens.cardTitle)
            content()
        }
        .padding(SpacingTokens.large)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
    }

    private func amountRow(_ title: LocalizedStringKey, _ amount: Int64) -> some View {
        LabeledContent(title) { Text(verbatim: IDRFormatter.string(from: amount)) }
    }

    private func textRow(_ title: LocalizedStringKey, _ value: String) -> some View {
        LabeledContent(title) { Text(verbatim: value).multilineTextAlignment(.trailing) }
    }

    private func percentage(_ rate: SafeOffer.Rate?) -> String {
        guard let rate else { return localized("dashboard.value.unavailable") }
        return String(format: localized("offer_detail.rate_value"), rate.displayPercentage)
    }

    private func penaltyText(_ terms: SafeOffer.LatePenaltyTerms?) -> String {
        guard let terms else { return localized("offer_detail.penalty_none") }
        let rate = percentage(terms.rate)
        let amount = terms.amount.map { IDRFormatter.string(from: $0) }
            ?? localized("dashboard.value.unavailable")
        return String(
            format: localized("offer_detail.penalty_value"),
            terms.triggerDays,
            rate,
            amount,
            localized("offers.penalty_basis.\(terms.basis.rawValue)")
        )
    }

    private func localized(_ key: String) -> String {
        NSLocalizedString(key, comment: "Offer detail value")
    }

    private func format(_ key: String, _ value: Int) -> String {
        String(format: localized(key), value)
    }
}
