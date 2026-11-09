import Foundation

/// Shared by the settings UI and the native proxy observer. Existing values,
/// including false, are user choices and must survive every proxy activation.
public enum NagramiXProxyPreferences {
    public static let changedNotification = Notification.Name("NagramiXSettingsChanged")
    private static let lock = NSLock()
    private static let avoidVPNKey = "nagramix.network.avoidProxyWithVPN"
    private static let autoSwitchKey = "nagramix.network.proxyAutoSwitchEnabled"
    private static let timeoutKey = "nagramix.network.proxyAutoSwitchTimeout"
    private static let preferIPv6Key = "nagramix.network.preferIPv6"

    public static var preferIPv6: Bool {
        return UserDefaults.standard.object(forKey: self.preferIPv6Key) as? Bool ?? false
    }

    public static func setPreferIPv6(_ value: Bool) {
        self.set(value, forKey: self.preferIPv6Key)
        // Reuse the existing per-account reconnect, which respects the native
        // keep-connection state and does not wake paused/background accounts.
        NotificationCenter.default.post(name: Notification.Name("NagramiXDnsSettingsChanged"), object: nil)
    }

    public static var autoSwitchEnabled: Bool {
        return UserDefaults.standard.object(forKey: self.autoSwitchKey) as? Bool ?? true
    }

    public static var autoSwitchTimeout: Int {
        let value = UserDefaults.standard.integer(forKey: self.timeoutKey)
        return [15, 30, 60].contains(value) ? value : 30
    }

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
        if defaults.object(forKey: self.autoSwitchKey) == nil {
            defaults.set(true, forKey: self.autoSwitchKey)
            changed = true
        }
        if defaults.object(forKey: self.timeoutKey) == nil {
            defaults.set(30, forKey: self.timeoutKey)
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
