import Foundation

/// One persisted default for new voice and round-video recordings.
/// A recording's native view-once state remains independently editable.
public enum NagramiXRecordingSettings {
    private static let viewOnceKey = "nagramix.recording.viewOnce"

    public static var viewOnceEnabled: Bool {
        return UserDefaults.standard.object(forKey: self.viewOnceKey) as? Bool ?? false
    }

    public static func setViewOnceEnabled(_ enabled: Bool) {
        UserDefaults.standard.set(enabled, forKey: self.viewOnceKey)
        NotificationCenter.default.post(name: NagramiXTabSettings.changedNotification, object: nil)
    }

    public static func initialViewOnce(available: Bool) -> Bool {
        return available && self.viewOnceEnabled
    }
}
