import Foundation

public struct NagramiXRoundVideoSettings: Equatable {
    public enum Quality: Int, CaseIterable {
        case standard = 480
        case high = 512
        case maximum = 640

        public var bitRate: Int {
            switch self {
            case .standard: return 1_500_000
            case .high: return 1_700_000
            case .maximum: return 2_000_000
            }
        }
    }
    public enum FrameRate: Int, CaseIterable {
        case standard = 30
        case smooth = 60
    }
    public enum Codec: Int, CaseIterable {
        case h264 = 0
        case hevc = 1
    }

    public var enabled: Bool
    public var quality: Quality
    public var frameRate: FrameRate
    public var cinematic: Bool
    public var codec: Codec

    public init(enabled: Bool = false, quality: Quality = .standard,
                frameRate: FrameRate = .standard, codec: Codec = .h264, cinematic: Bool = false) {
        self.cinematic = cinematic
        self.enabled = enabled
        self.quality = quality
        self.frameRate = frameRate
        self.codec = codec
    }

    private static let prefix = "nagramix.roundVideo.quality."
    public static var current: Self { return self.read(from: .standard) }

    public static func read(from defaults: UserDefaults) -> Self {
        let quality = Quality(rawValue: defaults.integer(forKey: self.prefix + "resolution"))
        let fps = FrameRate(rawValue: defaults.integer(forKey: self.prefix + "fps"))
        let codec = Codec(rawValue: defaults.integer(forKey: self.prefix + "codec"))
        // Unknown values must not activate an unsupported encoder configuration.
        let valid = ["resolution", "fps", "codec"].allSatisfy { suffix in
            guard defaults.object(forKey: self.prefix + suffix) != nil else { return true }
            switch suffix {
            case "resolution": return quality != nil
            case "fps": return fps != nil
            default: return codec != nil
            }
        }
        return Self(enabled: valid && (defaults.object(forKey: self.prefix + "enabled") as? Bool ?? false),
                    quality: quality ?? .standard, frameRate: fps ?? .standard, codec: codec ?? .h264, cinematic: defaults.bool(forKey: self.prefix + "cinematic"))
    }

    /// Resolve the requested capture mode after checking a real device format.
    /// A failed 60 FPS capability check changes only FPS, never the quality tier.
    /// Do not overwrite a newer user selection with a late camera callback.
    public func resolved(supports60FPS: Bool, in defaults: UserDefaults = .standard) -> Self {
        guard self.enabled, self.frameRate == .smooth, !supports60FPS else { return self }
        var result = self
        result.frameRate = .standard
        if Self.read(from: defaults) == self {
            Self.update(result, in: defaults)
            NotificationCenter.default.post(name: Self.changedNotification, object: nil)
        }
        return result
    }

    public static let changedNotification = Notification.Name("NagramiXRoundVideoQualityChanged")

    public static func update(_ value: Self, in defaults: UserDefaults = .standard) {
        defaults.set(value.cinematic, forKey: self.prefix + "cinematic")
        defaults.set(value.quality.rawValue, forKey: self.prefix + "resolution")
        defaults.set(value.frameRate.rawValue, forKey: self.prefix + "fps")
        defaults.set(value.codec.rawValue, forKey: self.prefix + "codec")
        defaults.set(value.enabled, forKey: self.prefix + "enabled")
    }
}
