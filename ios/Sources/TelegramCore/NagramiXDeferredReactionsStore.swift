import Foundation
import Postbox
import SwiftSignalKit

private struct NagramiXDeferredReaction: Codable {
    let emoji: String?
    let fileId: Int64?
    let file: Data?

    var value: UpdateMessageReaction? {
        if let emoji { return .builtin(emoji) }
        if let fileId {
            let media = self.file.flatMap { PostboxDecoder(buffer: MemoryBuffer(data: $0)).decodeRootObject() as? TelegramMediaFile }
            return .custom(fileId: fileId, file: media)
        }
        return nil
    }
}

private struct NagramiXDeferredReactionRecord: Codable {
    let peerId: Int64
    let namespace: Int32
    let id: Int32
    let threadId: Int64?
    let reactions: [NagramiXDeferredReaction]
    let isLarge: Bool
    let storeAsRecentlyUsed: Bool
    let isTags: Bool
    let sendAsPeerId: Int64?
    let revision: UInt32

    var messageId: MessageId {
        return MessageId(peerId: PeerId(self.peerId), namespace: self.namespace, id: self.id)
    }
}

// Independent of the deleted-message archive and Telegram's pending-action table.
// A preview never writes PendingReactionsMessageAttribute into Postbox.
public final class NagramiXDeferredReactionsStore {
    private let accountPeerId: PeerId
    private let path: URL
    private let queue = Queue(name: "org.nagramix.deferred-reactions", qos: .utility)
    private let lock = NSLock()
    private var records: [String: NagramiXDeferredReactionRecord] = [:]
    private var inFlight: Set<String> = []
    private var loaded = false
    private var dismissedBeforeLoad: Set<String> = []
    private var revision: UInt32 = 0
    private let changed = ValuePromise<Int>(0, ignoreRepeated: false)

    public var updates: Signal<Int, NoError> { return self.changed.get() }

    public init(accountPeerId: PeerId, basePath: String) {
        self.accountPeerId = accountPeerId
        self.path = URL(fileURLWithPath: basePath + "/nagramix-deferred-reactions.json")
        // Load on the utility queue; subscribers receive a second render when ready.
        self.queue.async { [weak self] in
            guard let self else { return }
            let loaded = (try? Data(contentsOf: self.path)).flatMap {
                try? JSONDecoder().decode([String: NagramiXDeferredReactionRecord].self, from: $0)
            } ?? [:]
            self.lock.lock()
            // A new tap wins over the saved value if startup loading overlaps it.
            for (key, record) in loaded where self.records[key] == nil && !self.dismissedBeforeLoad.contains(key) {
                if key == Self.key(record.messageId), record.namespace == Namespaces.Message.Cloud,
                   record.reactions.allSatisfy({ $0.value != nil }) {
                    self.records[key] = record
                }
            }
            self.revision = self.records.values.map(\.revision).max() ?? 0
            self.loaded = true
            self.dismissedBeforeLoad.removeAll()
            let revision = self.revision
            self.lock.unlock()
            self.changed.set(Int(revision))
        }
    }

    private static func key(_ id: MessageId) -> String {
        return "\(id.peerId.toInt64()):\(id.namespace):\(id.id)"
    }

    // Persistence is serialized, atomic, and off the UI thread. Read the current
    // snapshot at execution time so an older queued write cannot restore a reaction.
    private func publish() {
        self.lock.lock()
        let revision = self.revision
        self.lock.unlock()
        self.changed.set(Int(revision))
        self.queue.async { [weak self] in
            guard let self else { return }
            self.lock.lock()
            let snapshot = self.records
            self.lock.unlock()
            if let data = try? JSONEncoder().encode(snapshot) {
                try? data.write(to: self.path, options: .atomic)
            }
        }
    }

