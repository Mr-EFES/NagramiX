import TelegramCore

// Основное media — штатный HQ-источник истории. Настройки плеера и наличие
// уменьшенной копии в кэше не должны менять источник для сохранения.
func nagramiXBestStoryMediaForSaving(_ item: EngineStoryItem) -> EngineMedia {
    guard case let .file(original) = item.media,
          original.isVideo || original.mimeType.hasPrefix("video/"),
          let dimensions = original.dimensions, dimensions.width > 0, dimensions.height > 0 else {
        return item.media
    }
    var best = original
    var bestPixels = Int64(dimensions.width) * Int64(dimensions.height)
    // При равном разрешении оставляем основной вариант: размер файла сам по
    // себе не определяет качество при разных кодеках. Не экспортируем HLS-плейлист.
    for media in item.alternativeMediaList {
        guard case let .file(candidate) = media,
              candidate.isVideo || candidate.mimeType.hasPrefix("video/"),
              let size = candidate.dimensions, size.width > 0, size.height > 0 else { continue }
        let mime = candidate.mimeType.lowercased()
        guard mime != "application/x-mpegurl", mime != "application/vnd.apple.mpegurl",
              candidate.fileName?.lowercased().hasSuffix(".m3u8") != true else { continue }
        let pixels = Int64(size.width) * Int64(size.height)
        if pixels > bestPixels {
            best = candidate
            bestPixels = pixels
        }
    }
    return .file(best)
}
