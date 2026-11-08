import Foundation

/// Default for new outgoing messages; never reset a saved choice on launch.
public enum NagramiXSendSettings {
    private static let silentKey = "nagramix.messages.sendSilently"

    public static var sendSilently: Bool {
        return UserDefaults.standard.object(forKey: self.silentKey) as? Bool ?? true
    }

    public static func setSendSilently(_ value: Bool) {
        UserDefaults.standard.set(value, forKey: self.silentKey)
    }
}
