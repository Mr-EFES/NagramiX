import Foundation

/// Foundation-only so presentation formatting does not depend on UI modules.
public enum NagramiXNumberSettings {
    private static let roundingKey = "nagramix.interface.roundNumbers"
    public static let changedNotification = Notification.Name("NagramiXNumberFormatChanged")

    public static var roundingEnabled: Bool {
        return UserDefaults.standard.object(forKey: self.roundingKey) as? Bool ?? false
    }

    public static func setRoundingEnabled(_ enabled: Bool) {
        UserDefaults.standard.set(enabled, forKey: self.roundingKey)
        NotificationCenter.default.post(name: self.changedNotification, object: nil)
    }

    /// Keep every digit, including the minimum signed integer. Do not use abs
    /// or floating point, which can overflow or lose large counter values.
    public static func fullCountString<T: BinaryInteger>(_ count: T, groupingSeparator: String = Locale.current.groupingSeparator ?? "\u{00a0}") -> String {
        let digits = String(count.magnitude)
        guard !groupingSeparator.isEmpty, digits.count > 3 else { return String(count) }
        var result = count < 0 ? "-" : ""
        for (index, digit) in digits.enumerated() {
            if index > 0 && (digits.count - index) % 3 == 0 { result += groupingSeparator }
            result.append(digit)
        }
        return result
    }
}
