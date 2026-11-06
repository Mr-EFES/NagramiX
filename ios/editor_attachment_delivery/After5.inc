import Foundation
import Postbox
internal import TelegramApi

public func nagramiXCanCopyMessagesAsNew(_ messages: [EngineRawMessage], accountPeerId: EnginePeer.Id? = nil) -> Bool {
    return nagramiXCopyMessagesAsNew(messages, accountPeerId: accountPeerId) != nil
}

public func nagramiXAllowsOwnViewOnceDestination(_ peer: EnginePeer, accountPeerId: EnginePeer.Id, requiresPayment: Bool) -> Bool {
    guard case let .user(user) = peer else { return false }
    return user.id != accountPeerId && user.botInfo == nil && !requiresPayment
}

private func nagramiXCopyPollAsNew(_ poll: TelegramMediaPoll) -> TelegramMediaPoll? {
    // New polls have their own identity and votes. Never invent a quiz answer.
    var correctAnswers = poll.correctAnswers
    if case .quiz = poll.kind {
        if correctAnswers?.isEmpty != false {
            correctAnswers = poll.results.voters?.filter { $0.isCorrect }.map { $0.opaqueIdentifier }
        }
        guard let answers = correctAnswers, !answers.isEmpty,
              Set(answers).isSubset(of: Set(poll.options.map { $0.opaqueIdentifier })) else { return nil }
    }
    // The native poll sender accepts cloud attachments, not staged local files.
    // Check every slot so it can never silently omit part of a copied poll.
    let attachments = [poll.attachedMedia, poll.results.solution?.media] + poll.options.map { $0.media }
    guard attachments.compactMap({ $0 }).allSatisfy({ pollCloudMediaToInputMedia($0) != nil }) else { return nil }
    let options = poll.options.map {
        TelegramMediaPollOption(text: $0.text, entities: $0.entities, opaqueIdentifier: $0.opaqueIdentifier, media: $0.media, date: nil, addedBy: nil)
    }
    let results = TelegramMediaPollResults(voters: nil, totalVoters: nil, recentVoters: [], solution: poll.results.solution, hasUnseenVotes: nil, canViewStats: false)
    return TelegramMediaPoll(pollId: MediaId(namespace: Namespaces.Media.LocalPoll, id: Int64.random(in: 1 ... Int64.max)), publicity: poll.publicity, kind: poll.kind, text: poll.text, textEntities: poll.textEntities, options: options, correctAnswers: correctAnswers, results: results, isClosed: false, deadlineTimeout: nil, deadlineDate: nil, pollHash: 0, openAnswers: poll.openAnswers, revotingDisabled: poll.revotingDisabled, shuffleAnswers: poll.shuffleAnswers, hideResultsUntilClose: poll.hideResultsUntilClose, isCreator: true, attachedMedia: poll.attachedMedia, restrictToSubscribers: poll.restrictToSubscribers, countries: poll.countries)
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
        let sourceWebpage = message.media.first(where: { $0 is TelegramMediaWebpage }) as? TelegramMediaWebpage
        // Copy the post's explicit preview choice. A bare text link must stay a bare text link.
        if sourceWebpage == nil {
            attributes.append(OutgoingContentInfoMessageAttribute(flags: [.disableLinkPreviews]))
        } else {
            attributes.append(contentsOf: message.attributes.filter { $0 is WebpagePreviewMessageAttribute || $0 is InvertMediaMessageAttribute })
        }
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
            } else if let poll = media as? TelegramMediaPoll, mediaReference == nil {
                guard let copy = nagramiXCopyPollAsNew(poll) else { return nil }
                mediaReference = .standalone(media: copy)
            } else if mediaReference == nil && (media is TelegramMediaImage || media is TelegramMediaFile || media is TelegramMediaContact || media is TelegramMediaMap) {
                if ownViewOnce || nagramiXCanUseTemporaryMediaActions(message) || forceLocalMedia || message.isCopyProtected() || message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) {
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
        if mediaReference == nil, let sourceWebpage {
            mediaReference = .standalone(media: sourceWebpage)
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
        let hidesCaption = hideCaptions && mediaReference != nil && !(mediaReference?.media is TelegramMediaWebpage)
        if hidesCaption {
            attributes.removeAll(where: { $0 is TextEntitiesMessageAttribute })
            inlineStickers = [:]
        }
        let separateRoundCaption = nagramiXCanUseTemporaryMediaActions(message)
            && (message.media.first as? TelegramMediaFile)?.isInstantVideo == true
            && !hidesCaption && !message.text.isEmpty
        // Round-video bubbles do not render captions. Keep an authored repost's
        // signature as a neighbouring text message rather than invisible text.
        if separateRoundCaption {
            result.append(.message(text: message.text, attributes: attributes.filter { $0 is TextEntitiesMessageAttribute }, inlineStickers: inlineStickers, mediaReference: nil, threadId: nil, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: nil, correlationId: nil, bubbleUpEmojiOrStickersets: []))
            attributes.removeAll(where: { $0 is TextEntitiesMessageAttribute })
            inlineStickers = [:]
        }
        result.append(.message(text: hidesCaption || separateRoundCaption ? "" : message.text, attributes: attributes, inlineStickers: inlineStickers, mediaReference: mediaReference, threadId: nil, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: localGroupingKey, correlationId: nil, bubbleUpEmojiOrStickersets: []))
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

