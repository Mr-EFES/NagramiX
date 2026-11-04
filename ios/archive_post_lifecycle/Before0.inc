import Foundation
import Postbox
import SwiftSignalKit

/// The archive lives in TelegramCore, below the NagramiXCore presentation
/// module in the Bazel dependency graph. Read the persisted switches from
/// the same UserDefaults keys used by NagramiXTabSettings without introducing
/// a TelegramCore -> NagramiXCore dependency cycle.
private struct NagramiXMessageArchiveSettings {
    static let changedNotification = Notification.Name("NagramiXSettingsChanged")

    let showDeletedMessages: Bool
    let saveTemporaryMessages: Bool
    let replayViewOnce: Bool
    let messageEditHistory: Bool

    static var current: NagramiXMessageArchiveSettings {
        let defaults = UserDefaults.standard
        return NagramiXMessageArchiveSettings(
            showDeletedMessages: defaults.object(forKey: "nagramix.messages.showDeletedMessages") as? Bool ?? false,
            saveTemporaryMessages: (defaults.bool(forKey: "nagramix.messages.saveTemporaryMessages") || defaults.bool(forKey: "nagramix.messages.replayViewOnce")),
            replayViewOnce: (defaults.bool(forKey: "nagramix.messages.saveTemporaryMessages") || defaults.bool(forKey: "nagramix.messages.replayViewOnce")),
            messageEditHistory: defaults.object(forKey: "nagramix.messages.editHistory") as? Bool ?? false
        )
    }
}

public struct NagramiXMessageRevision: Codable, Equatable {
    public let text: String
    public let entities: [MessageTextEntity]
    public let timestamp: Int32

    public init(text: String, entities: [MessageTextEntity], timestamp: Int32) {
        self.text = text
        self.entities = entities
        self.timestamp = timestamp
    }

    /// Only consecutive equal text/entities are duplicates. A → B → A is three
    /// versions, even when several edits arrive during the same second.
    static func appendIfChanged(_ revision: NagramiXMessageRevision, to revisions: inout [NagramiXMessageRevision]) {
        if revisions.last?.text != revision.text || revisions.last?.entities != revision.entities {
            revisions.append(revision)
        }
    }
}

/// Marks a synthetic, display-only message supplied by NagramiXMessageArchive.
/// These messages never enter Postbox and must not be used for server actions.
public final class NagramiXArchivedMessageAttribute: MessageAttribute {
    public let deletedAt: Int32
    public let revisions: [NagramiXMessageRevision]
    public let isTemporary: Bool
    public let isViewOnceReplay: Bool

    public init(deletedAt: Int32, revisions: [NagramiXMessageRevision], isTemporary: Bool = false, isViewOnceReplay: Bool = false) {
        self.deletedAt = deletedAt
        self.revisions = revisions
        self.isTemporary = isTemporary
        self.isViewOnceReplay = isViewOnceReplay
    }

    public required init(decoder: PostboxDecoder) {
        self.deletedAt = decoder.decodeInt32ForKey("d", orElse: 0)
        self.revisions = []
        self.isTemporary = decoder.decodeBoolForKey("t", orElse: false)
        self.isViewOnceReplay = decoder.decodeBoolForKey("v", orElse: false)
    }

    public func encode(_ encoder: PostboxEncoder) {
        encoder.encodeInt32(self.deletedAt, forKey: "d")
        encoder.encodeBool(self.isTemporary, forKey: "t")
        encoder.encodeBool(self.isViewOnceReplay, forKey: "v")
    }
}

public extension Message {
    var nagramiXIsViewOnceReplay: Bool {
        return self.attributes.contains { ($0 as? NagramiXArchivedMessageAttribute)?.isViewOnceReplay == true }
    }
    var nagramiXShowsArchiveNotice: Bool {
        return self.attributes.contains { attribute in
            guard let archived = attribute as? NagramiXArchivedMessageAttribute else { return false }
            return !archived.isTemporary || archived.isViewOnceReplay
        }
    }
}

private struct NagramiXArchivedContent: Codable, Equatable {
    let text: String
    let entities: [MessageTextEntity]
    let media: [Data]
}

private struct NagramiXArchivedRecord: Codable, Equatable {
    let peerId: Int64
    let namespace: Int32
    let id: Int32
    let authorId: Int64?
    let timestamp: Int32
    let threadId: Int64?
    let groupingKey: Int64?
    let incoming: Bool
    var temporary: Bool?
    var viewOnceReplay: Bool?
    var peerData: [String: Data]
    var content: NagramiXArchivedContent
    var contentTimestamp: Int32?
    var revisions: [NagramiXMessageRevision]
    var deletedAt: Int32?
    var transcriptionAttributes: [Data]? = nil

    var messageId: MessageId {
        return MessageId(peerId: PeerId(self.peerId), namespace: self.namespace, id: self.id)
    }
}

private struct NagramiXMessageArchiveState: Codable, Equatable {
    var records: [String: NagramiXArchivedRecord] = [:]
}

private final class NagramiXWeakMessageArchive {
    weak var value: NagramiXMessageArchive?

    init(_ value: NagramiXMessageArchive) {
        self.value = value
    }
}

public final class NagramiXMessageArchive {
    private static let registry = Atomic<[ObjectIdentifier: NagramiXWeakMessageArchive]>(value: [:])

    public static func forPostbox(_ postbox: Postbox) -> NagramiXMessageArchive? {
        return self.registry.with { $0[ObjectIdentifier(postbox)]?.value }
    }

    public static func forMediaBox(_ mediaBox: MediaBox) -> NagramiXMessageArchive? {
        return self.registry.with { values in
            values.values.compactMap { $0.value }.first { $0.postbox.mediaBox === mediaBox }
        }
    }

