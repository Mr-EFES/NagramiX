import Foundation

// Shared by TelegramCore and presentation code without introducing a dependency cycle.
public enum NagramiXStorySettings {
    public static var anonymousViewingEnabled: Bool {
        return NagramiXPrivacySettings.current.hidesStoryReads
    }

    public static var effectiveAnonymousViewingEnabled: Bool {
        self.anonymousViewingEnabled
    }

    public static func update(anonymousViewing: Bool) {
        NagramiXPrivacySettings.update { $0[.storyReads] = anonymousViewing }
    }
}
