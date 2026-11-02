import Foundation

// Telegram metadata — граница. Алгоритмы выбора media/фотопредставления production.
struct PixelDimensions { let width: Int32; let height: Int32 }
struct TelegramMediaImageRepresentation { let dimensions: PixelDimensions; let resource: String }
final class TelegramMediaImage {
    let representations: [TelegramMediaImageRepresentation]
    init(_ values: [TelegramMediaImageRepresentation]) { representations = values }
}
final class TelegramMediaFile {
    let resource: String
    let dimensions: PixelDimensions?
    let mimeType: String
    let fileName: String?
    let isVideo: Bool
    init(_ resource: String, _ w: Int32?, _ h: Int32?, mime: String = "video/mp4", name: String? = nil, video: Bool = true) {
        self.resource = resource; self.mimeType = mime; self.fileName = name; self.isVideo = video
        if let w, let h { dimensions = .init(width: w, height: h) } else { dimensions = nil }
    }
}
enum EngineMedia { case file(TelegramMediaFile), image(TelegramMediaImage), liveStream, unsupported }
struct EngineStoryItem { let media: EngineMedia; let alternativeMediaList: [EngineMedia] }
