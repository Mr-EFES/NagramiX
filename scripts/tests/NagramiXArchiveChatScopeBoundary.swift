// Границы Postbox/UI/MediaBox для исполнения настоящих методов архива.
// Модели, persistence coordinator, мутации и блок построения строк вставляет валидатор.
import Foundation
import CoreFoundation

public enum NoError {}
public struct Signal<T, E> {}
final class ValuePromise<T> {
    var value: T
    init(_ value: T, ignoreRepeated: Bool) { self.value = value }
    func set(_ value: T) { self.value = value }
    func get() -> Signal<T, NoError> { Signal() }
}
final class Atomic<T> {
    var value: T
    init(value: T) { self.value = value }
    func with<R>(_ body: (T) -> R) -> R { body(value) }
    func swap(_ value: T) -> T { let previous = self.value; self.value = value; return previous }
    func modify<R>(_ body: (inout T) -> R) -> R { body(&value) }
}
final class Queue {
    static var pending: [() -> Void] = []
    func async(_ action: @escaping () -> Void) { Self.pending.append(action) }
    static func drain() { while !pending.isEmpty { pending.removeFirst()() } }
}
enum SwiftSignalKit {
    final class Timer {
        var invalidated = false
        init(timeout: Double, repeat: Bool, completion: @escaping () -> Void, queue: Queue) {}
        func start() {}
        func invalidate() { invalidated = true }
    }
}
public struct MessageTextEntity: Codable, Equatable {}
public struct PeerId: Hashable {
    let value: Int64
    init(_ value: Int64) { self.value = value }
    init(namespace: Int32, id: Int64) { self.value = Int64(namespace) << 32 | id }
    var namespace: Int32 { Int32(truncatingIfNeeded: value >> 32) }
    func toInt64() -> Int64 { value }
}
public struct MessageId: Hashable {
    public typealias Namespace = Int32
    let peerId: PeerId
    let namespace: Int32
    let id: Int32
}
struct MessageIndex: Comparable {
    let id: MessageId
    let timestamp: Int32
    static func < (lhs: Self, rhs: Self) -> Bool {
        lhs.timestamp == rhs.timestamp ? lhs.id.id < rhs.id.id : lhs.timestamp < rhs.timestamp
    }
}
enum Namespaces {
    enum Message { static let Cloud: Int32 = 0; static let ScheduledCloud: Int32 = 3; static let ScheduledLocal: Int32 = 4 }
    enum Peer { static let SecretChat: Int32 = 3; static let CloudChannel: Int32 = 2 }
}
struct MessageFlags: OptionSet {
    let rawValue: Int
    static let Incoming = Self(rawValue: 1)
}
class Media {}
final class TelegramMediaExpiredContent: Media {}
class MessageAttribute {}
final class EditedMessageAttribute: MessageAttribute { let date: Int32; init(_ date: Int32) { self.date = date } }
final class Peer {}
typealias StoreMessage = Message
final class Message {
    let id: MessageId
    let timestamp: Int32
    let threadId: Int64?
    let groupingKey: Int64?
    let text: String
    let incoming: Bool
    let bytes: [Data]
    let temporary: Bool
    let replay: Bool
    let eligible: Bool
    let isDeleted: Bool
    let media: [Media]
    var peers = SimpleDictionary<PeerId, Peer>()
    var attributes: [MessageAttribute] { [] }
    var index: MessageIndex { MessageIndex(id: id, timestamp: timestamp) }
    var flags: MessageFlags { incoming ? .Incoming : [] }
    var containsSecretMedia: Bool { temporary }
    init(_ id: MessageId, timestamp: Int32 = 100, thread: Int64? = nil,
         grouping: Int64? = nil, text: String = "message", incoming: Bool = true,
         bytes: [Data] = [], temporary: Bool = false, replay: Bool = false,
         eligible: Bool = true, deleted: Bool = false, media: [Media] = []) {
        self.id = id; self.timestamp = timestamp; self.threadId = thread
        self.groupingKey = grouping; self.text = text; self.incoming = incoming
        self.bytes = bytes; self.temporary = temporary; self.replay = replay
        self.eligible = eligible; self.isDeleted = deleted; self.media = media
    }
}
final class Transaction {
    var messages: [Message]
    var enumerations = 0
    init(_ messages: [Message]) { self.messages = messages }
    func getMessage(_ id: MessageId) -> Message? { messages.first { $0.id == id } }
    func withAllMessages(peerId: PeerId, namespace: Int32? = nil, _ body: (Message) -> Bool) {
        enumerations += 1
        for message in messages where message.id.peerId == peerId && (namespace == nil || message.id.namespace == namespace) {
            if !body(message) { break }
        }
    }
    func messageIdsForGlobalIds(_ ids: [Int32]) -> [MessageId] {
        messages.filter { ids.contains($0.id.id) && $0.id.peerId.namespace != Namespaces.Peer.CloudChannel }.map { $0.id }
    }
    func remove(_ ids: [MessageId]) { messages.removeAll { ids.contains($0.id) } }
    func clear(peerId: PeerId, threadId: Int64?, minTimestamp: Int32?, maxTimestamp: Int32?, namespaces: MessageIdNamespaces) {
        messages.removeAll {
            $0.id.peerId == peerId && namespaces.contains($0.id.namespace)
                && (threadId == nil || $0.threadId == threadId)
                && (minTimestamp == nil || $0.timestamp >= minTimestamp!)
                && (maxTimestamp == nil || $0.timestamp <= maxTimestamp!)
        }
    }
}
final class MediaBox {}
final class Postbox {
    let mediaBox = MediaBox()
}
struct NagramiXArchiveMediaRequest { let data: Data }
final class MediaStoreSpy {
    var sequence: Int64 = 0
    var reserved: Set<String> = []
    var retained: [String: [Data]] = [:]
    var removed: Set<String> = []
    var clears = 0
    func barrier() -> Int64 { sequence += 1; return sequence }
    func reserve(key: String, requests: [NagramiXArchiveMediaRequest]) -> Int64 { reserved.insert(key); return barrier() }
    func retain(key: String, requests: [NagramiXArchiveMediaRequest], ticket: Int64) { retained[key] = requests.map { $0.data } }
    func remove(keys: Set<String>, before: Int64) { removed.formUnion(keys); for key in keys { retained.removeValue(forKey: key) } }
    func clear(before: Int64) { clears += 1; removed.formUnion(retained.keys); retained.removeAll() }
}
enum ChatControllerSubject: Equatable {
    case message(id: Int)
    case scheduledMessages
    case pinnedMessages(id: Int?)
    case messageOptions
    case customChatContents
}
struct ChatLocation { let peerId: PeerId?; let threadId: Int64? }
struct MutableMessageHistoryEntryAttributes { let authorIsContact: Bool }
struct MessageHistoryEntry {
    let message: Message
    let isRead: Bool
    let location: Int?
    let monthLocation: Int?
    let attributes: MutableMessageHistoryEntryAttributes
}
struct MessageHistoryView {
    let entries: [MessageHistoryEntry]
    var tag: String? = nil
    var namespaces: MessageIdNamespaces = .all
    var earlierId: MessageIndex? = nil
    var laterId: MessageIndex? = nil
}
struct AssociatedData { var isRecentActions = false }
private struct TestAccount { let nagramiXMessageArchive: ArchiveHarness }
private struct TestContext { let account: TestAccount }
private final class NagramiXWeakMessageArchive {
    weak var value: ArchiveHarness?
    init(_ value: ArchiveHarness) { self.value = value }
}
