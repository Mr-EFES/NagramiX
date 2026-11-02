import Foundation
import Postbox

public func nagramiXCanCopyMessagesAsNew(_ messages: [EngineRawMessage], accountPeerId: EnginePeer.Id? = nil) -> Bool {
    return nagramiXCopyMessagesAsNew(messages, accountPeerId: accountPeerId) != nil
}

public func nagramiXAllowsOwnViewOnceDestination(_ peer: EnginePeer, accountPeerId: EnginePeer.Id, requiresPayment: Bool) -> Bool {
    guard case let .user(user) = peer else { return false }
    return user.id != accountPeerId && user.botInfo == nil && !requiresPayment
}

public func nagramiXCopyMessagesAsNew(_ messages: [EngineRawMessage], account: Account? = nil, hideCaptions: Bool = false, forceLocalMedia: Bool = false, accountPeerId: EnginePeer.Id? = nil) -> [EnqueueMessage]? {
    guard !messages.isEmpty else {
        return nil
    }
    let mediaBox = account?.postbox.mediaBox
    let archivedMediaCopy = mediaBox.map { NagramiXArchivedMediaCopy(mediaBox: $0) }
    var result: [EnqueueMessage] = []
    var copiedGroupingKeys: [Int64: Int64] = [:]
    for message in messages {
        let ownViewOnce = message.nagramiXAllowsOwnViewOnceCopy(accountPeerId: accountPeerId)
        guard message.nagramiXAllowsContentCopy || ownViewOnce else { return nil }
        if ownViewOnce, let mediaBox, !message.nagramiXHasLocalViewOnceRecording(mediaBox: mediaBox) {
            return nil
        }

        var attributes: [EngineMessage.Attribute] = []
        if ownViewOnce {
            // New one-shot lifetime; never reuse the original's countdown.
            attributes.append(AutoremoveTimeoutMessageAttribute(timeout: viewOnceTimeout, countdownBeginTime: nil))
        }
        var inlineStickers: [EngineMedia.Id: EngineRawMedia] = [:]
        if let entities = message.attributes.first(where: { $0 is TextEntitiesMessageAttribute }) as? TextEntitiesMessageAttribute {
            attributes.append(TextEntitiesMessageAttribute(entities: entities.entities))
            for mediaId in entities.associatedMediaIds {
                if let media = message.associatedMedia[mediaId] {
                    inlineStickers[mediaId] = media
                }
            }
        }
        if message.attributes.contains(where: { $0 is MediaSpoilerMessageAttribute }) {
            attributes.append(MediaSpoilerMessageAttribute())
        }

        var mediaReference: AnyMediaReference?
        for media in message.media {
            if media is TelegramMediaWebpage {
                continue
            } else if mediaReference == nil && (media is TelegramMediaImage || media is TelegramMediaFile || media is TelegramMediaContact || media is TelegramMediaMap) {
                if ownViewOnce || forceLocalMedia || message.isCopyProtected() || message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) {
                    if let archivedMediaCopy {
                        guard let copiedMedia = archivedMediaCopy.prepare(media) else {
                            return nil
                        }
                        mediaReference = .standalone(media: copiedMedia)
                    } else {
                        // Capability checks do not stage files or mutate the archive.
                        mediaReference = .standalone(media: media)
                    }
                } else {
                    mediaReference = .message(message: MessageReference(message), media: media)
                }
            } else {
                return nil
            }
        }
        if message.text.isEmpty && mediaReference == nil {
            return nil
        }

        var localGroupingKey: Int64?
        if let groupingKey = message.groupingKey {
            if let existing = copiedGroupingKeys[groupingKey] {
                localGroupingKey = existing
            } else {
                let generated = Int64.random(in: Int64.min ... Int64.max)
                copiedGroupingKeys[groupingKey] = generated
                localGroupingKey = generated
            }
        }
        let hidesCaption = hideCaptions && mediaReference != nil
        if hidesCaption {
            attributes.removeAll(where: { $0 is TextEntitiesMessageAttribute })
            inlineStickers = [:]
        }
        result.append(.message(text: hidesCaption ? "" : message.text, attributes: attributes, inlineStickers: inlineStickers, mediaReference: mediaReference, threadId: nil, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: localGroupingKey, correlationId: nil, bubbleUpEmojiOrStickersets: []))
    }
    archivedMediaCopy?.commit()
    return result
}

