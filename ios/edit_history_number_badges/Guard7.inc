import Foundation
import SwiftSignalKit
import Postbox
internal import TelegramApi

public func nagramiXCanCopyMessagesAsNew(_ messages: [EngineRawMessage], accountPeerId: EnginePeer.Id? = nil) -> Bool {
    return !messages.isEmpty && messages.allSatisfy { message in
        return message.nagramiXAllowsContentCopy || message.nagramiXAllowsOwnViewOnceCopy(accountPeerId: accountPeerId)
    }
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
    // Check every slot; the native sender resolves cloud references first and
    // uploads local/rejected attachments before assembling the complete poll.
    let attachments = [poll.attachedMedia, poll.results.solution?.media] + poll.options.map { $0.media }
    guard attachments.compactMap({ $0 }).allSatisfy({ $0 is TelegramMediaImage || $0 is TelegramMediaFile || pollCloudMediaToInputMedia($0) != nil }) else { return nil }
    let options = poll.options.map {
        TelegramMediaPollOption(text: $0.text, entities: $0.entities, opaqueIdentifier: $0.opaqueIdentifier, media: $0.media, date: nil, addedBy: nil)
    }
    let results = TelegramMediaPollResults(voters: nil, totalVoters: nil, recentVoters: [], solution: poll.results.solution, hasUnseenVotes: nil, canViewStats: false)
    return TelegramMediaPoll(pollId: MediaId(namespace: Namespaces.Media.LocalPoll, id: Int64.random(in: 1 ... Int64.max)), publicity: poll.publicity, kind: poll.kind, text: poll.text, textEntities: poll.textEntities, options: options, correctAnswers: correctAnswers, results: results, isClosed: false, deadlineTimeout: nil, deadlineDate: nil, pollHash: 0, openAnswers: poll.openAnswers, revotingDisabled: poll.revotingDisabled, shuffleAnswers: poll.shuffleAnswers, hideResultsUntilClose: poll.hideResultsUntilClose, isCreator: true, attachedMedia: poll.attachedMedia, restrictToSubscribers: poll.restrictToSubscribers, countries: poll.countries)
}

public func nagramiXCopyMessagesAsNew(_ messages: [EngineRawMessage], account: Account? = nil, hideCaptions: Bool = false, forceLocalMedia: Bool = false, accountPeerId: EnginePeer.Id? = nil, mediaCopy: NagramiXArchivedMediaCopy? = nil) -> [EnqueueMessage]? {
    return nagramiXBuildCopiedMessages(messages, account: account, hideCaptions: hideCaptions, forceLocalMedia: forceLocalMedia, accountPeerId: accountPeerId, mediaCopy: mediaCopy)?.messages
}

/// Each source owns its complete output range. Build the entire selection in
/// one pass so album keys and local resource ownership are shared consistently.
public func nagramiXCopyMessagesAsNewBySource(_ messages: [EngineRawMessage], account: Account? = nil, hideCaptions: Bool = false, forceLocalMedia: Bool = false, accountPeerId: EnginePeer.Id? = nil, mediaCopy: NagramiXArchivedMediaCopy? = nil) -> [EngineMessage.Id: [EnqueueMessage]]? {
    guard Set(messages.map { $0.id }).count == messages.count,
          let batch = nagramiXBuildCopiedMessages(messages, account: account, hideCaptions: hideCaptions, forceLocalMedia: forceLocalMedia, accountPeerId: accountPeerId, mediaCopy: mediaCopy),
          batch.sourceRanges.count == messages.count else { return nil }
    var result: [EngineMessage.Id: [EnqueueMessage]] = [:]
    for (index, message) in messages.enumerated() {
        let range = batch.sourceRanges[index]
        guard !range.isEmpty, range.lowerBound >= 0, range.upperBound <= batch.messages.count else { return nil }
        result[message.id] = Array(batch.messages[range])
    }
    return result
}

