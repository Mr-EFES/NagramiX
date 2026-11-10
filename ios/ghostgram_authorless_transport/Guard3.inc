import Foundation
import Postbox
import SwiftSignalKit

/// Transform every media slot without changing the poll's identity, metadata,
/// option order or votes. A failed required attachment rejects the whole poll.
public func nagramiXMapPollMedia(_ poll: TelegramMediaPoll, transform: (Media) -> Media?) -> TelegramMediaPoll? {
    var attachedMedia: Media?
    if let original = poll.attachedMedia {
        guard let copied = transform(original) else { return nil }
        attachedMedia = copied
    }
    var options: [TelegramMediaPollOption] = []
    for option in poll.options {
        var media: Media?
        if let original = option.media {
            guard let copied = transform(original) else { return nil }
            media = copied
        }
        options.append(TelegramMediaPollOption(text: option.text, entities: option.entities, opaqueIdentifier: option.opaqueIdentifier, media: media, date: option.date, addedBy: option.addedBy))
    }
    var solution: TelegramMediaPollResults.Solution?
    if let original = poll.results.solution {
        var media: Media?
        if let originalMedia = original.media {
            guard let copied = transform(originalMedia) else { return nil }
            media = copied
        }
        solution = TelegramMediaPollResults.Solution(text: original.text, entities: original.entities, media: media)
    }
    let results = TelegramMediaPollResults(voters: poll.results.voters, totalVoters: poll.results.totalVoters, recentVoters: poll.results.recentVoters, solution: solution, hasUnseenVotes: poll.results.hasUnseenVotes, canViewStats: poll.results.canViewStats)
    return TelegramMediaPoll(pollId: poll.pollId, publicity: poll.publicity, kind: poll.kind, text: poll.text, textEntities: poll.textEntities, options: options, correctAnswers: poll.correctAnswers, results: results, isClosed: poll.isClosed, deadlineTimeout: poll.deadlineTimeout, deadlineDate: poll.deadlineDate, pollHash: poll.pollHash, openAnswers: poll.openAnswers, revotingDisabled: poll.revotingDisabled, shuffleAnswers: poll.shuffleAnswers, hideResultsUntilClose: poll.hideResultsUntilClose, isCreator: poll.isCreator, attachedMedia: attachedMedia, restrictToSubscribers: poll.restrictToSubscribers, countries: poll.countries)
}

public func nagramiXPollMediaAttachments(_ poll: TelegramMediaPoll) -> [Media] {
    return ([poll.attachedMedia] + poll.options.map { $0.media } + [poll.results.solution?.media]).compactMap { $0 }
}

public extension Message {
    /// Only the account's own, already-sent recording may be uploaded again.
    /// Keep this separate from general export: incoming view-once media stays
    /// excluded, and this exception does not enable saving or server forwards.
    func nagramiXAllowsOwnViewOnceCopy(accountPeerId: PeerId?) -> Bool {
        // With retention enabled, outgoing recordings use the same full local
        // copy path as incoming recordings, without a new consumed lifetime.
        // Keep the restricted own-recording exception only for the OFF case.
        guard !nagramiXCanUseTemporaryMediaActions(self), let accountPeerId,
              self.author?.id == accountPeerId,
              !self.flags.contains(.Incoming), !self.flags.isSending, !self.flags.contains(.Failed),
              self.forwardInfo == nil,
              self.id.namespace == Namespaces.Message.Cloud,
              self.id.peerId.namespace == Namespaces.Peer.CloudUser,
              self.id.peerId != accountPeerId, !self.id.peerId.isVerificationCodes,
              self.minAutoremoveOrClearTimeout == viewOnceTimeout,
              self.media.count == 1, let file = self.media.first as? TelegramMediaFile else {
            return false
        }
        return file.isVoice || file.isInstantVideo
    }

