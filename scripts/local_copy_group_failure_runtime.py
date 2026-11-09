#!/usr/bin/env python3
"""Исполнить атомарную ошибку копируемого альбома и штатный gate группы."""
from pathlib import Path

from validate_quick_format import block
from local_copy_delivery_runtime import signal_runtime, SK

MANAGER = 'submodules/TelegramCore/Sources/State/PendingMessageManager.swift'

BOUNDARY = r'''
typealias PeerId = Int64
struct MessageId: Hashable, Comparable {
    let peerId: PeerId
    let namespace: Int32
    let id: Int32
    static func < (a: Self, b: Self) -> Bool { (a.peerId, a.namespace, a.id) < (b.peerId, b.namespace, b.id) }
}
struct MessageFlags: OptionSet {
    let rawValue: Int
    static let Unsent = Self(rawValue: 1)
    static let Failed = Self(rawValue: 2)
    static let Incoming = Self(rawValue: 4)
}
protocol MessageAttribute: AnyObject {}
struct OutgoingContentInfoFlags: OptionSet { let rawValue: Int; static let nagramiXCopy = Self(rawValue: 2) }
final class OutgoingContentInfoMessageAttribute: MessageAttribute {
    let flags: OutgoingContentInfoFlags
    init(flags: OutgoingContentInfoFlags) { self.flags = flags }
}
final class ForwardSourceInfoAttribute: MessageAttribute {}
final class OtherAttribute: MessageAttribute {}
final class Media { let token: Int; init(_ token: Int) { self.token = token } }
struct Peer { let id: PeerId }
struct ForwardInfo {
    let author: Peer?
    let source: Peer?
    let sourceMessageId: MessageId?
    let date: Int32
    let authorSignature: String?
    let psaType: String?
    let flags: Int
}
struct StoreMessageForwardInfo {
    let authorId: PeerId?
    let sourceId: PeerId?
    let sourceMessageId: MessageId?
    let date: Int32
    let authorSignature: String?
    let psaType: String?
    let flags: Int
}
struct Message {
    let id: MessageId
    let globallyUniqueId: Int64?
    let groupingKey: Int64?
    let threadId: Int64?
    let timestamp: Int32
    let flags: MessageFlags
    let tags: [String]
    let globalTags: [String]
    let localTags: [String]
    let forwardInfo: ForwardInfo?
    let author: Peer?
    let text: String
    let attributes: [MessageAttribute]
    let media: [Media]
}
struct StoreMessage {
    let id: MessageId
    let customStableId: Int64?
    let globallyUniqueId: Int64?
    let groupingKey: Int64?
    let threadId: Int64?
    let timestamp: Int32
    let flags: MessageFlags
    let tags: [String]
    let globalTags: [String]
    let localTags: [String]
    let forwardInfo: StoreMessageForwardInfo?
    let authorId: PeerId?
    let text: String
    let attributes: [MessageAttribute]
    let media: [Media]
}
enum Update { case update(StoreMessage) }
struct PendingMessageUploadedContentAndReuploadInfo { let token: Int }
enum PendingMessageUploadedContentResult { case content(PendingMessageUploadedContentAndReuploadInfo) }
enum PendingMessageUploadError { case generic }
final class Transaction {
    let records: [MessageId: Message]
    let grouped: [Message]?
    var writes: [MessageId: StoreMessage] = [:]
    init(_ records: [MessageId: Message], grouped: [Message]?) { self.records = records; self.grouped = grouped }
    func getMessageGroup(_ id: MessageId) -> [Message]? { self.grouped }
    func getMessage(_ id: MessageId) -> Message? { self.records[id] }
    func updateMessage(_ id: MessageId, update: (Message) -> Update) {
        guard let message = self.records[id] else { return }
        if case let .update(value) = update(message) { self.writes[id] = value }
    }
}
// A transaction body runs against one snapshot. Its write set becomes visible
// together, and one observer event then removes all failed pending IDs.
final class Postbox {
    let records: [MessageId: Message]
    let grouped: [Message]?
    var pending: [() -> Void] = []
    var requested = 0
    var committed = 0
    var writes: [MessageId: StoreMessage] = [:]
    var onCommit: ((Set<MessageId>) -> Void)?
    init(_ messages: [Message], grouped: [Message]?) {
        self.records = Dictionary(uniqueKeysWithValues: messages.map { ($0.id, $0) })
        self.grouped = grouped
    }
    func transaction<T>(_ body: @escaping (Transaction) -> T) -> Signal<T, NoError> {
        self.requested += 1
        return Signal { subscriber in
            self.pending.append {
                let transaction = Transaction(self.records, grouped: self.grouped)
                let value = body(transaction)
                self.committed += 1
                self.writes = transaction.writes
                self.onCommit?(Set(transaction.writes.keys))
                subscriber.putNext(value)
                subscriber.putCompletion()
            }
            return EmptyDisposable
        }
    }
    func commit() { let pending = self.pending; self.pending = []; for action in pending { action() } }
}
'''

