import Foundation

@main struct PageBehaviorTests {
    static func main() {
        NagramiXRoundVideoSettings.update(.init(enabled: true))
        let page = PageHarness()
        let originalCells = page.table.cells
        let offset = page.table.contentOffset
        var count = 0
        for quality in NagramiXRoundVideoSettings.Quality.allCases {
            for fps in NagramiXRoundVideoSettings.FrameRate.allCases {
                for codec in NagramiXRoundVideoSettings.Codec.allCases {
                    let value = NagramiXRoundVideoSettings(enabled: true, quality: quality, frameRate: fps, codec: codec)
                    page.commit(value)
                    precondition(NagramiXRoundVideoSettings.current == value)
                    precondition(page.table.contentOffset == offset)
                    for path in page.table.paths {
                        precondition(page.table.cells[path] === originalCells[path])
                        precondition(page.table.cells[path]!.value == value)
                    }
                    count += 1
                }
            }
        }
        precondition(page.changedCount == count)
        let proposed = NagramiXRoundVideoSettings(enabled: true, quality: .maximum, frameRate: .smooth, codec: .hevc)
        // ON доступен на аппарате с Cinematic30, даже если сейчас выбраны60.
        page.cinematicModes = [640 * 100 + 30: true, 640 * 100 + 60: false]
        precondition(page.enabled(IndexPath(row: 0, section: 3), value: proposed))
        var cinematic = proposed; cinematic.cinematic = true; cinematic.frameRate = .standard
        precondition(!page.enabled(IndexPath(row: 1, section: 1), value: cinematic))
        precondition(page.enabled(IndexPath(row: 0, section: 1), value: cinematic))
        page.cinematicModes = [:]
        precondition(!page.enabled(IndexPath(row: 0, section: 3), value: proposed))
        precondition(page.enabled(IndexPath(row: 1, section: 3), value: proposed))
        var off = NagramiXRoundVideoSettings.current; off.enabled = false
        NagramiXRoundVideoSettings.update(off)
        page.commit(proposed)
        precondition(NagramiXRoundVideoSettings.current == off && page.changedCount == count)

        let host = SourceHost()
        var notes = 0
        for quality in NagramiXRoundVideoSettings.Quality.allCases {
            for fps in NagramiXRoundVideoSettings.FrameRate.allCases {
                for codec in NagramiXRoundVideoSettings.Codec.allCases {
                    host.node.nagramiXQuality = .init(enabled: true, quality: quality, frameRate: fps, codec: codec)
                    for duration in [10.0, 45.0, 45.1, 59.9, 60.0] {
                        let attributes = host.attributes(finalDuration: duration)
                        guard case let .Video(seconds, size, flags, preload, cover, declaredCodec) = attributes[1] else { fatalError() }
                        precondition(seconds == duration && size.width == quality.rawValue && size.height == quality.rawValue)
                        precondition(flags.contains(.instantRoundVideo))
                        precondition(declaredCodec == (codec == .hevc ? "h265" : "h264"))
                        let networkFlags = apiVideoFlags(videoFlags: flags, preloadSize: preload, coverTime: cover, videoCodec: declaredCodec)
                        precondition(networkFlags & 1 != 0 && networkFlags & (1 << 5) != 0)
                        notes += 1
                    }
                }
            }
        }
        print("PASS: \(count) actual page commits retain cells/offset, Cinematic30 selection with60 preset, saved OFF; \(notes) round/codec metadata and actual API flags at10–60sec; server/device pending")
    }
}