    func nagramiXHasLocalViewOnceRecording(mediaBox: MediaBox) -> Bool {
        guard self.media.count == 1, let file = self.media.first as? TelegramMediaFile,
              let path = (file.resource as? LocalFileReferenceMediaResource)?.localFilePath ?? mediaBox.completedResourcePath(file.resource),
              let attributes = try? FileManager.default.attributesOfItem(atPath: path),
              attributes[.type] as? FileAttributeType == .typeRegular,
              let size = (attributes[.size] as? NSNumber)?.int64Value else { return false }
        return size > 0 && (file.size == nil || file.size == size)
    }

    var nagramiXRequiresFreeContentCopy: Bool {
        if self.id.peerId.namespace == Namespaces.Peer.SecretChat || self.isCopyProtected() { return true }
        if self.attributes.contains(where: { ($0 as? EphemeralMessageAttribute)?.isForwardingDisabled == true }) { return true }
        if let group = self.peers[self.id.peerId] as? TelegramGroup { return group.membership != .Member }
        guard let channel = self.peers[self.id.peerId] as? TelegramChannel else {
            return self.id.peerId.namespace == Namespaces.Peer.CloudChannel
        }
        switch channel.participationStatus {
        case .member:
            return false
        case .kicked:
            return true
        case .left:
            return (channel.username ?? "").isEmpty && !channel.usernames.contains { $0.flags.contains(.isActive) }
        }
    }

    var nagramiXAllowsContentCopy: Bool {
        let temporary = nagramiXCanUseTemporaryMediaActions(self)
        let retainedTemporary = self.attributes.contains { ($0 as? NagramiXArchivedMessageAttribute)?.isTemporary == true }
        return (!retainedTemporary || temporary)
            && !self.id.peerId.isVerificationCodes
            && (!self.containsSecretMedia || temporary)
            && (self.minAutoremoveOrClearTimeout != viewOnceTimeout || temporary)
            && !self.flags.isSending && !self.flags.contains(.Failed)
    }

    /// This is a transport decision, independent of the Free Content setting.
    /// Ordinary cloud media can be sent as a new message by reference.
    var nagramiXCopyNeedsLocalMedia: Bool {
        return self.media.contains { $0 is TelegramMediaPaidContent }
            || self.nagramiXRequiresFreeContentCopy
            || nagramiXCanUseTemporaryMediaActions(self)
            || self.attributes.contains { $0 is NagramiXArchivedMessageAttribute }

    }
}

private enum NagramiXContentCopyFetchError: Error { case unavailable }

