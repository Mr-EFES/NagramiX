import Foundation

public struct NagramiXPrivacySettings: Equatable {
    public enum Option: String, CaseIterable {
        case storyReads, online, typing, readOnAction, screenshotBypass
    }

    public static let changedNotification = Notification.Name("NagramiXPrivacySettingsChanged")
    private static let key = "nagramix.privacy.individual.v2"
    private static let lock = NSLock()
    public var readMode: NagramiXReadMode
    private var options: [String: Bool]

    public init(readMode: NagramiXReadMode = .standard, options: [String: Bool] = ["typing": true]) {
        self.readMode = readMode
        self.options = options
    }

    public subscript(_ option: Option) -> Bool {
        get { self.options[option.rawValue] ?? false }
        set { self.options[option.rawValue] = newValue }
    }

    public var hidesMessageReads: Bool { self.readMode == .local || self[.readOnAction] }
    public var hidesStoryReads: Bool { self[.storyReads] }
    public var hidesOnline: Bool { self[.online] }
    public var hidesTyping: Bool { self[.typing] }
    // Compatibility for native presence/RPC observers: both behaviors now have
    // a single switch and cannot be enabled independently.
    public var automaticOffline: Bool { self.hidesOnline }
    public var readsOnAction: Bool { self[.readOnAction] }
    public var bypassScreenshots: Bool { self[.screenshotBypass] }

    public func requiresScreenshotProtection(_ required: Bool, allowsBypass: Bool) -> Bool {
        return required && !(allowsBypass && self.bypassScreenshots)
    }

    public enum PresenceDirective: Equatable { case online, offline, unchanged }
    public func presenceDirective(requestedOnline: Bool, forceOffline: Bool) -> PresenceDirective {
        if !requestedOnline { return .offline }
        // Hidden status has no intentional delay, including after an online event.
        if self.hidesOnline { return .offline }
        return .online
    }

    public static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.readMode == rhs.readMode && Option.allCases.allSatisfy { lhs[$0] == rhs[$0] }
    }

    // Keep privately read history protected after switching an option OFF.
    public static func preservesPrivateRead(privateMaxId: Int32?, localMaxId: Int32, serverMaxId: Int32) -> Bool {
        guard let privateMaxId else { return false }
        return localMaxId > serverMaxId && serverMaxId < privateMaxId && localMaxId <= privateMaxId
    }

    public static func read(from defaults: UserDefaults) -> Self {
        if let values = defaults.dictionary(forKey: self.key) {
            var options: [String: Bool] = [:]
            for option in Option.allCases { options[option.rawValue] = values[option.rawValue] as? Bool ?? false }
            // Either previously enabled protection keeps the merged switch ON.
            // Future writes omit the retired field, so explicit OFF stays OFF.
            options[Option.online.rawValue] = (values["online"] as? Bool ?? false) || (values["automaticOffline"] as? Bool ?? false)
            return Self(readMode: (values["readMode"] as? String).flatMap(NagramiXReadMode.init(rawValue:)) ?? .standard, options: options)
        }
        // Preserve effective behavior, not dormant selections under an OFF
        // master. Legacy keys stay intact for a downgrade; v2 wins after editing.
        let savedLegacy = defaults.dictionary(forKey: "nagramix.privacy.ghost.v1")
        let legacy = savedLegacy ?? [:]
        let master = legacy["enabled"] as? Bool ?? false
        func active(_ name: String) -> Bool { master && (legacy[name] as? Bool ?? true) }
        let explicitRaw = defaults.string(forKey: "nagramix.privacy.messageReadMode.v1")
        let explicitMode = explicitRaw.flatMap(NagramiXReadMode.init(rawValue:)) ?? .standard
        // The retired "server" choice becomes normal reading, even if an old
        // ghost master had dormant message hiding selected.
        let mode: NagramiXReadMode = explicitRaw != "server" && explicitMode == .standard && active("messageReads") ? .local : explicitMode
        var settings = Self(readMode: mode)
        for option in Option.allCases { settings[option] = active(option.rawValue) }
        // This option did not exist under the legacy master. Never inherit its
        // missing-field ON default when migrating an older installation.
        settings[.screenshotBypass] = false
        settings[.online] = active("online") || active("automaticOffline")
        settings[.storyReads] = settings[.storyReads] || (defaults.object(forKey: "nagramix.stories.anonymousViewing") as? Bool ?? false)
        // The previous explicit-local mode suppressed the reply exception.
        settings[.readOnAction] = explicitRaw != "server" && explicitMode == .standard && active("messageReads") && active("readOnAction")
        if savedLegacy == nil { settings[.typing] = true }
        return settings
    }

    public static var current: Self { self.read(from: .standard) }

    public static func update(in defaults: UserDefaults = .standard, _ transform: (inout Self) -> Void) {
        self.lock.lock()
        let previous = self.read(from: defaults)
        var updated = previous
        transform(&updated)
        if updated != previous {
            var values: [String: Any] = ["readMode": updated.readMode.rawValue]
            for option in Option.allCases { values[option.rawValue] = updated[option] }
            defaults.set(values, forKey: self.key)
        }
        self.lock.unlock()
        if updated != previous { NotificationCenter.default.post(name: self.changedNotification, object: nil) }
    }
}