    public func stage(message: Message, threadId: Int64?, sendAsPeerId: PeerId?, reactions: [UpdateMessageReaction], maxCount: Int, isLarge: Bool, storeAsRecentlyUsed: Bool) {
        guard message.id.namespace == Namespaces.Message.Cloud,
              !message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) else { return }
        let values: [NagramiXDeferredReaction] = reactions.compactMap { reaction in
            switch reaction {
            case let .builtin(emoji):
                return NagramiXDeferredReaction(emoji: emoji, fileId: nil, file: nil)
            case let .custom(fileId, file):
                let data: Data?
                if let file {
                    let encoder = PostboxEncoder()
                    encoder.encodeRootObject(file)
                    data = encoder.makeData()
                } else {
                    data = nil
                }
                return NagramiXDeferredReaction(emoji: nil, fileId: fileId, file: data)
            case .stars:
                // Paid Stars require the native purchase flow in an active chat.
                return nil
            }
        }
        self.lock.lock()
        let key = Self.key(message.id)
        let previous = self.records[key]
        // Retain custom media metadata when toggling another reaction later.
        let merged = values.map { value -> NagramiXDeferredReaction in
            if let fileId = value.fileId, value.file == nil,
               let old = previous?.reactions.first(where: { $0.fileId == fileId }) {
                return old
            }
            return value
        }
        self.revision &+= 1
        self.records[key] = NagramiXDeferredReactionRecord(
            peerId: message.id.peerId.toInt64(), namespace: message.id.namespace, id: message.id.id,
            threadId: threadId, reactions: Array(merged.suffix(max(1, maxCount))),
            isLarge: isLarge, storeAsRecentlyUsed: storeAsRecentlyUsed,
            isTags: message.areReactionsTags(accountPeerId: self.accountPeerId),
            sendAsPeerId: sendAsPeerId?.toInt64(), revision: self.revision
        )
        self.lock.unlock()
        self.publish()
    }

    public func displayMessage(_ message: Message) -> Message {
        guard !message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) else { return message }
        self.lock.lock()
        let record = self.records[Self.key(message.id)]
        self.lock.unlock()
        guard let record else { return message }
        var attributes = message.attributes.filter { !($0 is PendingReactionsMessageAttribute) }
        let values = record.reactions.compactMap(\.value)
        attributes.append(PendingReactionsMessageAttribute(accountPeerId: self.accountPeerId,
            reactions: values.map { .init(value: $0.reaction, sendAsPeerId: record.sendAsPeerId.map(PeerId.init) ?? self.accountPeerId) },
            isLarge: record.isLarge, storeAsRecentlyUsed: record.storeAsRecentlyUsed, isTags: record.isTags))
        var associatedMedia = message.associatedMedia
        for value in values {
            if case let .custom(_, file?) = value, let id = file.id { associatedMedia[id] = file }
        }
        // Keep all stock message identity/data; change only local reactions/media
        // and the display version so the native history diff refreshes the bubble.
        return Message(stableId: message.stableId, stableVersion: message.stableVersion &+ record.revision &+ 0x80000000, id: message.id, globallyUniqueId: message.globallyUniqueId, groupingKey: message.groupingKey, groupInfo: message.groupInfo, threadId: message.threadId, timestamp: message.timestamp, flags: message.flags, tags: message.tags, globalTags: message.globalTags, localTags: message.localTags, customTags: message.customTags, forwardInfo: message.forwardInfo, author: message.author, text: message.text, attributes: attributes, media: message.media, peers: message.peers, associatedMessages: message.associatedMessages, associatedMessageIds: message.associatedMessageIds, associatedMedia: associatedMedia, associatedThreadInfo: message.associatedThreadInfo, associatedStories: message.associatedStories)
    }

    // An explicit ordinary-chat reaction supersedes any older local intent.
    // The native transaction checks this invalidation before creating its action.
    public func discard(messageId: MessageId) {
        self.lock.lock()
        let key = Self.key(messageId)
        let removed = self.records.removeValue(forKey: key) != nil
        let startupTombstone = !self.loaded && self.dismissedBeforeLoad.insert(key).inserted
        if removed || startupTombstone { self.revision &+= 1 }
        self.lock.unlock()
        if removed || startupTombstone { self.publish() }
    }

    private func isCurrent(key: String, revision: UInt32) -> Bool {
        self.lock.lock()
        let result = self.records[key]?.revision == revision
        self.lock.unlock()
        return result
    }

    // Only an ordinary, visible, readable chat calls this method. Committing the
    // stock pending action hands offline retry/limits/album normalization to Telegram.
    public func flush(account: Account, peerId: PeerId, threadId: Int64?) {
        guard account.peerId == self.accountPeerId else { return }
        self.queue.async { [weak self, weak account] in
            guard let self, let account else { return }
            self.lock.lock()
            let selected = self.records.filter {
                $0.value.peerId == peerId.toInt64() && $0.value.threadId == threadId && !self.inFlight.contains($0.key)
            }
            self.inFlight.formUnion(selected.keys)
            self.lock.unlock()
            for (key, record) in selected {
                let _ = (account.postbox.transaction { transaction -> Bool in
                    guard let message = transaction.getMessage(record.messageId),
                          message.id.namespace == Namespaces.Message.Cloud else { return false }
                    return true
                } |> mapToSignal { exists -> Signal<Never, NoError> in
                    if !exists { return .complete() }
                    return updateMessageReactionsInteractively(account: account, messageIds: [record.messageId],
                        reactions: record.reactions.compactMap(\.value), isLarge: record.isLarge,
                        storeAsRecentlyUsed: record.storeAsRecentlyUsed, shouldApply: { [weak self] in
                            return self?.isCurrent(key: key, revision: record.revision) == true
                        })
                }).startStandalone(completed: { [weak self] in
                    guard let self else { return }
                    self.lock.lock()
                    self.inFlight.remove(key)
                    if self.records[key]?.revision == record.revision {
                        self.records.removeValue(forKey: key)
                        self.revision &+= 1
                    }
                    self.lock.unlock()
                    self.publish()
                })
            }
        }
    }
}
