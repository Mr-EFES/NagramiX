import Foundation

// Shared by TelegramCore and presentation code without introducing a dependency cycle.
public enum NagramiXStorySettings {
    private static let anonymousViewingKey = "nagramix.stories.anonymousViewing"

    public static var anonymousViewingEnabled: Bool {
        return UserDefaults.standard.object(forKey: self.anonymousViewingKey) as? Bool ?? false
    }

    public static func update(anonymousViewing: Bool) {
        UserDefaults.standard.set(anonymousViewing, forKey: self.anonymousViewingKey)
    }
}
