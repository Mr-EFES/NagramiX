import Foundation
import Postbox

// Локальная ссылка нужна только загрузчику байтов; в Telegram API не передаётся.
public final class NagramiXAnonymousStickerMessageAttribute: MessageAttribute {
    public let source: TelegramMediaFile?

    public init(source: TelegramMediaFile) {
        self.source = source
    }

    public required init(decoder: PostboxDecoder) {
        self.source = decoder.decodeObjectForKey("f", decoder: { TelegramMediaFile(decoder: $0) }) as? TelegramMediaFile
    }

    public func encode(_ encoder: PostboxEncoder) {
        if let source = self.source { encoder.encodeObject(source, forKey: "f") }
    }
}

func nagramiXAnonymousStickerAttributes(_ attributes: [TelegramMediaFileAttribute]) -> [TelegramMediaFileAttribute] {
    return attributes.map { attribute in
        if case let .Sticker(text, _, mask) = attribute {
            return .Sticker(displayText: text, packReference: nil, maskData: mask)
        }
        return attribute
    }
}

func nagramiXAnonymousStickerMessage(_ message: EnqueueMessage, enabled: Bool) -> EnqueueMessage {
    guard enabled,
          case let .message(text, attributes, inlineStickers, reference, threadId, replyToMessageId, replyToStoryId, grouping, correlation, bubbleUp) = message,
          !attributes.contains(where: { $0 is NagramiXAnonymousStickerMessageAttribute || $0 is EphemeralOutgoingMessageAttribute || $0 is RichTextMessageAttribute }),
          replyToMessageId?.messageId.namespace != Namespaces.Message.EphemeralLocal,
          let file = reference?.media as? TelegramMediaFile, file.isSticker, !file.isCustomEmoji else { return message }
    // Новый MediaId не даёт ответу upload перезаписать общий файл стикерпака.
    let copy = TelegramMediaFile(fileId: MediaId(namespace: Namespaces.Media.LocalFile, id: Int64.random(in: 1 ... Int64.max)), partialReference: nil, resource: file.resource, previewRepresentations: file.previewRepresentations, videoThumbnails: file.videoThumbnails, videoCover: file.videoCover, immediateThumbnailData: file.immediateThumbnailData, mimeType: file.mimeType, size: file.size, attributes: nagramiXAnonymousStickerAttributes(file.attributes), alternativeRepresentations: [])
    var updated = attributes.filter { !($0 is InlineBotMessageAttribute) && !($0 is OutgoingChatContextResultMessageAttribute) }
    updated.append(NagramiXAnonymousStickerMessageAttribute(source: file.withUpdatedPartialReference(reference?.partial ?? file.partialReference)))
    return .message(text: text, attributes: updated, inlineStickers: inlineStickers, mediaReference: .standalone(media: copy), threadId: threadId, replyToMessageId: replyToMessageId, replyToStoryId: replyToStoryId, localGroupingKey: grouping, correlationId: correlation, bubbleUpEmojiOrStickersets: bubbleUp)
}
