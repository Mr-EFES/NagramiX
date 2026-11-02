import Foundation

public enum NagramiXStoryDownloadSettings {
    public static let changedNotification = Notification.Name("NagramiXStoryDownloadChanged")
    private static let key = "nagramix.stories.download"

    public static var enabled: Bool {
        return UserDefaults.standard.object(forKey: self.key) as? Bool ?? false
    }

    public static func setEnabled(_ value: Bool) {
        UserDefaults.standard.set(value, forKey: self.key)
        NotificationCenter.default.post(name: self.changedNotification, object: nil)
        NotificationCenter.default.post(name: NagramiXTabSettings.changedNotification, object: nil)
    }
}
