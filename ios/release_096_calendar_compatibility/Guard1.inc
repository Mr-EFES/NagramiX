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

    private struct Day {
        let interval: DateInterval
        let zone: String
        let window: NagramiXSnowHolidays.Window?
    }
    private static var day: Day?
    private static var published: NagramiXSnowConfiguration?
    private static let startSchedule: Void = {
        DispatchQueue.main.async { NagramiXSnowSchedule.shared.start() }
    }()

    private static func effectiveLocked(at date: Date, timeZone: TimeZone) -> NagramiXSnowConfiguration {
        if self.day == nil || self.day!.zone != timeZone.identifier || date < self.day!.interval.start || date >= self.day!.interval.end {
            self.day = NagramiXSnowHolidays.dayInterval(at: date, timeZone: timeZone).map {
                Day(interval: $0, zone: timeZone.identifier, window: NagramiXSnowHolidays.window(at: date, timeZone: timeZone))
            }
        }
        return NagramiXSnowHolidays.configuration(self.cached, during: self.day?.window)
    }

    public static func configuration(at date: Date, timeZone: TimeZone) -> NagramiXSnowConfiguration {
        self.lock.lock()
        defer { self.lock.unlock() }
        let value = self.effectiveLocked(at: date, timeZone: timeZone)
        if self.published == nil { self.published = value }
        return value
    }

    public static var current: NagramiXSnowConfiguration {
        _ = self.startSchedule
        return self.configuration(at: Date(), timeZone: .autoupdatingCurrent)
    }

    public static func refreshSchedule(at date: Date = Date(), timeZone: TimeZone = .autoupdatingCurrent) {
        self.lock.lock()
        self.day = nil
        let value = self.effectiveLocked(at: date, timeZone: timeZone)
        let changed = self.published != nil && self.published != value
        self.published = value
        self.lock.unlock()
        if changed { NotificationCenter.default.post(name: self.changedNotification, object: nil) }
    }

    public static func update(_ transform: (inout NagramiXSnowConfiguration) -> Void) {
        self.lock.lock()
        var value = self.cached
        transform(&value)
        value.density = self.normalizedDensity(value.density)
        guard value != self.cached else { self.lock.unlock(); return }
        self.cached = value
        UserDefaults.standard.set(["enabled": value.enabled, "inChats": value.inChats, "density": value.density], forKey: self.key)
        self.published = self.effectiveLocked(at: Date(), timeZone: .autoupdatingCurrent)
        self.lock.unlock()
        NotificationCenter.default.post(name: self.changedNotification, object: nil)
    }
}
