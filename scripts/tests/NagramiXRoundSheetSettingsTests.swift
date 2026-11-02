import Foundation
@main struct RoundVideoSettingsTests {
    static func main() {
        let suite = "NagramiXRoundVideoTests-" + UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        precondition(NagramiXRoundVideoSettings.read(from: defaults) == .init())
        for quality in NagramiXRoundVideoSettings.Quality.allCases {
            for fps in NagramiXRoundVideoSettings.FrameRate.allCases {
                for codec in NagramiXRoundVideoSettings.Codec.allCases {
                    var value = NagramiXRoundVideoSettings(enabled: true, quality: quality, frameRate: fps, codec: codec)
                    NagramiXRoundVideoSettings.update(value, in: defaults)
                    precondition(NagramiXRoundVideoSettings.read(from: defaults) == value)
                    value.enabled = false
                    NagramiXRoundVideoSettings.update(value, in: defaults)
                    precondition(NagramiXRoundVideoSettings.read(from: defaults) == value)
                }
            }
        }
        for quality in NagramiXRoundVideoSettings.Quality.allCases {
            for codec in NagramiXRoundVideoSettings.Codec.allCases {
                let requested = NagramiXRoundVideoSettings(enabled: true, quality: quality, frameRate: .smooth, codec: codec)
                NagramiXRoundVideoSettings.update(requested, in: defaults)
                precondition(requested.resolved(supports60FPS: true, in: defaults) == requested)
                precondition(NagramiXRoundVideoSettings.read(from: defaults) == requested)
                let actual = requested.resolved(supports60FPS: false, in: defaults)
                precondition(actual.frameRate == .standard && actual.quality == quality && actual.codec == codec && actual.enabled)
                precondition(actual.quality.bitRate == requested.quality.bitRate)
                precondition(NagramiXRoundVideoSettings.read(from: defaults) == actual)
                // A stale capability check may not undo a later user edit.
                NagramiXRoundVideoSettings.update(.init(), in: defaults)
                _ = requested.resolved(supports60FPS: false, in: defaults)
                precondition(NagramiXRoundVideoSettings.read(from: defaults) == .init())
            }
        }
        let disabled = NagramiXRoundVideoSettings(enabled: false, quality: .maximum, frameRate: .smooth, codec: .hevc)
        NagramiXRoundVideoSettings.update(disabled, in: defaults)
        precondition(disabled.resolved(supports60FPS: false, in: defaults) == disabled)
        defaults.set(999, forKey: "nagramix.roundVideo.quality.resolution")
        defaults.set(true, forKey: "nagramix.roundVideo.quality.enabled")
        precondition(!NagramiXRoundVideoSettings.read(from: defaults).enabled)
        precondition(NagramiXRoundVideoSettings.Quality.allCases.map { $0.bitRate } == [1_500_000, 1_700_000, 2_000_000])
        print("PASS: round video defaults, 12 combinations, saved OFF, 60-to-30 fallback, quality/codec preserved, stale callback, invalid configuration")
    }
}