    private let postbox: Postbox
    private let accountPeerId: PeerId
    public let deferredReactions: NagramiXDeferredReactionsStore
    private let path: String
    private let basePath: String
    private let queue: Queue
    private let state = Atomic<NagramiXMessageArchiveState>(value: NagramiXMessageArchiveState())
    private let replayCapturePending = Atomic<Set<MessageId>>(value: [])
    private let revisionValue = ValuePromise<Int>(0, ignoreRepeated: false)
    private var revision: Int = 0
    private var settingsObserver: NSObjectProtocol?
    private var lifecycleObservers: [NSObjectProtocol] = []
    private var readyForMediaDownloads = false
    private var inForeground = true
    private var mediaDownloadSettings: (Bool, Bool, Bool)?
    private let renderVersion = Atomic<UInt32>(value: 0)
    private let storageStatusValue = ValuePromise<NagramiXArchiveStorageStatus>(.ready, ignoreRepeated: true)
    private var loadBlocked = false
    private var publishAfterRetry = false
    private var removalTickets: [String: Int64] = [:]
    private var clearTicket: Int64?
    private lazy var persistence = NagramiXArchivePersistence<NagramiXMessageArchiveState>(write: { [weak self] state in
        guard let self else { throw NagramiXArchiveStorageFailure.writeFailed }
        try JSONEncoder().encode(state).write(to: URL(fileURLWithPath: self.path), options: [.atomic])
    }, schedule: { [weak self] delay, action in
        guard let self else { return {} }
        let timer = SwiftSignalKit.Timer(timeout: delay, repeat: false, completion: action, queue: self.queue)
        timer.start()
        return { timer.invalidate() }
    }, committed: { [weak self] state in
        self?.didPersist(state)
    }, status: { [weak self] status in
        guard let self else { return }
        if case .failed = status { self.publishAfterRetry = true }
        self.storageStatusValue.set(status)
    })

    public var storageStatus: Signal<NagramiXArchiveStorageStatus, NoError> { self.storageStatusValue.get() }

    private var mutationState: NagramiXMessageArchiveState {
        return self.persistence.pending ?? self.state.with { $0 }
    }

    private lazy var mediaStore = NagramiXArchivedMediaStore(mediaBox: self.postbox.mediaBox, queue: self.queue, basePath: self.basePath, changed: { [weak self] in
        self?.publishUpdate()
    })

    public var updates: Signal<Int, NoError> {
        return self.revisionValue.get()
    }

    var capturesMessageEdits: Bool {
        let settings = NagramiXMessageArchiveSettings.current
        return settings.showDeletedMessages || settings.messageEditHistory
    }

    public init(postbox: Postbox, accountPeerId: PeerId, basePath: String) {
        self.postbox = postbox
        self.accountPeerId = accountPeerId
        self.deferredReactions = NagramiXDeferredReactionsStore(accountPeerId: accountPeerId, basePath: basePath)
        self.path = basePath + "/nagramix-message-archive.json"
        self.basePath = basePath
        self.queue = Queue(name: "org.nagramix.message-archive", qos: .utility)
        _ = self.mediaStore

        _ = Self.registry.modify { value in
            var value = value
            value[ObjectIdentifier(postbox)] = NagramiXWeakMessageArchive(self)
            return value
        }
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            _ = self.loadPersistedState()
            self.mediaStore.load()
            for (key, record) in self.state.with({ $0.records }) {
                let requests = self.mediaRequests(record)
                if let ticket = self.mediaStore.reserveRestored(key: key, requests: requests) {
                    self.mediaStore.retain(key: key, requests: requests, ticket: ticket)
                }
            }
            self.publishUpdate()
        }

