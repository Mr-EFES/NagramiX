import Foundation

public enum NagramiXGalleryVideoSaveError: Error {
    case download
    case conversion
    case permissionDenied
    case library
}

public enum NagramiXVideoSavePolicy {
    public static func codecPriority(_ codec: String?) -> Int? {
        switch codec?.lowercased() {
        case "h264", "avc", "avc1": return 0
        case "h265", "hevc", "hvc1", "hev1": return 1
        default: return nil
        }
    }

    /// Quality is the shorter displayed edge, for portrait and landscape alike.
    /// Keep the source aspect, even encoder dimensions, and never upscale.
    public static func targetSize(width: Double, height: Double, quality: Int) -> (width: Int, height: Int)? {
        guard width.isFinite, height.isFinite, width >= 2, height >= 2,
              width <= 32768, height <= 32768, quality >= 2, quality <= 32768 else { return nil }
        let scale = min(1.0, Double(quality) / min(width, height))
        let targetWidth = Int(floor(width * scale / 2.0)) * 2
        let targetHeight = Int(floor(height * scale / 2.0)) * 2
        guard targetWidth >= 2, targetHeight >= 2 else { return nil }
        return (targetWidth, targetHeight)
    }

    public static func mayRetryFromOriginal(_ error: NagramiXGalleryVideoSaveError) -> Bool {
        switch error {
        case .download, .conversion: return true
        case .permissionDenied, .library: return false
        }
    }
}
