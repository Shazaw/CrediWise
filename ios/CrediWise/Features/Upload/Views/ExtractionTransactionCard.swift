import Foundation
import SwiftUI

struct ExtractionTransactionCard: View {
    let transaction: ExtractionReview.Transaction
    let correction: ExtractionReview.Correction?
    let onDateChange: (String) -> Void
    let onDescriptionChange: (String) -> Void
    let onAmountChange: (Int64) -> Void
    let onCategoryChange: (ExtractionReview.Category) -> Void
    let onInternalTransferChange: (Bool) -> Void
    let onDuplicateChange: (Bool) -> Void
    let onValidityChange: (Bool) -> Void

    @State private var isEditing = false
    @State private var dateText: String
    @State private var descriptionText: String
    @State private var amountText: String

    init(
        transaction: ExtractionReview.Transaction,
        correction: ExtractionReview.Correction?,
        onDateChange: @escaping (String) -> Void,
        onDescriptionChange: @escaping (String) -> Void,
        onAmountChange: @escaping (Int64) -> Void,
        onCategoryChange: @escaping (ExtractionReview.Category) -> Void,
        onInternalTransferChange: @escaping (Bool) -> Void,
        onDuplicateChange: @escaping (Bool) -> Void,
        onValidityChange: @escaping (Bool) -> Void
    ) {
        self.transaction = transaction
        self.correction = correction
        self.onDateChange = onDateChange
        self.onDescriptionChange = onDescriptionChange
        self.onAmountChange = onAmountChange
        self.onCategoryChange = onCategoryChange
        self.onInternalTransferChange = onInternalTransferChange
        self.onDuplicateChange = onDuplicateChange
        self.onValidityChange = onValidityChange
        _dateText = State(initialValue: correction?.proposedDate ?? transaction.date.normalized)
        _descriptionText = State(
            initialValue: correction?.proposedDescription ?? transaction.description.normalized
        )
        _amountText = State(
            initialValue: String(correction?.proposedAmount ?? transaction.amount.normalized)
        )
    }

