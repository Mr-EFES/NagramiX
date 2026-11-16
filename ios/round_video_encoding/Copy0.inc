import Foundation
import CoreFoundation

/// Account-local snapshot. Never changes the four bitrate levels saved by the user.
public struct NagramiXRoundVideoEncodingPolicy {
    public static let fallbackMaximumSize: Int64 = 12 * 1024 * 1024
    public static let maximumDuration: Double = 60.0
    public static let maximumAttempts = 3
    public let maximumSize: Int64

    public init(encoding: [String: Any]?) {
        if let number = encoding?["max_size"] as? NSNumber,
           CFGetTypeID(number) != CFBooleanGetTypeID(),
           number.doubleValue.isFinite,
           number.doubleValue >= 1024.0, number.doubleValue <= 512.0 * 1024.0 * 1024.0 {
            self.maximumSize = Int64(number.doubleValue)
        } else {
            self.maximumSize = Self.fallbackMaximumSize
        }
    }

    public func videoBitRate(requested: Int, audioBitRate: Int = 64_000) -> Int? {
        guard requested > 0, audioBitRate >= 0 else { return nil }
        // Match GhostGram's full-minute budget: reserve10% for muxing/rate swings and subtract audio.
        let available = Double(self.maximumSize) * 8.0 * 0.9 / Self.maximumDuration - Double(audioBitRate)
        guard available.isFinite, available >= 64_000.0 else { return nil }
        return min(requested, Int(available))
    }

    public func contains(size: Int64) -> Bool {
        return size > 0 && size <= self.maximumSize
    }

    public func maximumEncodedSize(videoBitRate: Int, audioBitRate: Int = 64_000, duration: Double) -> Int64? {
        guard videoBitRate > 0, audioBitRate >= 0, duration.isFinite, duration > 0.0,
              duration <= Self.maximumDuration + 0.5 else { return nil }
        let bytes = (Double(videoBitRate) + Double(audioBitRate)) * duration / 8.0 * 1.1 + 64.0 * 1024.0
        guard bytes.isFinite, bytes > 0.0 else { return nil }
        return Int64(min(Double(self.maximumSize), bytes))
    }

    public func retryBitRate(current: Int, actualSize: Int64, maximumSize: Int64? = nil) -> Int? {
        let ceiling = min(self.maximumSize, maximumSize ?? self.maximumSize)
        guard current > 64_000, ceiling > 0, actualSize > ceiling else { return nil }
        let adjusted = Int(Double(current) * Double(ceiling) * 0.85 / Double(actualSize))
        let next = max(64_000, min(current - 1, adjusted))
        return next < current ? next : nil
    }
}
