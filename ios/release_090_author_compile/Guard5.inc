import Foundation

/// Foundation-only preferences shared by the settings and native call UI.
public enum NagramiXCallSettings {
    public static let skipRatingKey = "nagramix.calls.skipRating"

    public static var skipRating: Bool {
        return UserDefaults.standard.object(forKey: self.skipRatingKey) as? Bool ?? true
    }
}