/// Fetch only primary attachments explicitly selected by the user. This does
/// not consume media, mark history read, or create outgoing messages.
public func nagramiXFetchContentCopyMedia(mediaBox: MediaBox, messages: [Message], accountPeerId: PeerId? = nil) -> Signal<Bool, NoError> {
    var references: [String: (PeerId, MediaResourceReference)] = [:]
    for message in messages {
        if message.nagramiXAllowsOwnViewOnceCopy(accountPeerId: accountPeerId) {
            // Do not open, consume or remotely fetch a view-once original.
            // A new upload is possible only while its full local bytes exist.
            guard message.nagramiXHasLocalViewOnceRecording(mediaBox: mediaBox) else { return .single(false) }
            continue
        }
        guard message.nagramiXAllowsContentCopy else { return .single(false) }
        var mediaToFetch = message.media
        if let richText = message.attributes.first(where: { $0 is RichTextMessageAttribute }) as? RichTextMessageAttribute {
            let page = richText.fullInstantPage ?? richText.instantPage
            guard page.isComplete else { return .single(false) }
            mediaToFetch.append(contentsOf: page.rawMedia.values)
        }
        for poll in message.media.compactMap({ $0 as? TelegramMediaPoll }) {
            mediaToFetch.append(contentsOf: ([poll.attachedMedia, poll.results.solution?.media] + poll.options.map { $0.media }).compactMap { $0 })
        }
        for media in mediaToFetch {
            let resource: TelegramMediaResource
            if let image = media as? TelegramMediaImage {
                guard let largest = image.representations.max(by: { lhs, rhs in
                    Int64(lhs.dimensions.width) * Int64(lhs.dimensions.height) < Int64(rhs.dimensions.width) * Int64(rhs.dimensions.height)
                }) else { return .single(false) }
                resource = largest.resource
            } else if let file = media as? TelegramMediaFile {
                resource = file.resource
            } else {
                continue
            }
            let reference = AnyMediaReference.message(message: MessageReference(message), media: media).resourceReference(resource)
            references[resource.id.stringRepresentation] = (message.id.peerId, reference)
        }
    }
    guard !references.isEmpty else { return .single(true) }
    let signals: [Signal<Bool, NagramiXContentCopyFetchError>] = references.values.map { peerId, reference in
        Signal { subscriber in
            let finished = Atomic<Bool>(value: false)
            let disposables = DisposableSet()
            disposables.add(mediaBox.keepResource(id: reference.resource.id).start())
            disposables.add((mediaBox.resourceData(reference.resource)
            |> filter { $0.complete }
            |> take(1)).start(next: { data in
                guard !finished.swap(true) else { return }
                if data.offset == 0 && data.size > 0 {
                    subscriber.putNext(true)
                    subscriber.putCompletion()
                } else {
                    subscriber.putError(.unavailable)
                }
            }))
            if !finished.with({ $0 }) {
                disposables.add(fetchedMediaResource(mediaBox: mediaBox, userLocation: .peer(peerId), userContentType: .other, reference: reference, reportResultStatus: true).start(error: { _ in
                    guard !finished.swap(true) else { return }
                    subscriber.putError(.unavailable)
                }))
            }
            return ActionDisposable {
                _ = finished.swap(true)
                disposables.dispose()
            }
        }
    }
    return combineLatest(signals)
    |> take(1)
    |> map { $0.allSatisfy { $0 } }
    |> `catch` { _ -> Signal<Bool, NoError> in .single(false) }
}


/// Pins original cache resources until the recipient batch has acquired its
/// independent upload files. Completing/cancelling the signal cannot release
/// resources after the ready event has transferred ownership to the caller.
public final class NagramiXCopyMediaLease {
    private let resources = DisposableSet()
    fileprivate func add(_ disposable: Disposable) { self.resources.add(disposable) }
    public func dispose() { self.resources.dispose() }
    deinit { self.resources.dispose() }
}

public enum NagramiXCopyMediaPreparationEvent {
    case progress(Float)
    case ready(NagramiXCopyMediaLease)
    case failed
}

