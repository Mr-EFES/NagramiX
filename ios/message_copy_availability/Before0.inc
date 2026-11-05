import Foundation
import Postbox

public func nagramiXCanCopyMessagesAsNew(_ messages: [EngineRawMessage], accountPeerId: EnginePeer.Id? = nil) -> Bool {
    return nagramiXCopyMessagesAsNew(messages, accountPeerId: accountPeerId) != nil
}

public func nagramiXAllowsOwnViewOnceDestination(_ peer: EnginePeer, accountPeerId: EnginePeer.Id, requiresPayment: Bool) -> Bool {
    guard case let .user(user) = peer else { return false }
    return user.id != accountPeerId && user.botInfo == nil && !requiresPayment
}

public func nagramiXCopyMessagesAsNew(_ messages: [EngineRawMessage], account: Account? = nil, hideCaptions: Bool = false, forceLocalMedia: Bool = false, accountPeerId: EnginePeer.Id? = nil, mediaCopy: NagramiXArchivedMediaCopy? = nil) -> [EnqueueMessage]? {
    guard !messages.isEmpty else {
        return nil
    }
    let mediaBox = account?.postbox.mediaBox
    let archivedMediaCopy = mediaCopy ?? mediaBox.map { NagramiXArchivedMediaCopy(mediaBox: $0) }
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

        var copiedRichText: RichTextMessageAttribute?
        if let richText = message.attributes.first(where: { $0 is RichTextMessageAttribute }) as? RichTextMessageAttribute {
            let page = richText.fullInstantPage ?? richText.instantPage
            // A menu capability check may see a partial preview. Resolve its
            // full page before sending; never silently send the preview only.
            guard !page.blocks.isEmpty, account == nil || page.isComplete else { return nil }
            var copiedMedia: [MediaId: Media] = [:]
            for (id, media) in page.rawMedia {
                guard media is TelegramMediaImage || media is TelegramMediaFile else { return nil }
                if let archivedMediaCopy, forceLocalMedia || message.isCopyProtected() || message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) {
                    guard let localMedia = archivedMediaCopy.prepare(media) else { return nil }
                    // Blocks reference dictionary keys. Preserve those keys
                    // while replacing values with independent local resources.
                    copiedMedia[id] = localMedia
                } else {
                    copiedMedia[id] = media
                }
            }
            let copiedPage = InstantPage(blocks: page.blocks, rawMedia: copiedMedia, isComplete: page.isComplete, rtl: page.rtl, url: page.url, views: nil)
            let copiedAttribute = RichTextMessageAttribute(instantPage: copiedPage, fullInstantPage: nil)
            copiedRichText = copiedAttribute
            attributes.append(copiedAttribute)
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
        if message.text.isEmpty && mediaReference == nil && copiedRichText == nil {
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
    if mediaCopy == nil { archivedMediaCopy?.commit() }
    return result
}

/// All recipient payloads are prepared before the first enqueue. Each owns its
/// group IDs, local media identities and movable temporary files independently.
public final class NagramiXRecipientCopyBatch {
    public let recipientMessages: [[EnqueueMessage]]
    private let mediaCopies: [NagramiXArchivedMediaCopy]
    private var committed = false

    fileprivate init(messages: [[EnqueueMessage]], mediaCopies: [NagramiXArchivedMediaCopy]) {
        self.recipientMessages = messages
        self.mediaCopies = mediaCopies
    }

    /// Keep this batch uncommitted while payment/schedule/diversion can cancel.
    /// Releasing it before enqueue rolls back every recipient's staging files.
    public func commit() {
        guard !self.committed else { return }
        self.committed = true
        for copy in self.mediaCopies { copy.commit() }
    }

    public func messages(forRecipientAt index: Int, template: [EnqueueMessage]) -> [EnqueueMessage]? {
        guard self.recipientMessages.indices.contains(index),
              let count = self.recipientMessages.first?.count,
              template.count >= count else { return nil }
        var result = Array(template.prefix(template.count - count))
        for (copy, configured) in zip(self.recipientMessages[index], template.suffix(count)) {
            let sendAttributes = configured.attributes.filter { $0 is NotificationInfoMessageAttribute || $0 is OutgoingScheduleInfoMessageAttribute }
            result.append(copy.withUpdatedAttributes { attributes in
                attributes.filter { !($0 is NotificationInfoMessageAttribute) && !($0 is OutgoingScheduleInfoMessageAttribute) } + sendAttributes
            })
        }
        return result
    }
}

public func nagramiXPrepareRecipientCopies(_ messages: [EngineRawMessage], account: Account, recipientCount: Int, hideCaptions: Bool = false, forceLocalMedia: Bool = false, accountPeerId: EnginePeer.Id? = nil) -> NagramiXRecipientCopyBatch? {
    guard recipientCount > 0, !messages.isEmpty else { return nil }
    var batches: [[EnqueueMessage]] = []
    var mediaCopies: [NagramiXArchivedMediaCopy] = []
    for _ in 0 ..< recipientCount {
        let copy = NagramiXArchivedMediaCopy(mediaBox: account.postbox.mediaBox)
        guard let batch = nagramiXCopyMessagesAsNew(messages, account: account, hideCaptions: hideCaptions, forceLocalMedia: forceLocalMedia, accountPeerId: accountPeerId, mediaCopy: copy) else { return nil }
        batches.append(batch)
        mediaCopies.append(copy)
    }
    return NagramiXRecipientCopyBatch(messages: batches, mediaCopies: mediaCopies)
}

