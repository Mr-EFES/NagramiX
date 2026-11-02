import Foundation

@main struct SettingsTests {
    static func main() {
        let suite = UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        precondition(NagramiXRoundVideoSettings.read(from: defaults) == .init())
        precondition(NagramiXRoundVideoSettings.Quality.allCases.map { $0.bitRate } == [1_000_000,1_200_000,1_500_000])
        for quality in NagramiXRoundVideoSettings.Quality.allCases {
            for fps in NagramiXRoundVideoSettings.FrameRate.allCases {
                for codec in NagramiXRoundVideoSettings.Codec.allCases {
                    var value = NagramiXRoundVideoSettings(enabled: true, quality: quality, frameRate: fps, codec: codec, cinematic: true)
                    precondition(value.cinematic == (fps == .standard))
                    NagramiXRoundVideoSettings.update(value, in: defaults)
                    precondition(NagramiXRoundVideoSettings.read(from: defaults) == value)
                    value.cinematic = true
                    NagramiXRoundVideoSettings.update(value, in: defaults)
                    precondition(NagramiXRoundVideoSettings.read(from: defaults).cinematic == (fps == .standard))
                    precondition(captureBitRate(value) == quality.bitRate && exportRate([quality.rawValue, fps.rawValue,codec.rawValue]) == quality.bitRate)
                    precondition(value.resolved(supports60FPS: false, in: defaults).quality == quality)
                }
            }
        }
        // Старое сохранённое сочетание 60+Cinematic не включает эффект скрыто.
        defaults.set(60, forKey: "nagramix.roundVideo.quality.fps")
        defaults.set(true, forKey: "nagramix.roundVideo.quality.cinematic")
        let old = NagramiXRoundVideoSettings.read(from: defaults)
        precondition(old.frameRate == .smooth && !old.cinematic)
        precondition(captureBitRate(nil) == 1_200_000)
        print("PASS: 12 real capture/export bitrate presets, default OFF and persisted selections; Cinematic30 normalization, legacy60 flag, stock encoder fallback")
    }
}
