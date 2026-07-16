import Foundation

enum IDRFormatter {
    static func string(from amount: Int64) -> String {
        let formatter = NumberFormatter()
        formatter.locale = Locale(identifier: "id_ID")
        formatter.numberStyle = .decimal
        formatter.maximumFractionDigits = 0
        formatter.minimumFractionDigits = 0
        formatter.usesGroupingSeparator = true

        return "Rp\(formatter.string(from: NSNumber(value: amount)) ?? String(amount))"
    }
}