private func nagramiXBuildCopiedMessages(_ messages: [EngineRawMessage], account: Account? = nil, hideCaptions: Bool = false, forceLocalMedia: Bool = false, accountPeerId: EnginePeer.Id? = nil, mediaCopy: NagramiXArchivedMediaCopy? = nil) -> (messages: [EnqueueMessage], sourceRanges: [Range<Int>])? {
    guard !messages.isEmpty else {
        return nil
    }
    let mediaBox = account?.postbox.mediaBox
    let archivedMediaCopy = mediaCopy ?? mediaBox.map { NagramiXArchivedMediaCopy(mediaBox: $0) }
    var result: [EnqueueMessage] = []
    var sourceRanges: [Range<Int>] = []
    var copiedGroupingKeys: [Int64: Int64] = [:]
    for message in messages {
        let outputStart = result.count
        // Paid bundles and separate round captions can expand one input. The
        // range is recorded at iteration exit, including the paid continue path.
        defer { sourceRanges.append(outputStart ..< result.count) }
        let ownViewOnce = message.nagramiXAllowsOwnViewOnceCopy(accountPeerId: accountPeerId)
        guard message.nagramiXAllowsContentCopy || ownViewOnce else { return nil }
        if ownViewOnce, let mediaBox, !message.nagramiXHasLocalViewOnceRecording(mediaBox: mediaBox) {
            return nil
        }

        if let paid = message.media.first as? TelegramMediaPaidContent {
            let complete = paid.extendedMedia.compactMap { item -> Media? in
                if case let .full(media) = item { return media }
                return nil
            }
            guard !complete.isEmpty, complete.count == paid.extendedMedia.count else { return nil }
            var parts: [Message] = []
            let sourceGroup = message.groupingKey ?? Int64.random(in: 1 ... Int64.max)
            let groupingKey = copiedGroupingKeys[sourceGroup] ?? Int64.random(in: 1 ... Int64.max)
            copiedGroupingKeys[sourceGroup] = groupingKey
            for (index, medium) in complete.enumerated() {
                var part = message.withUpdatedMedia([medium])
                if index != 0 { part = part.withUpdatedText("").withUpdatedAttributes(part.attributes.filter { !($0 is TextEntitiesMessageAttribute) }) }
                parts.append(part)
            }
            guard let copies = nagramiXCopyMessagesAsNew(parts, account: account, hideCaptions: hideCaptions, forceLocalMedia: true, accountPeerId: accountPeerId, mediaCopy: archivedMediaCopy) else { return nil }
            result.append(contentsOf: copies.map { $0.withUpdatedGroupingKey { _ in groupingKey } })
            continue
        }

        var attributes: [EngineMessage.Attribute] = []
        let sourceInfo = message.attributes.first(where: { $0 is OutgoingContentInfoMessageAttribute }) as? OutgoingContentInfoMessageAttribute
        var copyFlags: OutgoingContentInfoFlags = [.nagramiXCopy]
        if !message.media.contains(where: { $0 is TelegramMediaWebpage }) { copyFlags.insert(.disableLinkPreviews) }
        attributes.append(OutgoingContentInfoMessageAttribute(flags: copyFlags, nagramiXCopyFallbackText: sourceInfo?.nagramiXCopyFallbackText))
        let sourceWebpage = message.media.first(where: { $0 is TelegramMediaWebpage }) as? TelegramMediaWebpage
        // Copy the post's explicit preview choice. A bare text link must stay a bare text link.
        if sourceWebpage == nil {
            // Preview policy is included in the persisted copy transport flags.
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
                if let archivedMediaCopy, forceLocalMedia || message.nagramiXCopyNeedsLocalMedia {
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
                var sourcePoll = poll
                if forceLocalMedia || message.nagramiXCopyNeedsLocalMedia, let archivedMediaCopy {
                    guard let localPoll = archivedMediaCopy.prepare(poll) as? TelegramMediaPoll else { return nil }
                    sourcePoll = localPoll
                }
                guard let copy = nagramiXCopyPollAsNew(sourcePoll) else { return nil }
                if forceLocalMedia || message.nagramiXCopyNeedsLocalMedia {
                    mediaReference = .standalone(media: copy)
                } else {
                    // Native partial provenance refreshes nested cloud files.
                    // The payload is still a new poll with no forward header.
                    mediaReference = .message(message: MessageReference(message), media: copy)
                }
            } else if mediaReference == nil && (media is TelegramMediaImage || media is TelegramMediaFile || media is TelegramMediaContact || media is TelegramMediaMap || media is TelegramMediaTodo || media is TelegramMediaGame) {
                if ownViewOnce || nagramiXCanUseTemporaryMediaActions(message) || forceLocalMedia || message.nagramiXCopyNeedsLocalMedia {
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
        let separateRoundCaption = (message.media.first as? TelegramMediaFile)?.isInstantVideo == true
            && !hidesCaption && !message.text.isEmpty
        // Round-video bubbles do not render captions. Keep an authored repost's
        // signature as a neighbouring text message rather than invisible text.
        if separateRoundCaption {
            result.append(.message(text: message.text, attributes: attributes.filter { $0 is TextEntitiesMessageAttribute || $0 is OutgoingContentInfoMessageAttribute }, inlineStickers: inlineStickers, mediaReference: nil, threadId: nil, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: nil, correlationId: nil, bubbleUpEmojiOrStickersets: []))
            attributes.removeAll(where: { $0 is TextEntitiesMessageAttribute })
            inlineStickers = [:]
        }
        result.append(.message(text: hidesCaption || separateRoundCaption ? "" : message.text, attributes: attributes, inlineStickers: inlineStickers, mediaReference: mediaReference, threadId: nil, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: localGroupingKey, correlationId: nil, bubbleUpEmojiOrStickersets: []))
    }
    if mediaCopy == nil { archivedMediaCopy?.commit() }
    return (result, sourceRanges)
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


/// Retrying a rejected copy keeps its original pending identity/random_id.
/// A lost acknowledgement therefore cannot turn retry into a second send.
public func nagramiXRetryCopiedMessages(account: Account, messageIds: [EngineMessage.Id]) -> Signal<Void, NoError> {
    return account.postbox.transaction { transaction -> Void in
        for id in Set(messageIds) {
            transaction.updateMessage(id, update: { message in
                guard message.flags.contains(.Failed), !message.flags.contains(.Incoming),
                      message.attributes.contains(where: { ($0 as? OutgoingContentInfoMessageAttribute)?.flags.contains(.nagramiXCopy) == true }) else { return .skip }
                return .update(StoreMessage(id: message.id, customStableId: nil, globallyUniqueId: message.globallyUniqueId, groupingKey: message.groupingKey, threadId: message.threadId, timestamp: message.timestamp, flags: [.Unsent], tags: message.tags, globalTags: message.globalTags, localTags: message.localTags, forwardInfo: nil, authorId: message.author?.id, text: message.text, attributes: message.attributes, media: message.media))
            })
        }
    }
}