    var body: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
                    Text(verbatim: correction?.proposedDate ?? transaction.date.normalized)
                        .font(TypographyTokens.caption)
                        .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.65))
                    Text(verbatim: correction?.proposedDescription ?? transaction.description.normalized)
                        .font(TypographyTokens.cardTitle)
                        .foregroundStyle(CrediWiseColors.textPrimary)
                }
                Spacer()
                Text(verbatim: IDRFormatter.string(from: proposedAmount))
                    .font(.headline.monospacedDigit())
                    .foregroundStyle(proposedAmount >= 0 ? CrediWiseColors.success : CrediWiseColors.textPrimary)
            }

            HStack(spacing: SpacingTokens.small) {
                valuePill(NSLocalizedString(categoryKey(proposedCategory), comment: "Transaction category"))
                valuePill(
                    String(
                        format: NSLocalizedString("review.transaction.confidence", comment: "Extraction confidence"),
                        transaction.extractionConfidence
                    )
                )
            }

            if correction != nil {
                Label("review.transaction.proposed_badge", systemImage: "pencil.circle.fill")
                    .font(TypographyTokens.caption.weight(.semibold))
                    .foregroundStyle(CrediWiseColors.primary)
            }

            DisclosureGroup("review.transaction.source_values", isExpanded: $isEditing) {
                VStack(alignment: .leading, spacing: SpacingTokens.medium) {
                    sourceValue(
                        titleKey: "review.transaction.raw",
                        description: transaction.description.raw,
                        amount: transaction.amount.raw
                    )
                    sourceValue(
                        titleKey: "review.transaction.normalized",
                        description: transaction.description.normalized,
                        amount: transaction.amount.normalized
                    )
                    correctionControls
                }
                .padding(.top, SpacingTokens.medium)
            }
            .font(.subheadline.weight(.semibold))
            .tint(CrediWiseColors.primary)
            .accessibilityIdentifier("review.transaction.\(transaction.id).edit")
        }
        .padding(SpacingTokens.standard)
        .background(CrediWiseColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.card))
        .overlay {
            RoundedRectangle(cornerRadius: RadiusTokens.card)
                .stroke(CrediWiseColors.primaryTint, lineWidth: 1)
        }
        .accessibilityIdentifier("review.transaction.\(transaction.id)")
    }

    private var proposedAmount: Int64 {
        correction?.proposedAmount ?? transaction.amount.normalized
    }

    private var proposedCategory: ExtractionReview.Category {
        correction?.proposedCategory ?? transaction.category.normalized
    }

    private var amountIsValid: Bool {
        Int64(amountText) != nil
    }

    private var fieldsAreValid: Bool {
        amountIsValid &&
            !dateText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty &&
            !descriptionText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private var correctionControls: some View {
        VStack(alignment: .leading, spacing: SpacingTokens.medium) {
            Text("review.transaction.correction_title")
                .font(TypographyTokens.cardTitle)

            TextField("review.transaction.date", text: $dateText)
                .textFieldStyle(.roundedBorder)
                .onChange(of: dateText) { value in
                    onDateChange(value)
                    onValidityChange(fieldsAreValid)
                }

            TextField("review.transaction.description", text: $descriptionText)
                .textFieldStyle(.roundedBorder)
                .onChange(of: descriptionText) {
                    onDescriptionChange($0)
                    onValidityChange(fieldsAreValid)
                }

            TextField("review.transaction.amount", text: $amountText)
                .keyboardType(.numbersAndPunctuation)
                .textFieldStyle(.roundedBorder)
                .onChange(of: amountText) { value in
                    if let amount = Int64(value) {
                        onAmountChange(amount)
                    }
                    onValidityChange(fieldsAreValid)
                }
                .accessibilityIdentifier("review.transaction.\(transaction.id).amount")

            if !fieldsAreValid {
                Text("review.transaction.amount_error")
                    .font(TypographyTokens.caption)
                    .foregroundStyle(CrediWiseColors.danger)
            }

            Picker(
                "review.transaction.category",
                selection: Binding(
                    get: { proposedCategory },
                    set: onCategoryChange
                )
            ) {
                ForEach(ExtractionReview.Category.allCases, id: \.self) { category in
                    Text(LocalizedStringKey(categoryKey(category))).tag(category)
                }
            }
            .pickerStyle(.menu)

            Toggle(
                "review.transaction.internal_transfer",
                isOn: Binding(
                    get: { correction?.proposedInternalTransfer ?? transaction.internalTransfer.normalized },
                    set: onInternalTransferChange
                )
            )

            Toggle(
                "review.transaction.duplicate",
                isOn: Binding(
                    get: { correction?.proposedDuplicate ?? transaction.duplicate.normalized },
                    set: onDuplicateChange
                )
            )
        }
    }

    private func sourceValue(titleKey: String, description: String, amount: Int64) -> some View {
        VStack(alignment: .leading, spacing: SpacingTokens.xSmall) {
            Text(LocalizedStringKey(titleKey))
                .font(TypographyTokens.caption.weight(.semibold))
                .foregroundStyle(CrediWiseColors.textPrimary.opacity(0.65))
            Text(verbatim: description)
                .font(TypographyTokens.body)
            Text(verbatim: IDRFormatter.string(from: amount))
                .font(TypographyTokens.caption.monospacedDigit())
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(SpacingTokens.medium)
        .background(CrediWiseColors.surfaceAlt)
        .clipShape(RoundedRectangle(cornerRadius: RadiusTokens.chip))
    }

    private func valuePill(_ value: String) -> some View {
        Text(verbatim: value)
            .font(TypographyTokens.caption.weight(.semibold))
            .foregroundStyle(CrediWiseColors.primaryDark)
            .padding(.horizontal, SpacingTokens.medium)
            .padding(.vertical, SpacingTokens.small)
            .background(CrediWiseColors.primaryTint)
            .clipShape(Capsule())
    }

    private func categoryKey(_ category: ExtractionReview.Category) -> String {
        "review.category.\(category.rawValue)"
    }
}
