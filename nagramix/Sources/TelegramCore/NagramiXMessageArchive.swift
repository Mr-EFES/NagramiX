import Foundation
import Postbox
import SwiftSignalKit

/// The archive lives in TelegramCore, below the NagramiXCore presentation
/// module in the Bazel dependency graph. Read the two persisted switches from
/// the same UserDefaults keys used by NagramiXTabSettings without introducing
/// a TelegramCore -> NagramiXCore dependency cycle.
private struct NagramiXMessageArchiveSettings {
    static let changedNotification = Notification.Name("NagramiXSettingsChanged")

    let showDeletedMessages: Bool
    let messageEditHistory: Bool

    static var current: NagramiXMessageArchiveSettings {
        let defaults = UserDefaults.standard
        return NagramiXMessageArchiveSettings(
            showDeletedMessages: defaults.object(forKey: "nagramix.messages.showDeletedMessages") as? Bool ?? false,
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
    private let path: String
    private let queue: Queue
    private let state = Atomic<NagramiXMessageArchiveState>(value: NagramiXMessageArchiveState())
    private let revisionValue = ValuePromise<Int>(0, ignoreRepeated: false)
    private var revision: Int = 0
    private var settingsObserver: NSObjectProtocol?

    public var updates: Signal<Int, NoError> {
        return self.revisionValue.get()
    }

    public init(postbox: Postbox, accountPeerId: PeerId, basePath: String) {
        self.postbox = postbox
        self.accountPeerId = accountPeerId
        self.path = basePath + "/nagramix-message-archive.json"
        self.queue = Queue(name: "org.nagramix.message-archive", qos: .utility)

        Self.registry.modify { value in
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
            self.publishUpdate()
        }

        self.settingsObserver = NotificationCenter.default.addObserver(forName: NagramiXMessageArchiveSettings.changedNotification, object: nil, queue: nil, using: { [weak self] _ in
            self?.queue.async {
                self?.publishUpdate()
            }
        })
    }

    deinit {
        if let settingsObserver = self.settingsObserver {
            NotificationCenter.default.removeObserver(settingsObserver)
        }
        Self.registry.modify { value in
            var value = value
            value.removeValue(forKey: ObjectIdentifier(self.postbox))
            return value
        }
    }

    private func publishUpdate() {
        self.revision += 1
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
        guard !message.flags.contains(.CopyProtected) else {
            return nil
        }
        guard !message.attributes.contains(where: {
            $0 is AutoremoveTimeoutMessageAttribute
                || $0 is AutoclearTimeoutMessageAttribute
                || $0 is EphemeralMessageAttribute
                || $0 is EphemeralOutgoingMessageAttribute
        }) else {
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
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            var updated = self.state.with { $0 }
            let key = Self.key(replacement.messageId)
            var current = updated.records[key] ?? previous
            guard current.content != replacement.content else {
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
            self.publishUpdate()
        }
    }

    public func archiveServerDeletion(messageIds: [MessageId], deletedAt: Int32) {
        let settings = NagramiXMessageArchiveSettings.current
        guard settings.showDeletedMessages || settings.messageEditHistory else {
            return
        }
        let preserveDeletedMessage = settings.showDeletedMessages
        let keys = Set(messageIds.map { Self.key($0) })
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            var updated = self.state.with { $0 }
            var changed = false
            for key in keys {
                if var record = updated.records[key] {
                    if preserveDeletedMessage {
                        if record.deletedAt != nil {
                            continue
                        }
                        record.deletedAt = deletedAt
                        updated.records[key] = record
                    } else {
                        updated.records.removeValue(forKey: key)
                    }
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
        let settings = NagramiXMessageArchiveSettings.current
        guard settings.showDeletedMessages || settings.messageEditHistory else {
            return
        }
        let preserveDeletedMessage = settings.showDeletedMessages
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
                if preserveDeletedMessage {
                    if record.deletedAt != nil {
                        continue
                    }
                    record.deletedAt = deletedAt
                    updated.records[key] = record
                } else {
                    updated.records.removeValue(forKey: key)
                }
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
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            var updated = self.state.with { $0 }
            let oldCount = updated.records.count
            updated.records = updated.records.filter { !keys.contains($0.key) }
            if updated.records.count != oldCount {
                _ = self.state.swap(updated)
                self.persist(updated)
                self.publishUpdate()
            }
        }
    }

    public func clear(peerId: PeerId) {
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            var updated = self.state.with { $0 }
            let rawPeerId = peerId.toInt64()
            updated.records = updated.records.filter { $0.value.peerId != rawPeerId }
            _ = self.state.swap(updated)
            self.persist(updated)
            self.publishUpdate()
        }
    }

    public func clearAll() {
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            let updated = NagramiXMessageArchiveState()
            _ = self.state.swap(updated)
            try? FileManager.default.removeItem(atPath: self.path)
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
        return records.compactMap { record -> Message? in
            var peers: [PeerId: Peer] = [:]
            for (_, data) in record.peerData {
                if let peer = Self.decodedRootObject(data) as? Peer {
                    peers[peer.id] = peer
                }
            }
            let media = record.content.media.compactMap { Self.decodedRootObject($0) as? Media }
            var attributes: [MessageAttribute] = []
            if !record.content.entities.isEmpty {
                attributes.append(TextEntitiesMessageAttribute(entities: record.content.entities))
            }
            attributes.append(NagramiXArchivedMessageAttribute(deletedAt: record.deletedAt ?? record.timestamp, revisions: record.revisions))
            let flags: StoreMessageFlags = [.Incoming]
            let storeMessage = StoreMessage(
                id: .Id(record.messageId),
                customStableId: nil,
                globallyUniqueId: nil,
                groupingKey: record.groupingKey,
                threadId: record.threadId,
                timestamp: record.timestamp,
                flags: flags,
                tags: [],
                globalTags: [],
                localTags: [],
                forwardInfo: nil,
                authorId: record.authorId.map { PeerId($0) },
                text: record.content.text,
                attributes: attributes,
                media: media
            )
            return locallyRenderedMessage(message: storeMessage, peers: peers)
        }.sorted(by: { $0.index < $1.index })
    }
}
