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
    let messageEditHistory: Bool

    static var current: NagramiXMessageArchiveSettings {
        let defaults = UserDefaults.standard
        return NagramiXMessageArchiveSettings(
            showDeletedMessages: defaults.object(forKey: "nagramix.messages.showDeletedMessages") as? Bool ?? false,
            saveTemporaryMessages: defaults.object(forKey: "nagramix.messages.saveTemporaryMessages") as? Bool ?? false,
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
}

/// Marks a synthetic, display-only message supplied by NagramiXMessageArchive.
/// These messages never enter Postbox and must not be used for server actions.
public final class NagramiXArchivedMessageAttribute: MessageAttribute {
    public let deletedAt: Int32
    public let revisions: [NagramiXMessageRevision]

    public init(deletedAt: Int32, revisions: [NagramiXMessageRevision]) {
        self.deletedAt = deletedAt
        self.revisions = revisions
    }

    public required init(decoder: PostboxDecoder) {
        self.deletedAt = decoder.decodeInt32ForKey("d", orElse: 0)
        self.revisions = []
    }

    public func encode(_ encoder: PostboxEncoder) {
        encoder.encodeInt32(self.deletedAt, forKey: "d")
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
    var peerData: [String: Data]
    var content: NagramiXArchivedContent
    var contentTimestamp: Int32?
    var revisions: [NagramiXMessageRevision]
    var deletedAt: Int32?

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

    private let postbox: Postbox
    private let accountPeerId: PeerId
    public let deferredReactions: NagramiXDeferredReactionsStore
    private let path: String
    private let basePath: String
    private let queue: Queue
    private let state = Atomic<NagramiXMessageArchiveState>(value: NagramiXMessageArchiveState())
    private let revisionValue = ValuePromise<Int>(0, ignoreRepeated: false)
    private var revision: Int = 0
    private var settingsObserver: NSObjectProtocol?
    private var lifecycleObservers: [NSObjectProtocol] = []
    private var readyForMediaDownloads = false
    private var inForeground = true
    private var mediaDownloadSettings: (Bool, Bool)?
    private let renderVersion = Atomic<UInt32>(value: 0)
    private lazy var mediaStore = NagramiXArchivedMediaStore(mediaBox: self.postbox.mediaBox, queue: self.queue, basePath: self.basePath, changed: { [weak self] in
        self?.publishUpdate()
    })

    public var updates: Signal<Int, NoError> {
        return self.revisionValue.get()
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
            if let data = try? Data(contentsOf: URL(fileURLWithPath: self.path)), let loaded = try? JSONDecoder().decode(NagramiXMessageArchiveState.self, from: data) {
                _ = self.state.swap(loaded)
            }
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
        if let current = self.mediaDownloadSettings, current.0 == enabled, current.1 == temporary { return }
        self.mediaDownloadSettings = (enabled, temporary)
        self.mediaStore.configure(enabled: enabled, temporaryEnabled: temporary)
    }

    public func cacheResourcesToRemove(_ ids: [MediaResourceId]) -> [MediaResourceId] {
        let settings = NagramiXMessageArchiveSettings.current
        guard settings.showDeletedMessages else { return ids }
        return self.mediaStore.resourcesToRemove(ids, includeTemporary: settings.saveTemporaryMessages)
    }

    private func publishUpdate() {
        self.revision += 1
        _ = self.renderVersion.modify { $0 &+ 1 }
        self.revisionValue.set(self.revision)
    }

    private func persist(_ state: NagramiXMessageArchiveState) {
        guard let data = try? JSONEncoder().encode(state) else {
            return
        }
        try? data.write(to: URL(fileURLWithPath: self.path), options: [.atomic])
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
                result.append(NagramiXArchiveMediaRequest(reference: mediaReference.resourceReference(resource), temporary: record.temporary == true, primary: primary))
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
        guard message.flags.contains(.Incoming) else {
            return nil
        }
        let temporary = message.attributes.contains(where: { $0 is AutoremoveTimeoutMessageAttribute || $0 is AutoclearTimeoutMessageAttribute })
        guard !message.flags.contains(.CopyProtected) || (temporary && NagramiXMessageArchiveSettings.current.saveTemporaryMessages) else {
            return nil
        }
        guard !temporary || NagramiXMessageArchiveSettings.current.saveTemporaryMessages else { return nil }
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
            incoming: true,
            temporary: temporary,
            peerData: peerData,
            content: NagramiXArchivedContent(text: message.text, entities: entities, media: media),
            contentTimestamp: message.timestamp,
            revisions: [],
            deletedAt: nil
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

    public func captureIncoming(_ message: StoreMessage, peers: [PeerId: Peer]) {
        if message.media.contains(where: { $0 is TelegramMediaExpiredContent }), case let .Id(id) = message.id {
            self.markTemporaryExpired(id: id, expiredAt: Int32(Date().timeIntervalSince1970))
            return
        }
        let settings = NagramiXMessageArchiveSettings.current
        // Edit history captures the real previous Message immediately before an edit is
        // applied. Keeping every incoming message on disk is only necessary when a
        // later server-side deletion may need to be rendered locally.
        guard settings.showDeletedMessages else {
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
            var updated = self.state.with { $0 }
            let key = Self.key(record.messageId)
            if let current = updated.records[key] {
                var record = record
                record.revisions = current.revisions
                record.deletedAt = current.deletedAt
                updated.records[key] = record
            } else {
                updated.records[key] = record
            }
            _ = self.state.swap(updated)
            self.persist(updated)
            self.mediaStore.retain(key: key, requests: requests, ticket: ticket)
        }
    }

    /// Also covers existing attachments when the switch was enabled after receipt.
    /// Capturing bytes does not itself consume the message or start its timer.
    public func captureTemporaryBeforeViewing(message: Message) {
        let settings = NagramiXMessageArchiveSettings.current
        guard settings.showDeletedMessages && settings.saveTemporaryMessages,
              message.attributes.contains(where: { $0 is AutoremoveTimeoutMessageAttribute || $0 is AutoclearTimeoutMessageAttribute }) else { return }
        let peers: [PeerId: Peer] = message.peers.reduce([:], { current, entry in
            var current = current
            current[entry.0] = entry.1
            return current
        })
        if let record = Self.makeRecord(message: message, peers: peers), record.temporary == true, record.messageId.peerId != self.accountPeerId {
            let requests = self.mediaRequests(record)
            let ticket = self.mediaStore.reserve(key: Self.key(record.messageId), requests: requests)
            self.queue.async { [weak self] in
                guard let self else { return }
                var updated = self.state.with { $0 }
                let key = Self.key(record.messageId)
                if updated.records[key] == nil { updated.records[key] = record }
                _ = self.state.swap(updated)
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
            var updated = self.state.with { $0 }
            let key = Self.key(id)
            guard var record = updated.records[key], record.temporary == true, record.deletedAt == nil else { return }
            record.deletedAt = expiredAt
            updated.records[key] = record
            _ = self.state.swap(updated)
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
            var updated = self.state.with { $0 }
            let key = Self.key(replacement.messageId)
            var current = updated.records[key] ?? previous
            guard current.content != replacement.content else {
                self.mediaStore.retain(key: key, requests: requests, ticket: ticket)
                return
            }
            if settings.messageEditHistory {
                let previousRevision = NagramiXMessageRevision(text: current.content.text, entities: current.content.entities, timestamp: current.contentTimestamp ?? current.timestamp)
                if current.revisions.last != previousRevision {
                    current.revisions.append(previousRevision)
                }
            }
            current.content = replacement.content
            current.contentTimestamp = receivedAt
            current.peerData = replacement.peerData
            current.deletedAt = nil
            updated.records[key] = current
            _ = self.state.swap(updated)
            self.persist(updated)
            self.mediaStore.retain(key: key, requests: requests, ticket: ticket)
            self.publishUpdate()
        }
    }

    public func archiveServerDeletion(upToMessageId id: MessageId, deletedAt: Int32) {
        self.queue.async { [weak self] in
            guard let self else { return }
            let ids = self.state.with { state in
                state.records.values.filter { $0.messageId.peerId == id.peerId && $0.namespace == id.namespace && $0.id <= id.id }.map { $0.messageId }
            }
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
            var updated = self.state.with { $0 }
            var changed = false
            for key in keys {
                if var record = updated.records[key] {
                    if record.deletedAt != nil {
                        continue
                    }
                    record.deletedAt = deletedAt
                    updated.records[key] = record
                    changed = true
                }
            }
            if changed {
                _ = self.state.swap(updated)
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
            var updated = self.state.with { $0 }
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
                if record.deletedAt != nil {
                    continue
                }
                record.deletedAt = deletedAt
                updated.records[key] = record
                changed = true
            }
            if changed {
                _ = self.state.swap(updated)
                self.persist(updated)
                self.publishUpdate()
            }
        }
    }

    public func removeLocal(messageIds: [MessageId]) {
        let keys = Set(messageIds.map { Self.key($0) })
        let ticket = self.mediaStore.barrier()
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            var updated = self.state.with { $0 }
            let oldCount = updated.records.count
            updated.records = updated.records.filter { !keys.contains($0.key) }
            self.mediaStore.remove(keys: keys, before: ticket)
            if updated.records.count != oldCount {
                _ = self.state.swap(updated)
                self.persist(updated)
                self.publishUpdate()
            }
        }
    }

    public func clear(peerId: PeerId) {
        let ticket = self.mediaStore.barrier()
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            var updated = self.state.with { $0 }
            let rawPeerId = peerId.toInt64()
            let keys = Set(updated.records.filter { $0.value.peerId == rawPeerId }.keys)
            updated.records = updated.records.filter { $0.value.peerId != rawPeerId }
            self.mediaStore.remove(keys: keys, before: ticket)
            _ = self.state.swap(updated)
            self.persist(updated)
            self.publishUpdate()
        }
    }

    public func clearAll() {
        let ticket = self.mediaStore.barrier(clearFiles: true)
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            let updated = NagramiXMessageArchiveState()
            _ = self.state.swap(updated)
            try? FileManager.default.removeItem(atPath: self.path)
            self.mediaStore.clear(before: ticket)
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
        if result.last?.text != current.text || result.last?.entities != current.entities {
            result.append(current)
        }
        return result.count > 1 ? result : []
    }

    public func deletedMessage(id: MessageId) -> Message? {
        guard NagramiXMessageArchiveSettings.current.showDeletedMessages,
              let record = self.state.with({ $0.records[Self.key(id)] }), record.deletedAt != nil else { return nil }
        return self.renderDeletedRecord(record)
    }

    public func snapshotForExpiredMessage(id: MessageId) -> Message? {
        guard NagramiXMessageArchiveSettings.current.showDeletedMessages,
              let record = self.state.with({ $0.records[Self.key(id)] }), record.temporary == true else { return nil }
        self.markTemporaryExpired(id: id, expiredAt: Int32(Date().timeIntervalSince1970))
        return self.renderDeletedRecord(record)
    }

    public func containsArchivedMessage(id: MessageId) -> Bool {
        guard NagramiXMessageArchiveSettings.current.showDeletedMessages else { return false }
        return self.state.with { state in
            guard let record = state.records[Self.key(id)] else { return false }
            return record.deletedAt != nil || record.temporary == true
        }
    }

    public func updateDeletedMessageText(id: MessageId, text: String) {
        self.queue.async { [weak self] in
            guard let self else { return }
            var updated = self.state.with { $0 }
            let key = Self.key(id)
            guard var record = updated.records[key], record.deletedAt != nil,
                  text != record.content.text, !text.isEmpty || !record.content.media.isEmpty else { return }
            let timestamp = Int32(Date().timeIntervalSince1970)
            record.revisions.append(NagramiXMessageRevision(text: record.content.text, entities: record.content.entities, timestamp: record.contentTimestamp ?? record.timestamp))
            // Plain-text local editing must not retain invalid entity offsets.
            record.content = NagramiXArchivedContent(text: text, entities: [], media: record.content.media)
            record.contentTimestamp = timestamp
            updated.records[key] = record
            _ = self.state.swap(updated)
            self.persist(updated)
            self.publishUpdate()
        }
    }

    public func deletedMessages(peerId: PeerId, threadId: Int64?, minIndex: MessageIndex?, maxIndex: MessageIndex?, limit: Int = 200) -> [Message] {
        guard NagramiXMessageArchiveSettings.current.showDeletedMessages else {
            return []
        }
        let rawPeerId = peerId.toInt64()
        let records = self.state.with { state -> [NagramiXArchivedRecord] in
            state.records.values.filter { record in
                guard record.peerId == rawPeerId && record.deletedAt != nil && (threadId == nil || record.threadId == threadId) else {
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
        var peers: [PeerId: Peer] = [:]
        for (_, data) in record.peerData {
            if let peer = Self.decodedRootObject(data) as? Peer {
                peers[peer.id] = peer
            }
        }
        let media = record.content.media.compactMap { Self.decodedRootObject($0) as? Media }.map(self.localMedia)
        var attributes: [MessageAttribute] = []
        if !record.content.entities.isEmpty {
            attributes.append(TextEntitiesMessageAttribute(entities: record.content.entities))
        }
        attributes.append(NagramiXArchivedMessageAttribute(deletedAt: record.deletedAt ?? record.timestamp, revisions: record.revisions))
        let flags: StoreMessageFlags = [.Incoming]
        // Classify the retained media with the same tags as a native message.
        // Expiry attributes belong to the consumed original, not this local copy.
        let (tags, globalTags) = tagsForStoreMessage(incoming: true, attributes: attributes, media: media, textEntities: record.content.entities, isPinned: false)
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