        self.settingsObserver = NotificationCenter.default.addObserver(forName: NagramiXMessageArchiveSettings.changedNotification, object: nil, queue: nil, using: { [weak self] _ in
            self?.queue.async {
                self?.refreshMediaDownloads()
                self?.publishUpdate()
            }
        })
        for (name, foreground) in [("UIApplicationDidEnterBackgroundNotification", false), ("UIApplicationWillEnterForegroundNotification", true)] {
            self.lifecycleObservers.append(NotificationCenter.default.addObserver(forName: Notification.Name(name), object: nil, queue: nil, using: { [weak self] _ in
                self?.queue.async {
                    guard let self else { return }
                    self.inForeground = foreground
                    self.refreshMediaDownloads()
                    if foreground { self.retryStorage() }
                }
            }))
        }
    }

    deinit {
        if let settingsObserver = self.settingsObserver {
            NotificationCenter.default.removeObserver(settingsObserver)
        }
        for observer in self.lifecycleObservers { NotificationCenter.default.removeObserver(observer) }
        _ = Self.registry.modify { value in
            var value = value
            value.removeValue(forKey: ObjectIdentifier(self.postbox))
            return value
        }
    }

    public func startMediaDownloads() {
        self.queue.async { [weak self] in
            guard let self else { return }
            self.readyForMediaDownloads = true
            self.refreshMediaDownloads()
        }
    }

    private func refreshMediaDownloads() {
        let settings = NagramiXMessageArchiveSettings.current
        let enabled = self.readyForMediaDownloads && self.inForeground && settings.showDeletedMessages
        let temporary = settings.saveTemporaryMessages
        let replay = self.readyForMediaDownloads && self.inForeground && settings.replayViewOnce
        if let current = self.mediaDownloadSettings, current.0 == enabled, current.1 == temporary, current.2 == replay { return }
        self.mediaDownloadSettings = (enabled, temporary, replay)
        self.mediaStore.configure(enabled: enabled, temporaryEnabled: temporary, replayEnabled: replay)
    }

    public func cacheResourcesToRemove(_ ids: [MediaResourceId]) -> [MediaResourceId] {
        let settings = NagramiXMessageArchiveSettings.current
        guard settings.showDeletedMessages || settings.replayViewOnce else { return ids }
        return self.mediaStore.resourcesToRemove(ids, includeTemporary: settings.showDeletedMessages && settings.saveTemporaryMessages, includeOrdinary: settings.showDeletedMessages, includeReplay: settings.replayViewOnce)
    }

    private func publishUpdate() {
        self.revision += 1
        _ = self.renderVersion.modify { $0 &+ 1 }
        self.revisionValue.set(self.revision)
    }

    private func loadPersistedState() -> Bool {
        do {
            let data = try Data(contentsOf: URL(fileURLWithPath: self.path))
            let loaded = try JSONDecoder().decode(NagramiXMessageArchiveState.self, from: data)
            _ = self.state.swap(loaded)
            self.loadBlocked = false
            self.storageStatusValue.set(.ready)
            return true
        } catch {
            let error = error as NSError
            if error.domain == NSCocoaErrorDomain && error.code == NSFileReadNoSuchFileError {
                self.loadBlocked = false
                self.storageStatusValue.set(.ready)
                return true
            }
            // Never overwrite an existing unreadable archive with an empty one.
            self.loadBlocked = true
            self.storageStatusValue.set(.failed(.unreadable))
            return false
        }
    }

    public func retryPersistence() {
        self.queue.async { [weak self] in self?.retryStorage() }
    }

    private func retryStorage() {
        if self.loadBlocked {
            self.storageStatusValue.set(.retrying)
            guard self.loadPersistedState() else { return }
            self.publishUpdate()
        }
        _ = self.persistence.retry()
    }

    @discardableResult
    private func persist(_ state: NagramiXMessageArchiveState, retryNow: Bool = false) -> Bool {
        guard !self.loadBlocked else {
            self.storageStatusValue.set(.failed(.unreadable))
            return false
        }
        return self.persistence.submit(state, retryNow: retryNow)
    }

    private func didPersist(_ updated: NagramiXMessageArchiveState) {
        _ = self.state.swap(updated)
        if let ticket = self.clearTicket, updated.records.isEmpty {
            self.mediaStore.clear(before: ticket)
        } else {
            for (key, ticket) in self.removalTickets where updated.records[key] == nil {
                self.mediaStore.remove(keys: Set([key]), before: ticket)
            }
        }
        self.removalTickets.removeAll()
        self.clearTicket = nil
        if self.publishAfterRetry {
            self.publishAfterRetry = false
            self.publishUpdate()
        }
    }

    private static func key(_ id: MessageId) -> String {
        return "\(id.peerId.toInt64()):\(id.namespace):\(id.id)"
    }

    private static func encodedRootObject(_ object: PostboxCoding) -> Data {
        let encoder = PostboxEncoder()
        encoder.encodeRootObject(object)
        return encoder.makeData()
    }

    private static func decodedRootObject(_ data: Data) -> PostboxCoding? {
        return PostboxDecoder(buffer: MemoryBuffer(data: data)).decodeRootObject()
    }

    private func mediaRequests(_ record: NagramiXArchivedRecord) -> [NagramiXArchiveMediaRequest] {
        var peers: [PeerId: Peer] = [:]
        for data in record.peerData.values {
            if let peer = Self.decodedRootObject(data) as? Peer { peers[peer.id] = peer }
        }
        guard let peer = peers[record.messageId.peerId] else { return [] }
        let reference = MessageReference(peer: peer, author: record.authorId.flatMap { peers[PeerId($0)] }, id: record.messageId, timestamp: record.timestamp, incoming: record.incoming, secret: record.temporary == true, threadId: record.threadId)
        var result: [NagramiXArchiveMediaRequest] = []
        var seen = Set<MediaResourceId>()
        for data in record.content.media {
            guard let media = Self.decodedRootObject(data) as? Media else { continue }
            let mediaReference = AnyMediaReference.message(message: reference, media: media)
            func append(_ resource: TelegramMediaResource, primary: Bool) {
                guard !(resource is EmptyMediaResource), seen.insert(resource.id).inserted else { return }
                result.append(NagramiXArchiveMediaRequest(reference: mediaReference.resourceReference(resource), temporary: record.temporary == true, primary: primary, replay: record.viewOnceReplay == true))
            }
            func appendImage(_ image: TelegramMediaImage) {
                let largest = image.representations.max { lhs, rhs in
                    Int64(lhs.dimensions.width) * Int64(lhs.dimensions.height) < Int64(rhs.dimensions.width) * Int64(rhs.dimensions.height)
                }
                for representation in image.representations { append(representation.resource, primary: representation === largest) }
                for video in image.videoRepresentations { append(video.resource, primary: true) }
                if let video = image.video { appendFile(video) }
            }
            func appendFile(_ file: TelegramMediaFile) {
                append(file.resource, primary: true)
                for representation in file.previewRepresentations { append(representation.resource, primary: false) }
                for thumbnail in file.videoThumbnails { append(thumbnail.resource, primary: false) }
                if let cover = file.videoCover { appendImage(cover) }
                for alternative in file.alternativeRepresentations { appendFile(alternative) }
            }
            if let image = media as? TelegramMediaImage { appendImage(image) }
            if let file = media as? TelegramMediaFile { appendFile(file) }
        }
        return result
    }

    private func localRepresentation(_ representation: TelegramMediaImageRepresentation) -> TelegramMediaImageRepresentation {
        return TelegramMediaImageRepresentation(dimensions: representation.dimensions, resource: self.mediaStore.localResource(for: representation.resource), progressiveSizes: representation.progressiveSizes, immediateThumbnailData: representation.immediateThumbnailData, hasVideo: representation.hasVideo, isPersonal: representation.isPersonal, typeHint: representation.typeHint)
    }

    private func localImage(_ image: TelegramMediaImage) -> TelegramMediaImage {
        return TelegramMediaImage(imageId: image.imageId, representations: image.representations.map(self.localRepresentation), videoRepresentations: image.videoRepresentations.map { TelegramMediaImage.VideoRepresentation(dimensions: $0.dimensions, resource: self.mediaStore.localResource(for: $0.resource), startTimestamp: $0.startTimestamp) }, immediateThumbnailData: image.immediateThumbnailData, emojiMarkup: image.emojiMarkup, reference: image.reference, partialReference: nil, flags: image.flags, video: image.video.map(self.localFile))
    }

    private func localFile(_ file: TelegramMediaFile) -> TelegramMediaFile {
        return TelegramMediaFile(fileId: file.fileId, partialReference: nil, resource: self.mediaStore.localResource(for: file.resource), previewRepresentations: file.previewRepresentations.map(self.localRepresentation), videoThumbnails: file.videoThumbnails.map { TelegramMediaFile.VideoThumbnail(dimensions: $0.dimensions, resource: self.mediaStore.localResource(for: $0.resource)) }, videoCover: file.videoCover.map(self.localImage), immediateThumbnailData: file.immediateThumbnailData, mimeType: file.mimeType, size: file.size, attributes: file.attributes, alternativeRepresentations: file.alternativeRepresentations.map(self.localFile))
    }

    private func localMedia(_ media: Media) -> Media {
        if let image = media as? TelegramMediaImage { return self.localImage(image) }
        if let file = media as? TelegramMediaFile { return self.localFile(file) }
        return media
    }

    private static func makeRecord(message: StoreMessage, peers: [PeerId: Peer]) -> NagramiXArchivedRecord? {
        guard case let .Id(id) = message.id else {
            return nil
        }
        guard id.namespace == Namespaces.Message.Cloud, id.peerId.namespace != Namespaces.Peer.SecretChat else {
            return nil
        }
        guard !id.peerId.isVerificationCodes else {
            return nil
        }
        let temporary = message.attributes.contains(where: { $0 is AutoremoveTimeoutMessageAttribute || $0 is AutoclearTimeoutMessageAttribute })
        let viewOnce = message.flags.contains(.Incoming) && id.peerId.namespace == Namespaces.Peer.CloudUser && message.attributes.contains(where: {
            if let value = $0 as? AutoremoveTimeoutMessageAttribute { return value.timeout == viewOnceTimeout || (value.timeout > 0 && value.timeout <= 60) }
            if let value = $0 as? AutoclearTimeoutMessageAttribute { return value.timeout == viewOnceTimeout || (value.timeout > 0 && value.timeout <= 60) }
            return false
        })
        let replay = viewOnce && NagramiXMessageArchiveSettings.current.replayViewOnce
        guard !message.flags.contains(.CopyProtected) || (temporary && NagramiXMessageArchiveSettings.current.saveTemporaryMessages) || replay else {
            return nil
        }
        guard !temporary || NagramiXMessageArchiveSettings.current.saveTemporaryMessages || replay else { return nil }
        guard !message.attributes.contains(where: { $0 is EphemeralMessageAttribute || $0 is EphemeralOutgoingMessageAttribute }),
              !message.media.contains(where: { $0 is TelegramMediaExpiredContent }) else {
            return nil
        }
        guard !message.media.contains(where: { $0 is TelegramMediaPaidContent }) else {
            return nil
        }
        guard peers[id.peerId]?.isCopyProtectionEnabled != true else {
            return nil
        }

        let entities = (message.attributes.first(where: { $0 is TextEntitiesMessageAttribute }) as? TextEntitiesMessageAttribute)?.entities ?? []
        let media = message.media.compactMap { media -> Data? in
            if media is TelegramMediaImage || media is TelegramMediaFile {
                return self.encodedRootObject(media)
            }
            return nil
        }
        var peerData: [String: Data] = [:]
        var peerIds = Set<PeerId>([id.peerId])
        if let authorId = message.authorId {
            peerIds.insert(authorId)
        }
        for media in message.media {
            peerIds.formUnion(media.peerIds)
        }
        for peerId in peerIds {
            if let peer = peers[peerId] {
                peerData["\(peerId.toInt64())"] = self.encodedRootObject(peer)
            }
        }
        return NagramiXArchivedRecord(
            peerId: id.peerId.toInt64(),
            namespace: id.namespace,
            id: id.id,
            authorId: message.authorId?.toInt64(),
            timestamp: message.timestamp,
            threadId: message.threadId,
            groupingKey: message.groupingKey,
            incoming: message.flags.contains(.Incoming),
            temporary: temporary,
            viewOnceReplay: replay ? true : nil,
            peerData: peerData,
            content: NagramiXArchivedContent(text: message.text, entities: entities, media: media),
            contentTimestamp: (message.attributes.first(where: { $0 is EditedMessageAttribute }) as? EditedMessageAttribute).flatMap { $0.date > 0 ? $0.date : nil } ?? message.timestamp,
            revisions: [],
            deletedAt: nil,
            transcriptionAttributes: temporary ? message.attributes.filter {
                $0 is AudioTranscriptionMessageAttribute || $0 is DerivedDataMessageAttribute
            }.map(self.encodedRootObject) : nil
        )
    }

    private static func makeRecord(message: Message, peers: [PeerId: Peer]) -> NagramiXArchivedRecord? {
        return self.makeRecord(
            message: StoreMessage(
                id: .Id(message.id),
                customStableId: nil,
                globallyUniqueId: message.globallyUniqueId,
                groupingKey: message.groupingKey,
                threadId: message.threadId,
                timestamp: message.timestamp,
                flags: StoreMessageFlags(message.flags),
                tags: message.tags,
                globalTags: message.globalTags,
                localTags: message.localTags,
                forwardInfo: nil,
                authorId: message.author?.id,
                text: message.text,
                attributes: message.attributes,
                media: message.media
            ),
            peers: peers
        )
    }

    /// Called after a successful native send has its final server ID/resources.
    /// captureIncoming is the historical shared ingestion entry, now bidirectional.
    public func captureSent(_ message: StoreMessage, transaction: Transaction) {
        guard NagramiXMessageArchiveSettings.current.showDeletedMessages,
              !message.flags.contains(.Incoming) else { return }
        var peers: [PeerId: Peer] = [:]
        var ids = Set<PeerId>([message.id.peerId])
        if let authorId = message.authorId { ids.insert(authorId) }
        for media in message.media { ids.formUnion(media.peerIds) }
        for id in ids { if let peer = transaction.getPeer(id) { peers[id] = peer } }
        self.captureIncoming(message, peers: peers)
    }

    public func captureIncoming(_ message: StoreMessage, peers: [PeerId: Peer]) {
        if message.media.contains(where: { $0 is TelegramMediaExpiredContent }), case let .Id(id) = message.id {
            self.markTemporaryExpired(id: id, expiredAt: Int32(Date().timeIntervalSince1970))
            return
        }
        let settings = NagramiXMessageArchiveSettings.current
        // Edit history captures the real previous Message immediately before an edit is
        // applied. Keeping each approved message on disk is only necessary when a
        // later server-side deletion may need to be rendered locally.
        let eligibleReplay = settings.replayViewOnce && message.flags.contains(.Incoming)
            && message.id.peerId.namespace == Namespaces.Peer.CloudUser
            && message.attributes.contains(where: {
                if let value = $0 as? AutoremoveTimeoutMessageAttribute { return value.timeout == viewOnceTimeout || (value.timeout > 0 && value.timeout <= 60) }
                if let value = $0 as? AutoclearTimeoutMessageAttribute { return value.timeout == viewOnceTimeout || (value.timeout > 0 && value.timeout <= 60) }
                return false
            }) && message.media.contains(where: { media in
                if media is TelegramMediaImage { return true }
                if let file = media as? TelegramMediaFile { return file.isVoice || file.isInstantVideo || file.isVideo || file.isMusic || file.isAnimated }
                return false
            })
        guard settings.showDeletedMessages || eligibleReplay else {
            return
        }
        guard let record = Self.makeRecord(message: message, peers: peers), record.messageId.peerId != self.accountPeerId else {
            return
        }
        let requests = self.mediaRequests(record)
        let ticket = self.mediaStore.reserve(key: Self.key(record.messageId), requests: requests)
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            var updated = self.mutationState
            let key = Self.key(record.messageId)
            if let current = updated.records[key] {
                var record = record
                if current.viewOnceReplay == true { record.viewOnceReplay = true }
                record.revisions = current.revisions
                if record.content.media == current.content.media, record.transcriptionAttributes?.isEmpty != false {
                    record.transcriptionAttributes = current.transcriptionAttributes
                }
                if record.content == current.content {
                    // Re-fetching a message must not reset the edit date.
                    record.contentTimestamp = max(current.contentTimestamp ?? current.timestamp, record.contentTimestamp ?? record.timestamp)
                } else if settings.messageEditHistory {
                    // History pages / sync can refresh an existing snapshot too,
                    // without going through the explicit edit-update operation.
                    NagramiXMessageRevision.appendIfChanged(NagramiXMessageRevision(text: current.content.text, entities: current.content.entities, timestamp: current.contentTimestamp ?? current.timestamp), to: &record.revisions)
                }
                record.deletedAt = current.deletedAt
                updated.records[key] = record
            } else {
                updated.records[key] = record
            }
            self.persist(updated)
            let retainedRequests = updated.records[key].map(self.mediaRequests) ?? requests
            self.mediaStore.retain(key: key, requests: retainedRequests, ticket: ticket)
        }
    }

    /// Also covers existing attachments when the switch was enabled after receipt.
    /// Capturing bytes does not itself consume the message or start its timer.
    public func captureTemporaryBeforeViewing(message: Message) {
        let settings = NagramiXMessageArchiveSettings.current
        let isViewOnce = message.flags.contains(.Incoming) && message.id.peerId.namespace == Namespaces.Peer.CloudUser && message.containsSecretMedia
        guard (settings.showDeletedMessages && settings.saveTemporaryMessages) || (settings.replayViewOnce && isViewOnce),
              message.attributes.contains(where: { $0 is AutoremoveTimeoutMessageAttribute || $0 is AutoclearTimeoutMessageAttribute }) else { return }
        let peers: [PeerId: Peer] = message.peers.reduce([:], { current, entry in
            var current = current
            current[entry.0] = entry.1
            return current
        })
        if let record = Self.makeRecord(message: message, peers: peers), record.temporary == true, record.messageId.peerId != self.accountPeerId {
            let replayCapture = record.viewOnceReplay == true
            if replayCapture && self.state.with({ $0.records[Self.key(record.messageId)]?.viewOnceReplay == true }) { return }
            if replayCapture {
                var inserted = false
                _ = self.replayCapturePending.modify { pending in
                    var pending = pending; inserted = pending.insert(record.messageId).inserted; return pending
                }
                guard inserted else { return }
            }
            let requests = self.mediaRequests(record)
            let ticket = self.mediaStore.reserve(key: Self.key(record.messageId), requests: requests)
            self.queue.async { [weak self] in
                guard let self else { return }
                defer {
                    if replayCapture { _ = self.replayCapturePending.modify { pending in var pending = pending; pending.remove(record.messageId); return pending } }
                }
                var updated = self.mutationState
                let key = Self.key(record.messageId)
                if updated.records[key] == nil { updated.records[key] = record }
                else if record.viewOnceReplay == true { updated.records[key]?.viewOnceReplay = true }
                self.persist(updated)
                self.mediaStore.retain(key: key, requests: requests, ticket: ticket)
            }
        }
    }

    /// Called immediately before Telegram replaces media with expired content.
    /// Existing approved copies remain archived even if capture is later disabled.
    public func archiveTemporaryExpiration(message: Message, expiredAt: Int32) {
        self.captureTemporaryBeforeViewing(message: message)
        self.markTemporaryExpired(id: message.id, expiredAt: expiredAt)
    }

    public func markTemporaryExpired(id: MessageId, expiredAt: Int32) {
        self.queue.async { [weak self] in
            guard let self else { return }
            var updated = self.mutationState
            let key = Self.key(id)
            guard var record = updated.records[key], record.temporary == true, record.deletedAt == nil else { return }
            record.deletedAt = expiredAt
            updated.records[key] = record
            self.persist(updated)
            self.publishUpdate()
        }
    }

    public func recordIncomingEdit(previousMessage: Message, replacementMessage: StoreMessage, peers: [PeerId: Peer], receivedAt: Int32) {
        let settings = NagramiXMessageArchiveSettings.current
        guard settings.showDeletedMessages || settings.messageEditHistory else {
            return
        }
        guard let previous = Self.makeRecord(message: previousMessage, peers: peers), let replacement = Self.makeRecord(message: replacementMessage, peers: peers), replacement.messageId.peerId != self.accountPeerId else {
            return
        }
        let requests = self.mediaRequests(replacement)
        let ticket = self.mediaStore.reserve(key: Self.key(replacement.messageId), requests: requests)
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            var updated = self.mutationState
            let key = Self.key(replacement.messageId)
            var current = updated.records[key] ?? previous
            guard current.content != replacement.content else {
                self.mediaStore.retain(key: key, requests: requests, ticket: ticket)
                return
            }
            if settings.messageEditHistory {
                let previousRevision = NagramiXMessageRevision(text: current.content.text, entities: current.content.entities, timestamp: current.contentTimestamp ?? current.timestamp)
                NagramiXMessageRevision.appendIfChanged(previousRevision, to: &current.revisions)
                // If capture was paused or sync skipped intermediate updates,
                // also retain the actual previous Postbox version we observed.
                NagramiXMessageRevision.appendIfChanged(NagramiXMessageRevision(text: previous.content.text, entities: previous.content.entities, timestamp: previous.contentTimestamp ?? previous.timestamp), to: &current.revisions)
            }
            current.content = replacement.content
            current.contentTimestamp = (replacementMessage.attributes.first(where: { $0 is EditedMessageAttribute }) as? EditedMessageAttribute).flatMap { $0.date > 0 ? $0.date : nil } ?? receivedAt
            current.peerData = replacement.peerData
            updated.records[key] = current
            self.persist(updated)
            self.mediaStore.retain(key: key, requests: requests, ticket: ticket)
            self.publishUpdate()
        }
    }

    public func archiveServerDeletion(upToMessageId id: MessageId, deletedAt: Int32) {
        self.queue.async { [weak self] in
            guard let self else { return }
            let ids = self.mutationState.records.values.filter { $0.messageId.peerId == id.peerId && $0.namespace == id.namespace && $0.id <= id.id }.map { $0.messageId }
            self.archiveServerDeletion(messageIds: ids, deletedAt: deletedAt)
        }
    }

    public func archiveServerDeletion(messageIds: [MessageId], deletedAt: Int32) {
        // A later switch-off pauses capture and hides the archive, but does not
        // discard content that was already saved with the user's approval.
        let keys = Set(messageIds.map { Self.key($0) })
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            var updated = self.mutationState
            var changed = false
            for key in keys {
                if var record = updated.records[key] {
                    // A server deletion moves a replay copy to the normal
                    // deleted-message archive, independent of the replay switch.
                    if record.deletedAt != nil && record.viewOnceReplay != true { continue }
                    if record.viewOnceReplay == true {
                        record.viewOnceReplay = nil
                        record.temporary = false
                    }
                    record.deletedAt = deletedAt
                    updated.records[key] = record
                    changed = true
                }
            }
            if changed {
                self.persist(updated)
                self.publishUpdate()
            }
        }
    }

    public func archiveServerDeletion(globalIds: [Int32], deletedAt: Int32) {
        let ids = Set(globalIds)
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            var updated = self.mutationState
            var changed = false
            let matchingKeys = updated.records.compactMap { key, record -> String? in
                if record.namespace == Namespaces.Message.Cloud && record.messageId.peerId.namespace != Namespaces.Peer.CloudChannel && ids.contains(record.id) {
                    return key
                } else {
                    return nil
                }
            }
            for key in matchingKeys {
                guard var record = updated.records[key] else {
                    continue
                }
                if record.deletedAt != nil && record.viewOnceReplay != true { continue }
                if record.viewOnceReplay == true {
                    record.viewOnceReplay = nil
                    record.temporary = false
                }
                record.deletedAt = deletedAt
                updated.records[key] = record
                changed = true
            }
            if changed {
                self.persist(updated)
                self.publishUpdate()
            }
        }
    }

    /// Reserve available media before native deletion. OFF never captures new content.
    public func archiveMessagesBeforeDeletion(_ messages: [Message], deletedAt: Int32) {
        let settings = NagramiXMessageArchiveSettings.current
        let ids = Set(messages.map { $0.id })
        var captured: [(NagramiXArchivedRecord, [NagramiXArchiveMediaRequest], Int64)] = []
        if settings.showDeletedMessages {
            for message in messages {
                let peers: [PeerId: Peer] = message.peers.reduce([:], { current, entry in
                    var current = current
                    current[entry.0] = entry.1
                    return current
                })
                guard let record = Self.makeRecord(message: message, peers: peers), record.messageId.peerId != self.accountPeerId else { continue }
                let requests = self.mediaRequests(record)
                let ticket = self.mediaStore.reserve(key: Self.key(record.messageId), requests: requests)
                captured.append((record, requests, ticket))
            }
        }
        self.queue.async { [weak self] in
            guard let self else { return }
            var updated = self.mutationState
            for (snapshot, _, _) in captured {
                let key = Self.key(snapshot.messageId)
                var record = snapshot
                if let current = updated.records[key] {
                    record.revisions = current.revisions
                    if record.content.media == current.content.media, record.transcriptionAttributes?.isEmpty != false {
                        record.transcriptionAttributes = current.transcriptionAttributes
                    }
                    if record.content == current.content {
                        record.contentTimestamp = max(current.contentTimestamp ?? current.timestamp, record.contentTimestamp ?? record.timestamp)
                    } else if settings.messageEditHistory {
                        NagramiXMessageRevision.appendIfChanged(NagramiXMessageRevision(text: current.content.text, entities: current.content.entities, timestamp: current.contentTimestamp ?? current.timestamp), to: &record.revisions)
                    }
                    record.deletedAt = current.deletedAt
                }
                updated.records[key] = record
            }
            for id in ids {
                let key = Self.key(id)
                guard var record = updated.records[key] else { continue }
                if record.viewOnceReplay == true {
                    record.viewOnceReplay = nil
                    record.temporary = false
                }
                if record.deletedAt == nil { record.deletedAt = deletedAt }
                updated.records[key] = record
            }
            if updated != self.mutationState {
                self.persist(updated)
                self.publishUpdate()
            }
            for (record, requests, ticket) in captured {
                let key = Self.key(record.messageId)
                self.mediaStore.retain(key: key, requests: updated.records[key].map(self.mediaRequests) ?? requests, ticket: ticket)
            }
        }
    }

    public func archiveHistoryBeforeDeletion(transaction: Transaction, peerId: PeerId, threadId: Int64?, minTimestamp: Int32?, maxTimestamp: Int32?, namespaces: MessageIdNamespaces) {
        guard namespaces.contains(Namespaces.Message.Cloud), peerId.namespace != Namespaces.Peer.SecretChat else { return }
        let deletedAt = Int32(Date().timeIntervalSince1970)
        if NagramiXMessageArchiveSettings.current.showDeletedMessages {
            var messages: [Message] = []
            transaction.withAllMessages(peerId: peerId, namespace: Namespaces.Message.Cloud, { message in
                if (threadId == nil || message.threadId == threadId)
                    && (minTimestamp == nil || message.timestamp >= minTimestamp!)
                    && (maxTimestamp == nil || message.timestamp <= maxTimestamp!) {
                    messages.append(message)
                }
                return true
            })
            self.archiveMessagesBeforeDeletion(messages, deletedAt: deletedAt)
        }
        self.archiveHistoryDeletion(peerId: peerId, threadId: threadId, minTimestamp: minTimestamp, maxTimestamp: maxTimestamp, deletedAt: deletedAt)
    }

    public func archiveMessageRangeBeforeDeletion(transaction: Transaction, peerId: PeerId, namespace: MessageId.Namespace, minId: Int32, maxId: Int32, deletedAt: Int32) {
        guard NagramiXMessageArchiveSettings.current.showDeletedMessages, namespace == Namespaces.Message.Cloud else { return }
        var messages: [Message] = []
        transaction.withAllMessages(peerId: peerId, namespace: namespace, { message in
            if message.id.id >= minId && message.id.id <= maxId { messages.append(message) }
            return true
        })
        self.archiveMessagesBeforeDeletion(messages, deletedAt: deletedAt)
    }

    private func archiveHistoryDeletion(peerId: PeerId, threadId: Int64?, minTimestamp: Int32?, maxTimestamp: Int32?, deletedAt: Int32) {
        self.queue.async { [weak self] in
            guard let self else { return }
            let ids = self.mutationState.records.values.filter { record in
                record.messageId.peerId == peerId && record.namespace == Namespaces.Message.Cloud
                    && (threadId == nil || record.threadId == threadId)
                    && (minTimestamp == nil || record.timestamp >= minTimestamp!)
                    && (maxTimestamp == nil || record.timestamp <= maxTimestamp!)
            }.map { $0.messageId }
            self.archiveServerDeletion(messageIds: ids, deletedAt: deletedAt)
        }
    }

    public func removeLocal(messageIds: [MessageId]) {
        // Individual deletion never purges an approved archive snapshot.
        self.archiveServerDeletion(messageIds: messageIds, deletedAt: Int32(Date().timeIntervalSince1970))
    }

    public func clear(peerId: PeerId) {
        // Keep this compatibility entry non-destructive. Only clearAll purges data.
        self.archiveHistoryDeletion(peerId: peerId, threadId: nil, minTimestamp: nil, maxTimestamp: nil, deletedAt: Int32(Date().timeIntervalSince1970))
    }

    public func clearAll() {
        let ticket = self.mediaStore.barrier()
        self.queue.async { [weak self] in
            guard let self else { return }
            for key in self.mutationState.records.keys { self.removalTickets[key] = ticket }
            self.clearTicket = ticket
            // A durable empty snapshot is the deletion tombstone. Keep the
            // previous JSON and media on failure; clear bytes only after commit.
            self.loadBlocked = false // explicit user-requested full reset
            self.persist(NagramiXMessageArchiveState(), retryNow: true)
            self.publishUpdate()
        }
    }

    public func revisions(messageId: MessageId, currentText: String? = nil, currentEntities: [MessageTextEntity]? = nil) -> [NagramiXMessageRevision] {
        guard NagramiXMessageArchiveSettings.current.messageEditHistory else {
            return []
        }
        guard let record = self.state.with({ $0.records[Self.key(messageId)] }) else {
            return []
        }
        var result = record.revisions
        let text = currentText ?? record.content.text
        let entities = currentEntities ?? record.content.entities
        let current = NagramiXMessageRevision(text: text, entities: entities, timestamp: record.contentTimestamp ?? record.timestamp)
        NagramiXMessageRevision.appendIfChanged(current, to: &result)
        return result.count > 1 ? result : []
    }

    /// Обработчики выделения должны получать тот же объект, который виден в ленте,
    /// когда вместо истёкшей записи Postbox показано сохранённое вложение.
    /// Resolve an incoming one-time message to a completed local copy for
    /// explicit copy actions; never turn the original into a server forward.
    public func replayCopyForInteraction(id: MessageId, liveMessage: Message?) -> Message? {
        guard NagramiXMessageArchiveSettings.current.replayViewOnce,
              let liveMessage, liveMessage.id == id, liveMessage.flags.contains(.Incoming),
              liveMessage.containsSecretMedia,
              let record = self.state.with({ $0.records[Self.key(id)] }), record.viewOnceReplay == true else { return nil }
        return self.renderDeletedRecord(record)
    }

    public func interactionMessage(id: MessageId, liveMessage: Message?) -> Message? {
        if let liveMessage, !liveMessage.media.contains(where: { $0 is TelegramMediaExpiredContent }) {
            return liveMessage.id == id ? liveMessage : nil
        }
        let retained = self.deletedMessage(id: id) ?? (liveMessage == nil ? nil : self.snapshotForExpiredMessage(id: id))
        return Self.interactionMessage(id: id, liveMessage: liveMessage, retainedMessage: retained)
    }

    public static func interactionMessage(id: MessageId, liveMessage: Message?, retainedMessage: Message?) -> Message? {
        guard liveMessage == nil || liveMessage?.id == id else { return nil }
        if let liveMessage, !liveMessage.media.contains(where: { $0 is TelegramMediaExpiredContent }) { return liveMessage }
        if let retainedMessage, retainedMessage.id == id,
           retainedMessage.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) {
            return retainedMessage
        }
        return liveMessage
    }

    /// Read-only resolution for ASR. Unlike opening an expired row, this must
    /// not mark it expired, consume it, capture new bytes or change its lifetime.
    public func transcriptionMessage(id: MessageId, liveMessage: Message?) -> Message? {
        guard liveMessage == nil || liveMessage?.id == id else { return nil }
        if let liveMessage, !liveMessage.media.contains(where: { $0 is TelegramMediaExpiredContent }) { return liveMessage }
        guard let record = self.state.with({ $0.records[Self.key(id)] }),
              record.deletedAt != nil || (liveMessage != nil && record.temporary == true) else { return liveMessage }
        return self.renderDeletedRecord(record) ?? liveMessage
    }

    /// Store only ASR attributes on an already retained, visible temporary voice.
    /// All archive mutations (including clearAll) share this serial queue. A late
    /// recognizer can neither recreate a cleared record nor insert into Postbox.
    public func updateTranscriptionAttributes(id: MessageId, transform: @escaping (Message) -> [MessageAttribute]?) -> Signal<Bool, NoError> {
        return Signal { subscriber in
            self.queue.async {
                var updated = self.mutationState
                let key = Self.key(id)
                guard var record = updated.records[key],
                      let current = self.renderDeletedRecord(record), nagramiXCanPlayTemporaryVoiceInline(current),
                      let attributes = transform(current) else {
                    subscriber.putNext(false); subscriber.putCompletion(); return
                }
                record.transcriptionAttributes = attributes.filter {
                    $0 is AudioTranscriptionMessageAttribute || $0 is DerivedDataMessageAttribute
                }.map(Self.encodedRootObject)
                updated.records[key] = record
                let saved = self.persist(updated)
                if saved { self.publishUpdate() }
                subscriber.putNext(saved); subscriber.putCompletion()
            }
            return EmptyDisposable
        }
    }

    public func deletedMessage(id: MessageId) -> Message? {
        let settings = NagramiXMessageArchiveSettings.current
        guard let record = self.state.with({ $0.records[Self.key(id)] }), record.deletedAt != nil,
              settings.showDeletedMessages || (settings.replayViewOnce && record.viewOnceReplay == true) else { return nil }
        return self.renderDeletedRecord(record)
    }

    public func snapshotForExpiredMessage(id: MessageId) -> Message? {
        let settings = NagramiXMessageArchiveSettings.current
        guard let record = self.state.with({ $0.records[Self.key(id)] }), record.temporary == true,
              (settings.showDeletedMessages && settings.saveTemporaryMessages) || (settings.replayViewOnce && record.viewOnceReplay == true) else { return nil }
        self.markTemporaryExpired(id: id, expiredAt: Int32(Date().timeIntervalSince1970))
        return self.renderDeletedRecord(record)
    }

    public func containsArchivedMessage(id: MessageId) -> Bool {
        let settings = NagramiXMessageArchiveSettings.current
        guard settings.showDeletedMessages else { return false }
        return self.state.with { state in
            guard let record = state.records[Self.key(id)], record.temporary != true || settings.saveTemporaryMessages else { return false }
            return record.deletedAt != nil || record.temporary == true
        }
    }

    /// Deletion ownership must survive switching archive visibility off while a
    /// confirmation or undo is open. Unexpired/live temporary messages stay native.
    public func isLocallyDeletedMessage(id: MessageId) -> Bool {
        return self.state.with { $0.records[Self.key(id)]?.deletedAt != nil }
    }

    public func updateDeletedMessageText(id: MessageId, text: String) {
        self.queue.async { [weak self] in
            guard let self else { return }
            var updated = self.mutationState
            let key = Self.key(id)
            guard var record = updated.records[key], record.deletedAt != nil,
                  text != record.content.text, !text.isEmpty || !record.content.media.isEmpty else { return }
            let timestamp = Int32(Date().timeIntervalSince1970)
            NagramiXMessageRevision.appendIfChanged(NagramiXMessageRevision(text: record.content.text, entities: record.content.entities, timestamp: record.contentTimestamp ?? record.timestamp), to: &record.revisions)
            // Plain-text local editing must not retain invalid entity offsets.
            record.content = NagramiXArchivedContent(text: text, entities: [], media: record.content.media)
            record.contentTimestamp = timestamp
            updated.records[key] = record
            self.persist(updated, retryNow: true)
            self.publishUpdate()
        }
    }

    public func deletedMessages(peerId: PeerId, threadId: Int64?, minIndex: MessageIndex?, maxIndex: MessageIndex?, limit: Int = 200) -> [Message] {
        let settings = NagramiXMessageArchiveSettings.current
        guard settings.showDeletedMessages || settings.replayViewOnce else {
            return []
        }
        let rawPeerId = peerId.toInt64()
        let records = self.state.with { state -> [NagramiXArchivedRecord] in
            state.records.values.filter { record in
                let visibleInArchive = settings.showDeletedMessages && (record.temporary != true || settings.saveTemporaryMessages)
                let visibleForReplay = settings.replayViewOnce && record.viewOnceReplay == true
                guard record.peerId == rawPeerId && record.deletedAt != nil && (threadId == nil || record.threadId == threadId), visibleInArchive || visibleForReplay else {
                    return false
                }
                let index = MessageIndex(id: record.messageId, timestamp: record.timestamp)
                if let minIndex, index < minIndex {
                    return false
                }
                if let maxIndex, index > maxIndex {
                    return false
                }
                return true
            }
            .sorted(by: { MessageIndex(id: $0.messageId, timestamp: $0.timestamp) < MessageIndex(id: $1.messageId, timestamp: $1.timestamp) })
            .suffix(max(1, limit))
            .map { $0 }
        }
        return records.compactMap { self.renderDeletedRecord($0) }.sorted(by: { $0.index < $1.index })
    }

    private func renderDeletedRecord(_ record: NagramiXArchivedRecord) -> Message? {
        let settings = NagramiXMessageArchiveSettings.current
        let visibleInArchive = settings.showDeletedMessages && (record.temporary != true || settings.saveTemporaryMessages)
        let visibleForReplay = settings.replayViewOnce && record.viewOnceReplay == true
        guard visibleInArchive || visibleForReplay else { return nil }
        var peers: [PeerId: Peer] = [:]
        for (_, data) in record.peerData {
            if let peer = Self.decodedRootObject(data) as? Peer {
                peers[peer.id] = peer
            }
        }
        let media = record.content.media.compactMap { Self.decodedRootObject($0) as? Media }.map(self.localMedia)
        // A retained view-once row must not claim to be replayable until all
        // primary bytes are available in the independent local store.
        if visibleForReplay {
            guard !media.isEmpty && media.allSatisfy({ item in
                if let file = item as? TelegramMediaFile { return file.resource is LocalFileReferenceMediaResource }
                if let image = item as? TelegramMediaImage {
                    return image.representations.max(by: { Int64($0.dimensions.width) * Int64($0.dimensions.height) < Int64($1.dimensions.width) * Int64($1.dimensions.height) })?.resource is LocalFileReferenceMediaResource
                }
                return false
            }) else { return nil }
        }
        var attributes: [MessageAttribute] = (record.transcriptionAttributes ?? []).compactMap {
            let attribute = Self.decodedRootObject($0)
            guard attribute is AudioTranscriptionMessageAttribute || attribute is DerivedDataMessageAttribute else { return nil }
            return attribute as? MessageAttribute
        }
        if !record.content.entities.isEmpty {
            attributes.append(TextEntitiesMessageAttribute(entities: record.content.entities))
        }
        attributes.append(NagramiXArchivedMessageAttribute(deletedAt: record.deletedAt ?? record.timestamp, revisions: record.revisions, isTemporary: record.temporary == true, isViewOnceReplay: visibleForReplay))
        let flags: StoreMessageFlags = record.incoming ? [.Incoming] : []
        // Classify the retained media with the same tags as a native message.
        // Expiry attributes belong to the consumed original, not this local copy.
        let (tags, globalTags) = tagsForStoreMessage(incoming: record.incoming, attributes: attributes, media: media, textEntities: record.content.entities, isPinned: false)
        let storeMessage = StoreMessage(
            id: .Id(record.messageId),
            customStableId: nil,
            globallyUniqueId: nil,
            groupingKey: record.groupingKey,
            threadId: record.threadId,
            timestamp: record.timestamp,
            flags: flags,
            tags: tags,
            globalTags: globalTags,
            localTags: [],
            forwardInfo: nil,
            authorId: record.authorId.map { PeerId($0) },
            text: record.content.text,
            attributes: attributes,
            media: media
        )
        return locallyRenderedMessage(message: storeMessage, peers: peers)?.withUpdatedStableVersion(stableVersion: UInt32(clamping: record.revisions.count) &+ self.renderVersion.with { $0 })
    }
}
