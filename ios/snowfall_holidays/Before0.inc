import Foundation

public struct NagramiXSnowConfiguration: Equatable {
    public var enabled = false
    public var inChats = true
    public var density = 100
    public init() {}
}

public enum NagramiXSnowSettings {
    public static let changedNotification = Notification.Name("NagramiXSnowSettingsChanged")
    private static let key = "nagramix.atmosphere.snowfall"
    private static let lock = NSLock()
    private static var cached = read(in: .standard)

    public static func normalizedDensity(_ value: Int) -> Int {
        return ((min(100, max(10, value)) + 2) / 5) * 5
    }

    public static func read(in defaults: UserDefaults) -> NagramiXSnowConfiguration {
        let stored = defaults.dictionary(forKey: self.key) ?? [:]
        var value = NagramiXSnowConfiguration()
        value.enabled = stored["enabled"] as? Bool ?? false
        value.inChats = stored["inChats"] as? Bool ?? true
        value.density = self.normalizedDensity(stored["density"] as? Int ?? 100)
        return value
    }

    public static var current: NagramiXSnowConfiguration {
        self.lock.lock()
        defer { self.lock.unlock() }
        return self.cached
    }

    public static func update(_ transform: (inout NagramiXSnowConfiguration) -> Void) {
        self.lock.lock()
        var value = self.cached
        transform(&value)
        value.density = self.normalizedDensity(value.density)
        guard value != self.cached else { self.lock.unlock(); return }
        self.cached = value
        UserDefaults.standard.set(["enabled": value.enabled, "inChats": value.inChats, "density": value.density], forKey: self.key)
        self.lock.unlock()
        NotificationCenter.default.post(name: self.changedNotification, object: nil)
    }
}
