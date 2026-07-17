struct FinancingNeed: Equatable, Sendable {
    enum Purpose: String, CaseIterable, Equatable, Sendable {
        case medical
        case education
        case householdEmergency
        case productiveBusiness
        case equipment
        case workingCapital
        case vehicleDeviceRepair

        var titleKey: String {
            "financing_need.purpose.\(rawValue)"
        }
    }

    let requestedAmount: Int64
    let purpose: Purpose
    let preferredTenorMonths: Int
    let notes: String
}

struct FinancingNeedReceipt: Equatable, Sendable {
    let financingNeedID: String
}
