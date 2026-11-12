import Foundation

public enum NagramiXTypingPreset: Int, CaseIterable {
    case pulse, wave, panelWave, neon, shake, custom

    public var localizationKey: String {
        return "NagramiX.InputEffects.Preset." + ["Pulse", "Wave", "PanelWave", "Neon", "Shake", "Custom"][self.rawValue]
    }
}

public enum NagramiXTypingParameter: Int, CaseIterable {
    case intensity, speed, scale, offset, glow

    public var localizationKey: String {
        return "NagramiX.InputEffects." + ["Intensity", "Speed", "Scale", "Offset", "Glow"][self.rawValue]
    }
}

public struct NagramiXTypingConfiguration: Equatable {
    public var enabled: Bool = false
    public var preset: NagramiXTypingPreset = .wave
    public var intensity: Double = 55.0
    public var speed: Double = 55.0
    public var scale: Double = 45.0
    public var offset: Double = 45.0
    public var glow: Double = 55.0

    public init() {}

    public subscript(parameter: NagramiXTypingParameter) -> Double {
        get {
            switch parameter {
            case .intensity: return self.intensity
            case .speed: return self.speed
            case .scale: return self.scale
            case .offset: return self.offset
            case .glow: return self.glow
            }
        }
        set {
            let value = newValue.isFinite ? min(100.0, max(0.0, newValue)) : NagramiXTypingConfiguration()[parameter]
            switch parameter {
            case .intensity: self.intensity = value
            case .speed: self.speed = value
            case .scale: self.scale = value
            case .offset: self.offset = value
            case .glow: self.glow = value
            }
        }
    }

    public var duration: Double { return 0.45 - 0.003 * self.speed }
    public var minimumInterval: Double { return max(0.12, self.duration * 0.6) }
}

// Independent storage keeps aggregate tab-settings writes from resetting the effect.
public enum NagramiXTypingSettings {
    public static let changedNotification = Notification.Name("NagramiXTypingSettingsChanged")
    private static let key = "nagramix.input.typingEffects"
    private static let lock = NSLock()
    private static var cached = read(in: .standard)

    public static func read(in defaults: UserDefaults) -> NagramiXTypingConfiguration {
        let stored = defaults.dictionary(forKey: self.key) ?? [:]
        var value = NagramiXTypingConfiguration()
        value.enabled = stored["enabled"] as? Bool ?? false
        value.preset = (stored["preset"] as? Int).flatMap(NagramiXTypingPreset.init(rawValue:)) ?? .wave
        for parameter in NagramiXTypingParameter.allCases {
            value[parameter] = stored[String(parameter.rawValue)] as? Double ?? value[parameter]
        }
        return value
    }

    public static var current: NagramiXTypingConfiguration {
        self.lock.lock()
        defer { self.lock.unlock() }
        return self.cached
    }

    public static func update(_ transform: (inout NagramiXTypingConfiguration) -> Void) {
        self.lock.lock()
        var value = self.cached
        transform(&value)
        for parameter in NagramiXTypingParameter.allCases { value[parameter] = value[parameter] }
        guard value != self.cached else { self.lock.unlock(); return }
        self.cached = value
        var stored: [String: Any] = ["enabled": value.enabled, "preset": value.preset.rawValue]
        for parameter in NagramiXTypingParameter.allCases { stored[String(parameter.rawValue)] = value[parameter] }
        UserDefaults.standard.set(stored, forKey: self.key)
        self.lock.unlock()
        NotificationCenter.default.post(name: self.changedNotification, object: nil)
    }
}
