import Foundation

/// Shared by the settings UI and the native proxy observer. Existing values,
/// including false, are user choices and must survive every proxy activation.
public enum NagramiXProxyPreferences {
    public static let changedNotification = Notification.Name("NagramiXSettingsChanged")
    private static let lock = NSLock()
    private static let avoidVPNKey = "nagramix.network.avoidProxyWithVPN"
    private static let autoSwitchKey = "nagramix.network.proxyAutoSwitchEnabled"
    private static let timeoutKey = "nagramix.network.proxyAutoSwitchTimeout"

    public static func initializeIfNeeded(proxyEnabled: Bool, serverCount: Int) {
        guard proxyEnabled, serverCount > 0 else {
            return
        }
        self.lock.lock()
        let defaults = UserDefaults.standard
        var changed = false
        if defaults.object(forKey: self.avoidVPNKey) == nil {
            defaults.set(true, forKey: self.avoidVPNKey)
            changed = true
        }
        if serverCount >= 2 && defaults.object(forKey: self.autoSwitchKey) == nil {
            defaults.set(true, forKey: self.autoSwitchKey)
            changed = true
        }
        if defaults.object(forKey: self.timeoutKey) == nil {
            defaults.set(15, forKey: self.timeoutKey)
            changed = true
        }
        self.lock.unlock()
        if changed {
            NotificationCenter.default.post(name: self.changedNotification, object: nil)
        }
    }

    public static func setAvoidVPN(_ value: Bool) {
        self.set(value, forKey: self.avoidVPNKey)
    }

    public static func setAutoSwitch(_ value: Bool) {
        self.set(value, forKey: self.autoSwitchKey)
    }

    private static func set(_ value: Bool, forKey key: String) {
        self.lock.lock()
        UserDefaults.standard.set(value, forKey: key)
        self.lock.unlock()
        NotificationCenter.default.post(name: self.changedNotification, object: nil)
    }
}