PROBE = r'''
final class PendingMessageContext {
    var state: PendingMessageState
    var threadId: Int64?
    var nagramiXIsCopiedMessage = false
    init(_ state: PendingMessageState, threadId: Int64? = nil) { self.state = state; self.threadId = threadId }
}
final class GroupProbe {
    var messageContexts: [MessageId: PendingMessageContext] = [:]
    var sent: [[MessageId]] = []
    func commitSendingMessageGroup(groupId: Int64,
        messages: [(messageContext: PendingMessageContext, messageId: MessageId,
                    content: PendingMessageUploadedContentAndReuploadInfo)]) {
        self.sent.append(messages.map { $0.messageId })
    }
    func observeRemoved(_ ids: Set<MessageId>, groupId: Int64) {
        for id in ids { self.messageContexts[id]?.state = .none }
        self.beginSendingGroupIfPossible(groupId: groupId)
    }
'''

TESTS = r'''
var checks = 0
func check(_ condition: @autoclosure () -> Bool, _ label: String) {
    if !condition() { fputs("FAIL: \(label)\n", stderr); exit(91) }
    checks += 1
}
@main enum AtomicGroupTests {
    static func main() {
        func message(_ id: Int32, peer: PeerId = 1, namespace: Int32 = 4, group: Int64? = 33,
                     thread: Int64? = 7, flags: MessageFlags = [.Unsent], copy: Bool = true,
                     forward: Bool = false, withForwardInfo: Bool = false) -> Message {
            var attributes: [MessageAttribute] = [OtherAttribute()]
            if copy { attributes.append(OutgoingContentInfoMessageAttribute(flags: [.nagramiXCopy])) }
            if forward { attributes.append(ForwardSourceInfoAttribute()) }
            return Message(id: .init(peerId: peer, namespace: namespace, id: id), globallyUniqueId: Int64(id) * 100,
                groupingKey: group, threadId: thread, timestamp: 500 + id, flags: flags,
                tags: ["tag-\(id)"], globalTags: ["global-\(id)"], localTags: ["local-\(id)"],
                forwardInfo: withForwardInfo ? .init(author: .init(id: 11), source: .init(id: 12),
                    sourceMessageId: .init(peerId: 13, namespace: 14, id: 15), date: 16,
                    authorSignature: "author", psaType: "psa", flags: 17) : nil,
                author: .init(id: 101), text: "caption-\(id)", attributes: attributes, media: [Media(Int(id))])
        }
        let first = message(10, withForwardInfo: true), failed = message(11), pending = message(12)
        let excluded = [message(20, peer: 2), message(21, namespace: 5), message(22, group: 44),
                        message(23, thread: 8), message(24, flags: []), message(25, flags: [.Failed]),
                        message(26, copy: false), message(27, forward: true), message(28, thread: nil),
                        message(29, flags: [.Incoming])]
        let all = [pending, failed, first] + excluded
        let selected = nagramiXCopyUploadFailureIds(all, failedId: failed.id, groupId: 33, threadId: 7)
        check(selected == [first.id, failed.id, pending.id], "failure selector isolates peer namespace group thread and local-copy scope")
        check(nagramiXCopyUploadFailureIds(all + [first, failed], failedId: failed.id, groupId: 33, threadId: 7) == selected,
              "duplicate group or context records cannot duplicate a failure write")
        check(nagramiXCopyUploadFailureIds([], failedId: failed.id, groupId: 33, threadId: 7) == [failed.id],
              "the original failing record is always retained")
        for grouped: [Message]? in [nil, [first], [first, failed, pending]] {
            let store = Postbox(all, grouped: grouped)
            var completed = 0, values = 0
            let d = nagramiXFailCopiedUploadGroup(postbox: store, failedId: failed.id, groupId: 33, threadId: 7,
                contextIds: all.map { $0.id } + [first.id, failed.id]).start(next: { _ in values += 1 },
                    completed: { completed += 1 })
            check(store.requested == 1 && store.committed == 0 && store.writes.isEmpty,
                  "album failure is one deferred database transaction")
            store.commit()
            check(store.committed == 1 && Set(store.writes.keys) == Set(selected),
                  "database and live context fallback fail the whole pending copy album atomically")
            check(completed == 1 && values == 0, "group failure cannot fabricate an uploaded payload")
            for original in [first, failed, pending] {
                let written = store.writes[original.id]!
                check(written.flags == [.Failed], "every pending group member becomes failed")
                check(written.globallyUniqueId == original.globallyUniqueId && written.id == original.id,
                      "atomic failure preserves original retry identity")
                check(written.groupingKey == original.groupingKey && written.threadId == original.threadId,
                      "atomic failure preserves album and topic")
                check(written.timestamp == original.timestamp && written.authorId == original.author?.id
                    && written.text == original.text, "atomic failure preserves content and author fields")
                check(written.tags == original.tags && written.globalTags == original.globalTags
                    && written.localTags == original.localTags, "atomic failure preserves all tags")
                check(written.attributes.map(ObjectIdentifier.init) == original.attributes.map(ObjectIdentifier.init)
                    && written.media.map(ObjectIdentifier.init) == original.media.map(ObjectIdentifier.init),
                    "atomic failure preserves attributes and actual media objects")
            }
            let info = store.writes[first.id]!.forwardInfo!
            check(info.authorId == 11 && info.sourceId == 12 && info.sourceMessageId == first.forwardInfo?.sourceMessageId
                && info.date == 16 && info.authorSignature == "author" && info.psaType == "psa" && info.flags == 17,
                "writer preserves the native forward metadata representation")
            for excluded in excluded { check(store.writes[excluded.id] == nil, "unrelated or nonpending records remain untouched") }
            d.dispose()
        }
        // Compose the production selector/writer with the real native group
        // collector: a completed sibling cannot pass while the failed upload
        // still blocks the group, and a single atomic removal leaves no subset.
        do {
            let probe = GroupProbe()
            probe.messageContexts[first.id] = PendingMessageContext(.waitingToBeSent(groupId: 33, content: .init(token: 1)))
            probe.messageContexts[failed.id] = PendingMessageContext(.uploading(groupId: 33))
            probe.messageContexts[pending.id] = PendingMessageContext(.collectingInfo(message: pending))
            probe.messageContexts[first.id]?.nagramiXIsCopiedMessage = true
            probe.messageContexts[failed.id]?.nagramiXIsCopiedMessage = true
            let contextIds = probe.contextIdsForFailure(failedId: failed.id, groupId: 33)
            check(Set(contextIds) == Set([first.id, failed.id, pending.id]),
                  "fallback includes collecting members before their copy flag is initialized")
            let store = Postbox([first, failed, pending], grouped: [first])
            store.onCommit = { probe.observeRemoved($0, groupId: 33) }
            let d = nagramiXFailCopiedUploadGroup(postbox: store, failedId: failed.id, groupId: 33,
                threadId: 7, contextIds: contextIds).start()
            probe.beginSendingGroupIfPossible(groupId: 33)
            check(probe.sent.isEmpty, "failed uploading record blocks ready siblings before atomic failure")
            probe.messageContexts[pending.id]?.state = .waitingToBeSent(groupId: 33, content: .init(token: 3))
            probe.beginSendingGroupIfPossible(groupId: 33)
            check(probe.sent.isEmpty, "late sibling content cannot race the pending atomic failure")
            store.commit()
            check(probe.sent.isEmpty, "atomic group failure cannot send an incomplete album")
            check(Set(store.writes.keys) == Set([first.id, failed.id, pending.id]), "collecting and ready members fail with the upload")
            d.dispose()
        }
        // The old one-record removal really would release a partial group.
        // This positive control proves the fixture can observe that regression.
        do {
            let probe = GroupProbe()
            probe.messageContexts[first.id] = PendingMessageContext(.waitingToBeSent(groupId: 33, content: .init(token: 1)))
            probe.messageContexts[failed.id] = PendingMessageContext(.uploading(groupId: 33))
            probe.observeRemoved([failed.id], groupId: 33)
            check(probe.sent == [[first.id]], "control reproduces native partial send after one-record failure")
        }
        print("Local copy atomic album-failure checks: \(checks)")
    }
}
'''


