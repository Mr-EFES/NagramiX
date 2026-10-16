import Foundation

// Shared by TelegramCore and the settings UI without a presentation dependency.
public enum NagramiXAdvertisingSettings {
    public static let changedNotification = Notification.Name("NagramiXAdvertisingSettingsChanged")

    public static var showAdvertising: Bool {
        let defaults = UserDefaults.standard
        if let hidden = defaults.object(forKey: "nagramix.interface.hideProxySponsorChannel") as? Bool {
            return !hidden
        }
        // Preserve the choice made by builds predating the inverse hide key.
        return defaults.object(forKey: "nagramix.interface.showProxySponsorChannel") as? Bool ?? false
    }
}
