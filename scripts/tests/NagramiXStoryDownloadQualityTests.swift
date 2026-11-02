import Foundation

@main struct StoryDownloadQualityTests {
    static func main() {
        func file(_ media: EngineMedia) -> TelegramMediaFile {
            guard case let .file(result) = media else { fatalError("expected file") }; return result
        }
        let original = TelegramMediaFile("original", 1080, 1920)
        let low = TelegramMediaFile("cached-low", 360, 640)
        let medium = TelegramMediaFile("medium", 720, 1280)
        let hq = TelegramMediaFile("higher", 2160, 3840)
        let hls = TelegramMediaFile("playlist", 4096, 8192, mime: "application/x-mpegurl")
        let namedHls = TelegramMediaFile("named-playlist", 4096, 8192, name: "STORY.M3U8")
        let audio = TelegramMediaFile("audio", 8192, 8192, mime: "audio/ogg", video: false)
        let malformed = TelegramMediaFile("invalid", -8192, -8192)
        let unknown = TelegramMediaFile("unknown", nil, nil)
        let same = TelegramMediaFile("same-resolution-other-codec", 1080, 1920, mime: "video/hevc")
        let variants: [[EngineMedia]] = [[], [.file(low)], [.file(low), .file(medium)], [.file(medium), .file(low)],
            [.file(same)], [.file(hls), .file(namedHls), .file(audio), .file(malformed), .file(unknown)], [.unsupported, .liveStream]]
        var cases = 0
        for alternatives in variants {
            let saved = nagramiXBestStoryMediaForSaving(.init(media: .file(original), alternativeMediaList: alternatives))
            precondition(file(saved) === original, "low/cached/playlist/invalid variant replaced original")
            cases += 1
        }
        for alternatives in [[EngineMedia.file(hq), .file(low)], [.file(low), .file(hq)], [.file(hls), .file(hq)]] {
            precondition(file(nagramiXBestStoryMediaForSaving(.init(media: .file(original), alternativeMediaList: alternatives))) === hq)
            cases += 1
        }
        // Если основной документ не описывает размеры, сохраняем штатный HQ,
        // вместо догадки о качестве по размеру файла/низкой альтернативе.
        precondition(file(nagramiXBestStoryMediaForSaving(.init(media: .file(unknown), alternativeMediaList: [.file(low)]))) === unknown)
        let zero = TelegramMediaFile("zero", 0, 1920)
        precondition(file(nagramiXBestStoryMediaForSaving(.init(media: .file(zero), alternativeMediaList: [.file(low)]))) === zero)
        let max = TelegramMediaFile("max-dimensions", Int32.max, Int32.max)
        precondition(file(nagramiXBestStoryMediaForSaving(.init(media: .file(original), alternativeMediaList: [.file(max)]))) === max)
        let image = TelegramMediaImage([
            .init(dimensions: .init(width: 360, height: 640), resource: "preview"),
            .init(dimensions: .init(width: 1080, height: 1920), resource: "full-photo"),
            .init(dimensions: .init(width: 720, height: 1280), resource: "middle")])
        guard case let .image(savedImage) = nagramiXBestStoryMediaForSaving(.init(media: .image(image), alternativeMediaList: [.file(hq)])) else { fatalError() }
        precondition(savedImage === image && largestImageRepresentation(savedImage.representations)?.resource == "full-photo")
        guard case .liveStream = nagramiXBestStoryMediaForSaving(.init(media: .liveStream, alternativeMediaList: [.file(hq)])) else { fatalError() }
        guard case .unsupported = nagramiXBestStoryMediaForSaving(.init(media: .unsupported, alternativeMediaList: [.file(hq)])) else { fatalError() }
        precondition(largestImageRepresentation([]) == nil)
        print("PASS: \(cases + 7) production quality/photo choices: original HQ, lower/cached/tied alternatives, higher resolution, HLS/type/metadata exclusions, Int32 bounds; no re-encoding; server/Photos pending")
    }
}