def fixture(source: Path) -> str:
    manager = (source / MANAGER).read_text()
    pieces = [signal_runtime(source), BOUNDARY]
    meta = (source / (SK + 'Signal_Meta.swift')).read_text()
    mapping = (source / (SK + 'Signal_Mapping.swift')).read_text()
    pieces.append(block(mapping, 'public func map<T, E, R>('))
    for marker in ['private final class SignalQueueState', 'public func switchToLatest<',
                   'public func mapToSignal<T, R, E>(']:
        pieces.append(block(meta, marker))
    pieces.extend(block(manager, marker) for marker in [
        'private func nagramiXIsLocalCopyMessage(', 'private func nagramiXCopyUploadFailureIds(',
        'private func nagramiXFailCopiedUploadGroup(',
    ])
    pieces.append(block(manager, 'private enum PendingMessageState').replace('private enum', 'enum', 1))
    pieces.append(PROBE)
    pieces.append(block(manager, '    private func dataForPendingMessageGroup('))
    pieces.append(block(manager, '    private func beginSendingGroupIfPossible(')
                  .replace('    private func', '    func', 1))
    context_ids = block(manager, '                    let ids = strongSelf.messageContexts.compactMap')
    pieces.append('func contextIdsForFailure(failedId id: MessageId, groupId: Int64) -> [MessageId] {\n'
                  'let strongSelf = self\n' + context_ids + '\nreturn ids\n}\n')
    pieces.append('}\n')
    pieces.append(TESTS)
    return '\n'.join(pieces)


