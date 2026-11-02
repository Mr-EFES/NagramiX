@main struct RoundBitRateTests {
    static func main() throws {
        var checks = 0
        func check(_ condition: @autoclosure () -> Bool, _ message: String) {
            checks += 1
            if !condition() { FileHandle.standardError.write(Data(("FAIL: " + message + "\n").utf8)); exit(1) }
        }
        let defaults = UserDefaults.standard
        let prefix = "nagramix.roundVideo.quality."
        defaults.removePersistentDomain(forName: Bundle.main.bundleIdentifier ?? "unused")
        for key in ["resolution", "fps", "codec", "cinematic", "bitrate", "enabled"] { defaults.removeObject(forKey: prefix + key) }
        check(!NagramiXRoundVideoSettings.current.enabled && NagramiXRoundVideoSettings.current.bitRate == 1_000_000, "fresh install remains OFF with 1 Mbps")
        for quality in NagramiXRoundVideoSettings.Quality.allCases {
            defaults.set(quality.rawValue, forKey: prefix + "resolution")
            defaults.removeObject(forKey: prefix + "bitrate")
            check(NagramiXRoundVideoSettings.current.bitRate == quality.bitRate, "missing bitrate preserves old quality rate")
        }
        for (input, expected) in [(Int.min, 1_000_000), (Int.max, 2_000_000), (1_149_999, 1_100_000), (1_150_000, 1_200_000), (2_000_001, 2_000_000)] {
            var value = NagramiXRoundVideoSettings(bitRate: input)
            check(value.bitRate == expected, "safe initial bitrate normalization")
            value.bitRate = input
            check(value.bitRate == expected, "safe subsequent bitrate normalization")
        }
        var combinations = 0
        for quality in NagramiXRoundVideoSettings.Quality.allCases {
            for fps in NagramiXRoundVideoSettings.FrameRate.allCases {
                for codec in NagramiXRoundVideoSettings.Codec.allCases {
                    for step in 0...10 {
                        let rate = 1_000_000 + step * 100_000
                        let value = NagramiXRoundVideoSettings(enabled: true, quality: quality, frameRate: fps, codec: codec, bitRate: rate)
                        NagramiXRoundVideoSettings.update(value)
                        check(NagramiXRoundVideoSettings.current == value, "all 11 steps persist with quality/FPS/codec")
                        let capture = CaptureHarness(value); capture.configure()
                        check(!capture.failed && capture.writer.input != nil, "selected capture settings reach writer")
                        let settings = capture.writer.input!.outputSettings
                        let compression = settings[AVVideoCompressionPropertiesKey] as! [String: Any]
                        check(compression[AVVideoAverageBitRateKey] as? Int == rate, "capture must use chosen independent bitrate")
                        check(settings[AVVideoCodecKey] as? AVVideoCodecType == (codec == .h264 ? .h264 : .hevc), "writer must use selected actual codec")
                        check(settings[AVVideoWidthKey] as? Int == quality.rawValue && settings[AVVideoHeightKey] as? Int == quality.rawValue, "capture resolution preserved")
                        check(compression[AVVideoProfileLevelKey] as? String == (codec == .h264 ? AVVideoProfileLevelH264HighAutoLevel : kVTProfileLevel_HEVC_Main_AutoLevel), "codec profile agrees with encoder")
                        check((compression[AVVideoH264EntropyModeKey] != nil) == (codec == .h264), "no H264 entropy settings for HEVC")
                        let snapshot = SnapshotSource(node: .init(nagramiXQuality: value)).tuning()!
                        check(snapshot == [quality.rawValue, fps.rawValue, codec.rawValue, rate], "recording snapshots the chosen bitrate")
                        let encoded = try JSONEncoder().encode(TuningEnvelope(snapshot))
                        let decoded = try JSONDecoder().decode(TuningEnvelope.self, from: encoded).nagramiXRoundTuning
                        check(decoded == snapshot, "deferred resource JSON retains 4-value snapshot")
                        // Changing live settings must not alter this recording's export.
                        NagramiXRoundVideoSettings.update(.init(enabled: false, quality: .standard, codec: codec == .hevc ? .h264 : .hevc, bitRate: 2_000_000))
                        let exported = export(.init(qualityPreset: .videoMessage, nagramiXRoundTuning: decoded))
                        check(exported != nil, "deferred/trim export accepts four-field recording snapshot")
                        let configuration = exported!
                        let properties = configuration.videoSettings[AVVideoCompressionPropertiesKey] as! [String: Any]
                        check(properties[AVVideoAverageBitRateKey] as? Int == rate, "deferred/trim export must retain this recording's bitrate")
                        check(configuration.videoSettings[AVVideoCodecKey] as? AVVideoCodecType == (codec == .h264 ? .h264 : .hevc), "deferred/trim export must retain this recording's codec")
                        check(configuration.frameRate == Float(fps.rawValue), "deferred FPS preserved")
                        let writerSettings = exportWriterSettings(configuration: configuration, preferredTransform: nil, sourceFrameRate: Float(fps.rawValue))
                        check(writerSettings[AVVideoCodecKey] as? AVVideoCodecType == (codec == .h264 ? .h264 : .hevc), "final native export writer preserves encoder codec")
                        check((writerSettings[AVVideoCompressionPropertiesKey] as! [String: Any])[AVVideoAverageBitRateKey] as? Int == rate, "final native export writer preserves bitrate")
                        combinations += 1
                    }
                    let legacy = [quality.rawValue, fps.rawValue, codec.rawValue]
                    let decoded = try JSONDecoder().decode(TuningEnvelope.self, from: JSONEncoder().encode(TuningEnvelope(legacy))).nagramiXRoundTuning
                    let config = export(.init(qualityPreset: .videoMessage, nagramiXRoundTuning: decoded))!
                    check((config.videoSettings[AVVideoCompressionPropertiesKey] as! [String: Any])[AVVideoAverageBitRateKey] as? Int == quality.bitRate, "legacy 3-field pending resources remain compatible")
                }
            }
        }
        for bad in [[], [480], [480,30], [999,30,0,1_000_000], [480,0,0,1_000_000], [480,30,9,1_000_000],
                    [480,30,0,999_999], [480,30,0,2_000_001], [480,30,0,1_150_000], [480,30,0,1_000_000,0]] {
            check(export(.init(qualityPreset: .videoMessage, nagramiXRoundTuning: bad)) == nil, "invalid snapshot must leave stock export")
        }
        check(export(.init(qualityPreset: .story, nagramiXRoundTuning: [640,60,1,2_000_000])) == nil, "stories do not use round tuning")
        check(export(.init(qualityPreset: .videoMessage, nagramiXRoundTuning: nil)) == nil, "master OFF recording retains native export")
        check(SnapshotSource(node: .init(nagramiXQuality: nil)).tuning() == nil, "OFF recording has no override snapshot")
        let stock = CaptureHarness(nil); stock.configure()
        check(stock.writer.probed[AVVideoCodecKey] as? AVVideoCodecType == .h264, "stock capture codec unchanged")
        check((stock.writer.probed[AVVideoCompressionPropertiesKey] as! [String: Any])[AVVideoAverageBitRateKey] as? Int == 1_200_000, "stock capture rate unchanged")
        let unsupported = CaptureHarness(.init(enabled: true, codec: .hevc, bitRate: 1_700_000))
        unsupported.writer.applies = false; unsupported.configure()
        check(unsupported.failed && unsupported.writer.input == nil, "unsupported HEVC fails instead of silently recording H264")
        let selected = NagramiXRoundVideoSettings(enabled: true, quality: .maximum, frameRate: .smooth, codec: .hevc, bitRate: 1_900_000)
        NagramiXRoundVideoSettings.update(selected)
        let fallback = selected.resolved(supports60FPS: false)
        check(fallback.frameRate == .standard && fallback.bitRate == selected.bitRate && fallback.codec == selected.codec && fallback.quality == selected.quality,
              "FPS fallback preserves bitrate, quality and codec")
        NagramiXRoundVideoSettings.update(selected)
        var newer = selected; newer.bitRate = 1_800_000
        NagramiXRoundVideoSettings.update(newer)
        _ = selected.resolved(supports60FPS: false)
        check(NagramiXRoundVideoSettings.current == newer, "stale camera fallback must not overwrite a newer bitrate selection")
        print("PASS: \(checks) model/capture/snapshot/JSON/deferred/export/codec checks across \(combinations) recording configurations")
    }
}