/// Fetches only attachments whose new-message transport needs local bytes.
/// Cloud references for ordinary posts remain on Telegram's native send path.
public func nagramiXPrepareCopyMedia(mediaBox: MediaBox, messages: [Message]) -> Signal<NagramiXCopyMediaPreparationEvent, NoError> {
    var references: [String: (PeerId, MediaResourceReference)] = [:]
    for message in messages where message.nagramiXCopyNeedsLocalMedia {
        var media = message.media
        if let rich = message.attributes.first(where: { $0 is RichTextMessageAttribute }) as? RichTextMessageAttribute {
            let page = rich.fullInstantPage ?? rich.instantPage
            guard page.isComplete else { return .single(.failed) }
            media.append(contentsOf: page.rawMedia.values)
        }
        var expandedMedia: [Media] = []
        for item in media {
            if let paid = item as? TelegramMediaPaidContent {
                let complete = paid.extendedMedia.compactMap { value -> Media? in
                    if case let .full(media) = value { return media }
                    return nil
                }
                guard complete.count == paid.extendedMedia.count else { return .single(.failed) }
                expandedMedia.append(contentsOf: complete)
            } else { expandedMedia.append(item) }
        }
        func collect(_ item: Media, depth: Int = 0) -> Bool {
            guard depth <= 8 else { return false }
            let resource: TelegramMediaResource
            if let poll = item as? TelegramMediaPoll {
                return nagramiXPollMediaAttachments(poll).allSatisfy { collect($0, depth: depth + 1) }
            } else if let image = item as? TelegramMediaImage {
                guard let largest = image.representations.max(by: { Int64($0.dimensions.width) * Int64($0.dimensions.height) < Int64($1.dimensions.width) * Int64($1.dimensions.height) }) else { return false }
                resource = largest.resource
                if let video = image.video, !collect(video, depth: depth + 1) { return false }
            } else if let file = item as? TelegramMediaFile {
                resource = file.resource
                if let cover = file.videoCover, !collect(cover, depth: depth + 1) { return false }
            } else { return true }
            references[resource.id.stringRepresentation] = (message.id.peerId, AnyMediaReference.message(message: MessageReference(message), media: item).resourceReference(resource))
            return true
        }
        guard expandedMedia.allSatisfy({ collect($0) }) else { return .single(.failed) }
    }
    return Signal { subscriber in
        let lease = NagramiXCopyMediaLease()
        let transferred = Atomic<Bool>(value: false)
        if references.isEmpty {
            _ = transferred.swap(true)
            subscriber.putNext(.ready(lease))
            subscriber.putCompletion()
            return EmptyDisposable
        }
        let signals: [Signal<Float, NagramiXContentCopyFetchError>] = references.values.map { peerId, reference in
            lease.add(mediaBox.keepResource(id: reference.resource.id).start())
            return Signal { itemSubscriber in
                let finished = Atomic<Bool>(value: false)
                let generation = Atomic<Int>(value: 0)
                let subscriptions = DisposableSet()
                func progress(_ value: Float) {
                    guard !finished.with({ $0 }) else { return }
                    let current = generation.modify { $0 + 1 }
                    itemSubscriber.putNext(min(0.99, max(0.0, value)))
                    Queue.concurrentDefaultQueue().after(120.0) {
                        guard generation.with({ $0 }) == current, !finished.swap(true) else { return }
                        itemSubscriber.putError(.unavailable)
                    }
                }
                progress(0.0)
                subscriptions.add((mediaBox.resourceStatus(reference.resource)
                |> distinctUntilChanged).start(next: { status in
                    switch status {
                    case let .Remote(value), let .Paused(value): progress(value)
                    case let .Fetching(_, value): progress(value)
                    case .Local: break
                    }
                }))
                subscriptions.add((mediaBox.resourceData(reference.resource)
                |> filter { $0.complete }
                |> take(1)).start(next: { data in
                    guard !finished.swap(true) else { return }
                    if data.offset == 0 && data.size > 0 {
                        itemSubscriber.putNext(1.0)
                        itemSubscriber.putCompletion()
                    } else {
                        itemSubscriber.putError(.unavailable)
                    }
                }))
                if !finished.with({ $0 }) {
                    subscriptions.add(fetchedMediaResource(mediaBox: mediaBox, userLocation: .peer(peerId), userContentType: .other, reference: reference, reportResultStatus: true).start(error: { _ in
                        guard !finished.swap(true) else { return }
                        itemSubscriber.putError(.unavailable)
                    }))
                }
                return ActionDisposable {
                    _ = finished.swap(true)
                    subscriptions.dispose()
                }
            }
        }
        let subscription = (combineLatest(signals)).start(next: { values in
            if values.allSatisfy({ $0 >= 1.0 }) {
                guard !transferred.swap(true) else { return }
                subscriber.putNext(.ready(lease))
                subscriber.putCompletion()
            } else {
                subscriber.putNext(.progress(values.reduce(0.0, +) / Float(values.count)))
            }
        }, error: { _ in
            lease.dispose()
            subscriber.putNext(.failed)
            subscriber.putCompletion()
        })
        return ActionDisposable {
            subscription.dispose()
            if !transferred.with({ $0 }) { lease.dispose() }
        }
    }
}
