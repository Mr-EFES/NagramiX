import Foundation

public enum NagramiXDownloadAcceleration: Int, CaseIterable, Equatable {
    case standard = 0
    case medium = 1
    case maximum = 2
}

public struct NagramiXDownloadTuning: Equatable {
    public let parallelParts: Int
    public let partSize: Int64
    public let workersPerTarget: Int
}

// Keep network preferences in the existing Foundation-only module. Importing
// NagramiXCore from TelegramCore would create a presentation dependency cycle.
public struct NagramiXDownloadSettings: Equatable {
    private enum Key {
        static let enabled = "nagramix.downloads.accelerationEnabled"
        static let mode = "nagramix.downloads.accelerationMode"
    }

    public var enabled: Bool
    public var mode: NagramiXDownloadAcceleration

    public static let `default` = NagramiXDownloadSettings(enabled: false, mode: .medium)

    public init(enabled: Bool, mode: NagramiXDownloadAcceleration) {
        self.enabled = enabled
        self.mode = mode
    }

    public var tuning: NagramiXDownloadTuning? {
        guard self.enabled else {
            return nil
        }
        switch self.mode {
        case .standard:
            return nil
        case .medium:
            return NagramiXDownloadTuning(parallelParts: 12, partSize: 1024 * 1024, workersPerTarget: 6)
        case .maximum:
            return NagramiXDownloadTuning(parallelParts: 24, partSize: 1024 * 1024, workersPerTarget: 8)
        }
    }

    public static var current: NagramiXDownloadSettings {
        let defaults = UserDefaults.standard
        let mode: NagramiXDownloadAcceleration
        if let storedMode = defaults.object(forKey: Key.mode) {
            // Unknown persisted modes must fall back to native limits.
            mode = (storedMode as? Int).flatMap(NagramiXDownloadAcceleration.init(rawValue:)) ?? .standard
        } else {
            mode = Self.default.mode
        }
        return NagramiXDownloadSettings(
            enabled: defaults.object(forKey: Key.enabled) as? Bool ?? Self.default.enabled,
            mode: mode
        )
    }

    public static func update(_ value: NagramiXDownloadSettings) {
        let defaults = UserDefaults.standard
        defaults.set(value.mode.rawValue, forKey: Key.mode)
        defaults.set(value.enabled, forKey: Key.enabled)
    }
}