def semantic_negatives(swift: str):
    variants = [
        ('partial-album-failure',
         'for id in nagramiXCopyUploadFailureIds(messages, failedId: failedId, groupId: groupId, threadId: threadId) {',
         'for id in [failedId] {', 'database and live context fallback fail the whole pending copy album atomically'),
        ('cross-peer-failure', 'message.id.peerId == failedId.peerId && message.id.namespace == failedId.namespace,',
         'message.id.namespace == failedId.namespace,',
         'failure selector isolates peer namespace group thread and local-copy scope'),
        ('lost-retry-identity', 'globallyUniqueId: currentMessage.globallyUniqueId,',
         'globallyUniqueId: nil,', 'atomic failure preserves original retry identity'),
        ('premature-copy-flag', 'entry.value.state.groupId == groupId ? entry.key : nil',
         'entry.value.state.groupId == groupId && entry.value.nagramiXIsCopiedMessage ? entry.key : nil',
         'fallback includes collecting members before their copy flag is initialized'),
        ('early-partial-send', '            case let .uploading(contextGroupId):\n                if contextGroupId == groupId {\n                    return nil\n                }',
         '            case .uploading:\n                continue loop',
         'late sibling content cannot race the pending atomic failure'),
    ]
    for name, before, after, diagnostic in variants:
        assert swift.count(before) == 1, (name, swift.count(before))
        yield name, swift.replace(before, after), diagnostic
