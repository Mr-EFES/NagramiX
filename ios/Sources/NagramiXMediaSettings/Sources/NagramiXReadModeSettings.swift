import Foundation

public enum NagramiXReadMode: String, CaseIterable {
    case standard, local

    public func setting(_ option: NagramiXReadMode, enabled: Bool) -> NagramiXReadMode {
        guard option == .local else { return self }
        return enabled ? .local : .standard
    }
}

// Compatibility accessors use the same privacy record as the other switches.
public enum NagramiXReadModeSettings {
    public static let changedNotification = NagramiXPrivacySettings.changedNotification

    public static func read(from defaults: UserDefaults) -> NagramiXReadMode {
        return NagramiXPrivacySettings.read(from: defaults).readMode
    }

    public static var current: NagramiXReadMode { self.read(from: .standard) }

    public static func set(_ option: NagramiXReadMode, enabled: Bool, in defaults: UserDefaults = .standard) {
        NagramiXPrivacySettings.update(in: defaults) { $0.readMode = $0.readMode.setting(option, enabled: enabled) }
    }
}
