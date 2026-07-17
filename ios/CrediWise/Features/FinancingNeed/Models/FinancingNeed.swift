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

    enum Urgency: String, CaseIterable, Equatable, Sendable {
        case low
        case medium
        case high

        var titleKey: String {
            "financing_need.urgency.\(rawValue)"
        }
    }

    let requestedAmount: Int64
    let purpose: Purpose
    let preferredTenorMonths: Int
    let urgency: Urgency
    let notes: String
}

struct FinancingNeedReceipt: Equatable, Sendable {
    let financingNeedID: String
}
