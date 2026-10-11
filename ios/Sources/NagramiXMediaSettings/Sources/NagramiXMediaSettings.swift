import Foundation

public struct NagramiXMediaSettings: Equatable {
    public static let displayChangedNotification = Notification.Name("NagramiXMediaDisplaySettingsChanged")

    private enum Key {
        static let photoQuality = "nagramix.photos.quality"
        static let sendLargePhotos = "nagramix.photos.sendLarge"
        static let highQualityPhotos = "nagramix.photos.highQuality"
        static let legacyOriginalPhotos = "nagramix.photos.original"
        static let originalVideos = "nagramix.videos.original"
        static let stickerSize = "nagramix.stickers.size"
        static let showStickerTime = "nagramix.stickers.showTime"
    }

    public var photoQuality: Int
    // Legacy HD preference: retained for saved manual mode; no separate settings control.
    public var sendLargePhotos: Bool
    public var highQualityPhotos: Bool
    public var originalVideos: Bool
    public var stickerSize: Int
    public var showStickerTime: Bool

    public static let `default` = NagramiXMediaSettings(photoQuality: 100, sendLargePhotos: true, stickerSize: 100, showStickerTime: true)

    public init(photoQuality: Int, sendLargePhotos: Bool, stickerSize: Int, showStickerTime: Bool, highQualityPhotos: Bool = true, originalVideos: Bool = true) {
        self.photoQuality = Self.normalizedPercentage(photoQuality)
        self.sendLargePhotos = sendLargePhotos
        self.highQualityPhotos = highQualityPhotos
        self.originalVideos = originalVideos
        self.stickerSize = Self.normalizedPercentage(stickerSize)
        self.showStickerTime = showStickerTime
    }

    public static func normalizedPercentage(_ value: Int) -> Int {
        return min(100, max(0, value))
    }

    public var jpegQuality: Double {
        return Double(Self.normalizedPercentage(self.photoQuality)) / 100.0
    }

    public var stickerScale: Double {
        // Keep a nonzero drawable/font size at the slider's zero endpoint.
        return max(0.01, Double(Self.normalizedPercentage(self.stickerSize)) / 100.0)
    }

    public static var current: NagramiXMediaSettings {
        let defaults = UserDefaults.standard
        return NagramiXMediaSettings(
            photoQuality: defaults.object(forKey: Key.photoQuality) as? Int ?? Self.default.photoQuality,
            sendLargePhotos: defaults.object(forKey: Key.sendLargePhotos) as? Bool ?? Self.default.sendLargePhotos,
            stickerSize: defaults.object(forKey: Key.stickerSize) as? Int ?? Self.default.stickerSize,
            showStickerTime: defaults.object(forKey: Key.showStickerTime) as? Bool ?? Self.default.showStickerTime,
            highQualityPhotos: defaults.object(forKey: Key.highQualityPhotos) as? Bool ?? defaults.object(forKey: Key.legacyOriginalPhotos) as? Bool ?? Self.default.highQualityPhotos,
            originalVideos: defaults.object(forKey: Key.originalVideos) as? Bool ?? Self.default.originalVideos
        )
    }

    public static func update(_ value: NagramiXMediaSettings) {
        let previous = Self.current
        let defaults = UserDefaults.standard
        let size = Self.normalizedPercentage(value.stickerSize)
        defaults.set(Self.normalizedPercentage(value.photoQuality), forKey: Key.photoQuality)
        defaults.set(value.sendLargePhotos, forKey: Key.sendLargePhotos)
        defaults.set(value.highQualityPhotos, forKey: Key.highQualityPhotos)
        defaults.set(value.originalVideos, forKey: Key.originalVideos)
        defaults.set(size, forKey: Key.stickerSize)
        defaults.set(value.showStickerTime, forKey: Key.showStickerTime)
        if previous.stickerSize != size || previous.showStickerTime != value.showStickerTime {
            NotificationCenter.default.post(name: Self.displayChangedNotification, object: nil)
        }
    }
}
