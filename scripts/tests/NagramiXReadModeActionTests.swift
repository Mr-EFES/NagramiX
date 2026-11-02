// Contract doubles for TelegramCore's account/transaction/network boundary.
// The validator compiles the real production read-mode and private-ledger code
// against these doubles. This does not replace an Apple SDK/device test.
import Foundation

public enum NoError {}
enum TestNetworkError { case rejected }
protocol Disposable { func dispose() }
struct ActionDisposable: Disposable {
    let action: () -> Void
    init(_ action: @escaping () -> Void) { self.action = action }
    func dispose() { self.action() }
}
private let emptyDisposable = ActionDisposable({})
public final class Subscriber<T, E> {
    let next: (T) -> Void
    let error: (E) -> Void
    let completed: () -> Void
    init(next: @escaping (T) -> Void, error: @escaping (E) -> Void, completed: @escaping () -> Void) {
        self.next = next; self.error = error; self.completed = completed
    }
    func putNext(_ value: T) { self.next(value) }
    func putError(_ value: E) { self.error(value) }
    func putCompletion() { self.completed() }
}
public final class Signal<T, E> {
    let generate: (Subscriber<T, E>) -> Disposable
    init(_ generate: @escaping (Subscriber<T, E>) -> Disposable) { self.generate = generate }
    @discardableResult func start(next: @escaping (T) -> Void = { _ in }, error: @escaping (E) -> Void = { _ in }, completed: @escaping () -> Void = {}) -> Disposable {
        return self.generate(Subscriber(next: next, error: error, completed: completed))
    }
    static func single(_ value: T) -> Signal<T, E> { Signal { $0.putNext(value); $0.putCompletion(); return emptyDisposable } }
    static func complete() -> Signal<T, E> { Signal { $0.putCompletion(); return emptyDisposable } }
    @discardableResult func startStandalone() -> Disposable { self.start() }
}
precedencegroup PipeRight {
    associativity: left
    higherThan: DefaultPrecedence
}
infix operator |> : PipeRight
func |> <T, U>(value: T, function: (T) -> U) -> U { function(value) }
func map<T, U, E>(_ transform: @escaping (T) -> U) -> (Signal<T, E>) -> Signal<U, E> {
    { source in Signal { subscriber in source.start(next: { subscriber.putNext(transform($0)) }, error: subscriber.putError, completed: subscriber.putCompletion) } }
}
func mapToSignal<T, U, E>(_ transform: @escaping (T) -> Signal<U, E>) -> (Signal<T, E>) -> Signal<U, E> {
    { source in Signal { subscriber in source.start(next: { _ = transform($0).start(next: subscriber.putNext, error: subscriber.putError) }, error: subscriber.putError, completed: subscriber.putCompletion) } }
}
func `catch`<T, E, U>(_ transform: @escaping (E) -> Signal<T, U>) -> (Signal<T, E>) -> Signal<T, U> {
    { source in Signal { subscriber in source.start(next: subscriber.putNext, error: { _ = transform($0).start(next: subscriber.putNext, error: subscriber.putError, completed: subscriber.putCompletion) }, completed: subscriber.putCompletion) } }
}
func distinctUntilChanged<T: Equatable, E>(_ source: Signal<T, E>) -> Signal<T, E> {
    Signal { subscriber in
        var previous: T?
        return source.start(next: { if previous != $0 { previous = $0; subscriber.putNext($0) } }, error: subscriber.putError, completed: subscriber.putCompletion)
    }
}
enum Namespaces {
    enum Message { static let Cloud: Int32 = 0; static let Local: Int32 = 1 }
    enum Peer { static let CloudUser: Int32 = 0; static let CloudChannel: Int32 = 2; static let SecretChat: Int32 = 3 }
}
struct PeerId: Hashable {
    let namespace: Int32; let value: Int64
    init(namespace: Int32, value: Int64) { self.namespace = namespace; self.value = value }
    init(_ encoded: Int64) { self.namespace = Int32(encoded / 1_000_000); self.value = encoded % 1_000_000 }
    func toInt64() -> Int64 { value + Int64(namespace) * 1_000_000 }
}
struct MessageId: Hashable, Comparable {
    let peerId: PeerId; let namespace: Int32; let id: Int32
    static func < (lhs: Self, rhs: Self) -> Bool { lhs.id < rhs.id }
}
struct MessageIndex { let id: MessageId }
final class ValueBoxKey: Hashable {
    var words: [Int: Int64] = [:]
    init(length: Int) { precondition(length == 16 || length == 24) }
    func setInt64(_ offset: Int, value: Int64) { self.words[offset] = value }
    func hash(into hasher: inout Hasher) { hasher.combine(words[0]); hasher.combine(words[8]); hasher.combine(words[16]) }
    static func == (lhs: ValueBoxKey, rhs: ValueBoxKey) -> Bool { lhs.words == rhs.words }
}
struct PreferencesEntry {
    let data: Data
    init<T: Encodable>(_ value: T) { self.data = try! JSONEncoder().encode(value) }
    func get<T: Decodable>(_ type: T.Type) -> T? { try? JSONDecoder().decode(type, from: self.data) }
}
class Peer {
    let id: PeerId
    init(id: PeerId) { self.id = id }
    var isForumOrMonoForum: Bool { false }
    var isForum: Bool { false }
}
final class TelegramChannel: Peer {
    struct Flags: OptionSet {
        let rawValue: Int
        static let isForum = Flags(rawValue: 1)
        static let isMonoforum = Flags(rawValue: 2)
    }
    let flags: Flags
    init(id: PeerId, flags: Flags = .isForum) { self.flags = flags; super.init(id: id) }
    override var isForumOrMonoForum: Bool { !self.flags.isEmpty }
    override var isForum: Bool { self.flags.contains(.isForum) }
}
struct Message { let index: MessageIndex; let threadId: Int64? }
struct MessageHistoryThreadData: Codable {
    var maxIncomingReadId: Int32 = 0
    var incomingUnreadCount: Int32 = 0
    var maxKnownMessageId: Int32 = 0
}
struct StoredMessageHistoryThreadInfo {
    let data: PreferencesEntry
    init?(_ data: MessageHistoryThreadData) { self.data = PreferencesEntry(data) }
}
struct ThreadItem { let threadId: Int64 }
enum ThreadHole: Hashable { case everywhere }
final class OutgoingScheduleInfoMessageAttribute {}
struct EngineMessageReplySubject { let messageId: MessageId }
enum EnqueueMessage {
    case message(String, [Any], Int, Int, Int64?, EngineMessageReplySubject?, Int, Int, Int, Int)
    case forward(MessageId, Int64?, Int, [Any], Int)
    var attributes: [Any] {
        switch self { case let .message(_, attributes, _, _, _, _, _, _, _, _), let .forward(_, _, _, attributes, _): return attributes }
    }
}
final class Transaction {
    var values: [ValueBoxKey: PreferencesEntry] = [:]
    var peers: [PeerId: Peer] = [:]
    var messages: [MessageId: Message] = [:]
    var localReads: [MessageId] = []
    var threads: [PeerId: [Int64: MessageHistoryThreadData]] = [:]
    func getPreferencesEntry(key: ValueBoxKey) -> PreferencesEntry? { values[key] }
    func setPreferencesEntry(key: ValueBoxKey, value: PreferencesEntry) { values[key] = value }
    func updatePreferencesEntry(key: ValueBoxKey, _ update: (PreferencesEntry?) -> PreferencesEntry?) { values[key] = update(values[key]) }
    func getPeer(_ id: PeerId) -> Peer? { peers[id] }
    func getMessage(_ id: MessageId) -> Message? { messages[id] }
    func getMessageHistoryThreadInfo(peerId: PeerId, threadId: Int64) -> StoredMessageHistoryThreadInfo? { self.threads[peerId]?[threadId].flatMap(StoredMessageHistoryThreadInfo.init) }
    func setMessageHistoryThreadInfo(peerId: PeerId, threadId: Int64, info: StoredMessageHistoryThreadInfo) { self.threads[peerId, default: [:]][threadId] = info.data.get(MessageHistoryThreadData.self)! }
    func getThreadMessageCount(peerId: PeerId, threadId: Int64, namespace: Int32, fromIdExclusive: Int32, toIndex: MessageIndex) -> Int? {
        self.messages.values.filter { $0.index.id.peerId == peerId && $0.threadId == threadId && $0.index.id.namespace == namespace && $0.index.id.id > fromIdExclusive && $0.index.id.id <= toIndex.id.id }.count
    }
    func getMessageHistoryThreadTopMessage(peerId: PeerId, threadId: Int64, namespaces: Set<Int32>) -> MessageIndex? {
        self.messages.values.filter { $0.index.id.peerId == peerId && $0.threadId == threadId && namespaces.contains($0.index.id.namespace) }.max(by: { $0.index.id.id < $1.index.id.id })?.index
    }
    func getTopPeerMessageIndex(peerId: PeerId, namespace: Int32) -> MessageIndex? {
        self.messages.values.filter { $0.index.id.peerId == peerId && $0.index.id.namespace == namespace }.max(by: { $0.index.id.id < $1.index.id.id })?.index
    }
    func getThreadIndexHole(peerId: PeerId, threadId: Int64, namespace: Int32, containing: Int32) -> [ThreadHole: Bool] { [:] }
    func getMessageHistoryThreadIndex(peerId: PeerId, limit: Int) -> [ThreadItem] { (self.threads[peerId] ?? [:]).keys.sorted().prefix(limit).map(ThreadItem.init) }
}
final class TestPostbox {
    let storage = Transaction()
    var beforeEmission: (() -> Void)?
    func transaction<T>(_ action: @escaping (Transaction) -> T) -> Signal<T, NoError> {
        Signal { subscriber in
            let result = action(self.storage)
            let hook = self.beforeEmission; self.beforeEmission = nil; hook?()
            subscriber.putNext(result); subscriber.putCompletion(); return emptyDisposable
        }
    }
}
enum Api {
    enum Bool { case boolTrue, boolFalse }
    struct Channel { let channelId: Int64; let accessHash: Int64 }
    enum InputChannel { case inputChannel(Channel) }
    enum InputPeer { case inputPeerChannel(Channel), inputPeerUser(Int64) }
    enum messages {
        struct Data { let pts: Int32; let ptsCount: Int32 }
        enum AffectedMessages { case affectedMessages(Data) }
    }
    enum functions {
        enum channels {
            static func readHistory(channel: InputChannel, maxId: Int32) -> TestRequest<Api.Bool> {
                switch channel {
                case let .inputChannel(data): return TestRequest(peer: data.channelId, maxId: maxId, response: { $0.channelResult })
                }
            }
        }
        enum messages {
            static func readSavedHistory(parentPeer: InputPeer, peer: InputPeer, maxId: Int32) -> TestRequest<Api.Bool> {
                guard case let .inputPeerChannel(data) = parentPeer, case let .inputPeerUser(id) = peer else { preconditionFailure("invalid saved target") }
                return TestRequest(peer: data.channelId, maxId: maxId, response: { $0.discussionResult }, saved: id)
            }
            static func readDiscussion(peer: InputPeer, msgId: Int32, readMaxId: Int32) -> TestRequest<Api.Bool> {
                switch peer {
                case let .inputPeerChannel(data): return TestRequest(peer: data.channelId, maxId: readMaxId, response: { $0.discussionResult }, discussion: msgId)
                case let .inputPeerUser(id): return TestRequest(peer: id, maxId: readMaxId, response: { $0.discussionResult }, discussion: msgId)
                }
            }
            static func readHistory(peer: InputPeer, maxId: Int32) -> TestRequest<Api.messages.AffectedMessages> {
                if case let .inputPeerUser(id) = peer { return TestRequest(peer: id, maxId: maxId, response: { _ in .affectedMessages(.init(pts: 42, ptsCount: 1)) }) }
                preconditionFailure("channel must use channels.readHistory")
            }
        }
    }
}
func apiInputPeer(_ peer: Peer) -> Api.InputPeer? {
    if peer.id.namespace == Namespaces.Peer.SecretChat { return nil }
    if peer.id.namespace == Namespaces.Peer.CloudChannel { return .inputPeerChannel(.init(channelId: peer.id.value, accessHash: 123)) }
    return .inputPeerUser(peer.id.value)
}
struct TestRequest<T> { let peer: Int64; let maxId: Int32; let response: (TestNetwork) -> T; var discussion: Int32? = nil; var saved: Int64? = nil }
final class TestNetwork {
    var requests: [(Int64, Int32)] = []
    var reject = false
    var channelResult = Api.Bool.boolTrue
    var discussionResult = Api.Bool.boolTrue
    var discussionRequests: [(Int32, Int32)] = []
    var savedRequests: [(Int64, Int32)] = []
    var duringRequest: (() -> Void)?
    func request<T>(_ request: TestRequest<T>) -> Signal<T, TestNetworkError> {
        Signal { subscriber in
            if let saved = request.saved { self.savedRequests.append((saved, request.maxId)) }
            else if let discussion = request.discussion { self.discussionRequests.append((discussion, request.maxId)) }
            else { self.requests.append((request.peer, request.maxId)) }
            let hook = self.duringRequest; self.duringRequest = nil; hook?()
            if self.reject { subscriber.putError(.rejected) } else { subscriber.putNext(request.response(self)); subscriber.putCompletion() }
            return emptyDisposable
        }
    }
}
enum TestUpdate { case updatePts(pts: Int32, ptsCount: Int32) }
final class TestStateManager {
    var updates: [TestUpdate] = []
    func addUpdateGroups(_ updates: [TestUpdate]) { self.updates += updates }
}
final class Account {
    var isSupportUser = false
    let peerId = PeerId(namespace: Namespaces.Peer.CloudUser, value: 1)
    let postbox = TestPostbox()
    let network = TestNetwork()
    let stateManager = TestStateManager()
}


func ignoreValues<T, E>(_ source: Signal<T, E>) -> Signal<Never, E> {
    Signal { subscriber in source.start(error: subscriber.putError, completed: subscriber.putCompletion) }
}
func _internal_applyMaxReadIndexInteractively(transaction: Transaction, stateManager: TestStateManager, index: MessageIndex) {
    transaction.localReads.append(index.id)
    _ = nagramiXRecordPrivateRead(transaction: transaction, index: index)
}

@main struct ReadModeActionTests {
    static func main() {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ name: String) { precondition(value(), name); checks += 1 }
        let key = "nagramix.privacy.individual.v2"
        let saved = UserDefaults.standard.object(forKey: key)
        defer { if let saved { UserDefaults.standard.set(saved, forKey: key) } else { UserDefaults.standard.removeObject(forKey: key) } }
        func settings(local: Bool, action: Bool) {
            NagramiXPrivacySettings.update { $0.readMode = local ? .local : .standard; $0[.readOnAction] = action }
        }
        let peer = PeerId(namespace: Namespaces.Peer.CloudUser, value: 2)
        func id(_ value: Int32, peerId: PeerId? = nil, namespace: Int32 = Namespaces.Message.Cloud) -> MessageId { MessageId(peerId: peerId ?? peer, namespace: namespace, id: value) }
        func index(_ value: Int32, peerId: PeerId? = nil) -> MessageIndex { MessageIndex(id: id(value, peerId: peerId)) }
        func seed(_ account: Account, through: Int32 = 5, peerId: PeerId? = nil, thread: Int64? = nil) {
            let peerId = peerId ?? peer
            account.postbox.storage.peers[peerId] = peerId.namespace == Namespaces.Peer.CloudChannel ? TelegramChannel(id: peerId, flags: thread == nil ? [] : .isForum) : Peer(id: peerId)
            for n in 1...through {
                account.postbox.storage.messages[id(n, peerId: peerId)] = Message(index: index(n, peerId: peerId), threadId: thread)
            }
            if let thread { account.postbox.storage.threads[peerId, default: [:]][thread] = MessageHistoryThreadData(incomingUnreadCount: through) }
            check(nagramiXRecordPrivateRead(transaction: account.postbox.storage, index: index(through, peerId: peerId), threadId: thread), "real production ledger records private boundary")
        }
        for local in [false, true] {
            settings(local: local, action: true)
            let account = Account(), other = Account()
            seed(account); seed(other)
            nagramiXReadPreviouslyLocalMessage(account: account, index: index(5)).start()
            check(account.network.requests.isEmpty, "opening chat in independent action mode sends no read receipt")
            nagramiXReadAfterUserAction(account: account, peerId: peer, upTo: id(3)).start()
            check(account.network.requests.count == 1 && account.network.requests[0].1 == 3, "reaction to 3 reads exactly 1...3, not 4 or 5")
            check(account.postbox.storage.localReads.last?.id == 3, "local action boundary matches selected message")
            check(nagramiXHasPrivateRead(transaction: account.postbox.storage, peerId: peer), "4 and 5 remain protected after partial acknowledgement")
            check(nagramiXPreservePrivateRead(transaction: account.postbox.storage, peerId: peer, localMaxId: 5, serverMaxId: 3), "background validation cannot publish 4 and 5")
            check(other.network.requests.isEmpty && nagramiXHasPrivateRead(transaction: other.postbox.storage, peerId: peer), "other account unaffected")
            // New incoming 6 appears after Send captured 5 but before its read request.
            account.postbox.storage.messages[id(6)] = Message(index: index(6), threadId: nil)
            nagramiXReadAfterUserAction(account: account, peerId: peer, upTo: id(5)).start()
            check(account.network.requests.last?.1 == 5, "reply uses captured boundary, not newly arriving 6")
            check(!nagramiXHasPrivateRead(transaction: account.postbox.storage, peerId: peer), "full successful acknowledgement retires only accepted private marker")
            check(account.stateManager.updates.count == 2, "native pts updates are applied")
        }
        settings(local: true, action: false)
        let account = Account(); seed(account)
        nagramiXReadAfterUserAction(account: account, peerId: peer, upTo: id(3)).start()
        nagramiXReadPreviouslyLocalMessage(account: account, index: index(5)).start()
        check(account.network.requests.isEmpty && account.postbox.storage.localReads.isEmpty, "local only never authorizes action or opening receipts")
        settings(local: false, action: false)
        check(account.network.requests.isEmpty, "changing settings does not read closed chats")
        nagramiXReadPreviouslyLocalMessage(account: account, index: index(3)).start()
        check(account.network.requests.last?.1 == 3, "normal opening can read the visible boundary after local mode is OFF")
        check(nagramiXHasPrivateRead(transaction: account.postbox.storage, peerId: peer), "normal partial opening preserves later private messages")
        settings(local: false, action: true)
        account.network.reject = true
        nagramiXReadAfterUserAction(account: account, peerId: peer, upTo: id(5)).start()
        check(nagramiXHasPrivateRead(transaction: account.postbox.storage, peerId: peer), "network failure cannot acknowledge private history")
        account.network.reject = false
        account.postbox.beforeEmission = { settings(local: true, action: false) }
        let before = account.network.requests.count
        nagramiXReadAfterUserAction(account: account, peerId: peer, upTo: id(5)).start()
        check(account.network.requests.count == before, "turning action reading OFF before request cancels authorization")
        settings(local: false, action: true)
        account.network.duringRequest = {
            seed(account, through: 7)
        }
        nagramiXReadAfterUserAction(account: account, peerId: peer, upTo: id(5)).start()
        check(nagramiXPreservePrivateRead(transaction: account.postbox.storage, peerId: peer, localMaxId: 7, serverMaxId: 5), "in-flight success cannot erase newer private boundary")
        for target in [id(5, peerId: account.peerId), id(5, peerId: PeerId(namespace: Namespaces.Peer.SecretChat, value: 3)), id(5, namespace: Namespaces.Message.Local), id(99)] {
            let count = account.network.requests.count
            nagramiXReadAfterUserAction(account: account, peerId: target.peerId, upTo: target).start()
            check(account.network.requests.count == count, "self/secret/local/deleted boundary does not publish")
        }
        let otherPeer = PeerId(namespace: Namespaces.Peer.CloudUser, value: 88)
        let count = account.network.requests.count
        nagramiXReadAfterUserAction(account: account, peerId: otherPeer, upTo: id(3)).start()
        check(account.network.requests.count == count, "mismatched peer is rejected")
        let channel = PeerId(namespace: Namespaces.Peer.CloudChannel, value: 9)
        seed(account, peerId: channel, thread: 2)
        account.network.channelResult = .boolFalse
        account.network.discussionResult = .boolFalse
        let broadCount = account.network.requests.count
        nagramiXReadAfterUserAction(account: account, peerId: channel, upTo: id(5, peerId: channel)).start()
        check(account.network.requests.count == broadCount && account.network.discussionRequests.last?.0 == 2, "thread action sends no channel-wide readHistory")
        check(nagramiXHasPrivateRead(transaction: account.postbox.storage, peerId: channel, threadId: 2), "failed discussion keeps its private marker")
        account.network.discussionResult = .boolTrue
        nagramiXReadAfterUserAction(account: account, peerId: channel, upTo: id(5, peerId: channel)).start()
        check(!nagramiXHasPrivateRead(transaction: account.postbox.storage, peerId: channel, threadId: 2), "successful discussion retires only its topic marker")
        check(account.network.discussionRequests.last?.0 == 2 && account.network.discussionRequests.last?.1 == 5, "discussion uses exact thread and maxId")
        check(account.postbox.storage.localReads.allSatisfy { $0.peerId != channel }, "thread actions never invoke peer-wide local read")
        for local in [false, true] {
            settings(local: local, action: true)
            let scoped = Account(); seed(scoped, peerId: channel, thread: 2)
            let storage = scoped.postbox.storage
            for value in Int32(101)...105 {
                storage.messages[id(value, peerId: channel)] = Message(index: index(value, peerId: channel), threadId: 100)
            }
            storage.threads[channel, default: [:]][100] = MessageHistoryThreadData(incomingUnreadCount: 5)
            _ = nagramiXRecordPrivateRead(transaction: storage, index: index(105, peerId: channel), threadId: 100)
            _ = nagramiXRecordPrivateRead(transaction: storage, index: index(105, peerId: channel)) // retained legacy marker
            nagramiXReadAfterUserAction(account: scoped, peerId: channel, upTo: id(3, peerId: channel)).start()
            check(scoped.network.requests.isEmpty && scoped.network.discussionRequests.count == 1, "reaction in topic has exactly one scoped RPC")
            check(storage.threads[channel]?[2]?.maxIncomingReadId == 3 && storage.threads[channel]?[2]?.incomingUnreadCount == 2, "topic reaction reads 1...3 locally, keeps 4 and 5 unread")
            check(storage.threads[channel]?[100]?.maxIncomingReadId == 0 && storage.threads[channel]?[100]?.incomingUnreadCount == 5, "reaction cannot change another topic's local counters")
            check(nagramiXHasPrivateRead(transaction: storage, peerId: channel, threadId: 2), "partial topic acknowledgement preserves later private messages")
            check(nagramiXHasPrivateRead(transaction: storage, peerId: channel, threadId: 100), "other topic private marker remains independent")
            check(nagramiXHasPrivateRead(transaction: storage, peerId: channel), "topic receipt never retires legacy peer marker")
            let outgoing = EnqueueMessage.message("reply", [], 0, 0, 2, nil, 0, 0, 0, 0)
            let boundary = nagramiXReadBoundaryBeforeEnqueue(transaction: storage, peerId: channel, message: outgoing)!
            check(boundary.messageId == id(5, peerId: channel) && boundary.threadId == 2, "reply snapshots topic top5 instead of other topic105")
            storage.messages[id(6, peerId: channel)] = Message(index: index(6, peerId: channel), threadId: 2)
            _ = nagramiXRecordPrivateRead(transaction: storage, index: index(6, peerId: channel), threadId: 2)
            nagramiXReadAfterUserAction(account: scoped, peerId: channel, upTo: boundary.messageId, threadId: boundary.threadId).start()
            check(scoped.network.discussionRequests.last?.0 == 2 && scoped.network.discussionRequests.last?.1 == 5, "reply reads captured topic boundary, not newer6 or other topic105")
            check(nagramiXHasPrivateRead(transaction: storage, peerId: channel, threadId: 2), "reply acknowledgement cannot erase a newer topic watermark")
            check(storage.localReads.isEmpty, "topic reply never runs peer-wide local accounting")
            nagramiXReadAfterUserAction(account: scoped, peerId: channel, upTo: id(105, peerId: channel)).start()
            check(!nagramiXHasPrivateRead(transaction: storage, peerId: channel, threadId: 100) && nagramiXHasPrivateRead(transaction: storage, peerId: channel, threadId: 2), "full reply in second topic retires only second marker")
            let restarted = Transaction(); restarted.values = storage.values
            check(nagramiXHasPrivateRead(transaction: restarted, peerId: channel, threadId: 2) && !nagramiXHasPrivateRead(transaction: restarted, peerId: channel, threadId: 100), "encoded scoped markers survive Postbox boundary reload")
            let calls = scoped.network.discussionRequests.count
            nagramiXReadAfterUserAction(account: scoped, peerId: channel, upTo: id(6, peerId: channel), threadId: 100).start()
            check(scoped.network.discussionRequests.count == calls, "captured topic/message mismatch is rejected")
            let scheduled = EnqueueMessage.message("later", [OutgoingScheduleInfoMessageAttribute()], 0, 0, 2, nil, 0, 0, 0, 0)
            check(nagramiXReadBoundaryBeforeEnqueue(transaction: storage, peerId: channel, message: scheduled) == nil, "scheduled item captures no action permission")
            let forward = EnqueueMessage.forward(id(3), 2, 0, [], 0)
            check(nagramiXReadBoundaryBeforeEnqueue(transaction: storage, peerId: channel, message: forward)?.messageId == id(6, peerId: channel), "forward uses destination topic, not source chat")
            let absent = EnqueueMessage.message("empty topic", [], 0, 0, 999, nil, 0, 0, 0, 0)
            check(nagramiXReadBoundaryBeforeEnqueue(transaction: storage, peerId: channel, message: absent) == nil, "missing topic top never falls back to whole peer")
            scoped.network.reject = true
            nagramiXReadAfterUserAction(account: scoped, peerId: channel, upTo: id(6, peerId: channel)).start()
            check(nagramiXHasPrivateRead(transaction: storage, peerId: channel, threadId: 2), "topic RPC failure retains marker")
            scoped.network.reject = false
            scoped.postbox.beforeEmission = { settings(local: true, action: false) }
            nagramiXReadAfterUserAction(account: scoped, peerId: channel, upTo: id(6, peerId: channel)).start()
            check(scoped.network.discussionRequests.count == calls + 1, "OFF between local commit and request suppresses topic receipt")
        }
        settings(local: true, action: true)
        let mono = Account(); let subPeer = PeerId(namespace: Namespaces.Peer.CloudUser, value: 25)
        seed(mono, peerId: channel, thread: subPeer.toInt64())
        mono.postbox.storage.peers[channel] = TelegramChannel(id: channel, flags: .isMonoforum)
        mono.postbox.storage.peers[subPeer] = Peer(id: subPeer)
        nagramiXReadAfterUserAction(account: mono, peerId: channel, upTo: id(5, peerId: channel)).start()
        check(mono.network.savedRequests.last?.0 == 25 && mono.network.savedRequests.last?.1 == 5 && mono.network.requests.isEmpty && mono.network.discussionRequests.isEmpty, "monoforum uses native readSavedHistory scope exclusively")
        let invalid = Int64(Int32.max) + 1
        seed(mono, peerId: channel, thread: invalid)
        mono.postbox.storage.peers[channel] = TelegramChannel(id: channel)
        nagramiXReadAfterUserAction(account: mono, peerId: channel, upTo: id(5, peerId: channel)).start()
        check(mono.network.discussionRequests.isEmpty && mono.network.requests.isEmpty && nagramiXHasPrivateRead(transaction: mono.postbox.storage, peerId: channel, threadId: invalid), "invalid discussion id is not clamped into a different topic")
        let batch = Account(); seed(batch, peerId: channel, thread: 2)
        let batchBoundary = nagramiXReadBoundaryBeforeEnqueue(transaction: batch.postbox.storage, peerId: channel, message: .message("reply", [], 0, 0, 2, nil, 0, 0, 0, 0))!
        productionReadAfterEnqueue(account: batch, peerId: channel, resultIds: [nil], nagramiXReadBoundaries: [batchBoundary])
        check(batch.network.discussionRequests.isEmpty, "failed enqueue authorizes no receipt")
        productionReadAfterEnqueue(account: batch, peerId: channel, resultIds: [id(20), id(21), id(22)], nagramiXReadBoundaries: [batchBoundary, nil, batchBoundary])
        check(batch.network.discussionRequests.count == 1 && batch.network.requests.isEmpty, "actual enqueue completion dispatches only successful, unique scoped boundaries")
        let ordinaryChannel = Account(); seed(ordinaryChannel, peerId: channel)
        ordinaryChannel.network.channelResult = .boolFalse
        nagramiXReadAfterUserAction(account: ordinaryChannel, peerId: channel, upTo: id(5, peerId: channel)).start()
        check(nagramiXHasPrivateRead(transaction: ordinaryChannel.postbox.storage, peerId: channel) && ordinaryChannel.network.discussionRequests.isEmpty, "ordinary channel false result retains peer marker")
        ordinaryChannel.network.channelResult = .boolTrue
        nagramiXReadAfterUserAction(account: ordinaryChannel, peerId: channel, upTo: id(5, peerId: channel)).start()
        check(!nagramiXHasPrivateRead(transaction: ordinaryChannel.postbox.storage, peerId: channel) && ordinaryChannel.network.requests.count == 2, "ordinary channel still uses only native channel-wide history")
        let missingSubPeer = Account(); seed(missingSubPeer, peerId: channel, thread: subPeer.toInt64())
        missingSubPeer.postbox.storage.peers[channel] = TelegramChannel(id: channel, flags: .isMonoforum)
        nagramiXReadAfterUserAction(account: missingSubPeer, peerId: channel, upTo: id(5, peerId: channel)).start()
        check(missingSubPeer.network.requests.isEmpty && missingSubPeer.network.discussionRequests.isEmpty && missingSubPeer.network.savedRequests.isEmpty, "missing monoforum peer never falls back to broad acknowledgement")
        settings(local: true, action: false)
        check(nagramiXReadBoundaryBeforeEnqueue(transaction: batch.postbox.storage, peerId: channel, message: .message("reply", [], 0, 0, 2, nil, 0, 0, 0, 0)) == nil, "disabled action reading captures no enqueue boundary")
        let visible = Account(); seed(visible, peerId: channel, thread: 2)
        _ = nagramiXRecordPrivateRead(transaction: visible.postbox.storage, index: index(50, peerId: channel))
        _ = nagramiXRecordPrivateRead(transaction: visible.postbox.storage, index: index(105, peerId: channel), threadId: 100)
        productionAcknowledgeVisibleThread(account: visible, peerId: channel, threadId: 2, messageIndex: index(5, peerId: channel), result: .boolFalse).start()
        check(nagramiXHasPrivateRead(transaction: visible.postbox.storage, peerId: channel, threadId: 2), "false native visible-thread result cannot retire marker")
        productionAcknowledgeVisibleThread(account: visible, peerId: channel, threadId: 2, messageIndex: index(3, peerId: channel), result: .boolTrue).start()
        check(nagramiXHasPrivateRead(transaction: visible.postbox.storage, peerId: channel, threadId: 2), "partial native visible-thread success preserves later private watermark")
        productionAcknowledgeVisibleThread(account: visible, peerId: channel, threadId: 2, messageIndex: index(5, peerId: channel), result: .boolTrue).start()
        check(!nagramiXHasPrivateRead(transaction: visible.postbox.storage, peerId: channel, threadId: 2) && nagramiXHasPrivateRead(transaction: visible.postbox.storage, peerId: channel, threadId: 100) && nagramiXHasPrivateRead(transaction: visible.postbox.storage, peerId: channel), "native visible success retires exactly one topic, keeps other topic and legacy markers")
        settings(local: true, action: true)
        let general = Account(); seed(general, peerId: channel, thread: 1)
        general.postbox.storage.messages[id(105, peerId: channel)] = Message(index: index(105, peerId: channel), threadId: 100)
        let generalSend = EnqueueMessage.message("general", [], 0, 0, nil, nil, 0, 0, 0, 0)
        let generalBoundary = nagramiXReadBoundaryBeforeEnqueue(transaction: general.postbox.storage, peerId: channel, message: generalSend)
        check(generalBoundary?.threadId == 1 && generalBoundary?.messageId.id == 5, "nil outgoing forum topic resolves to native General, never peer top105")
        let replyTopic = EnqueueMessage.message("reply", [], 0, 0, nil, EngineMessageReplySubject(messageId: id(105, peerId: channel)), 0, 0, 0, 0)
        check(nagramiXReadBoundaryBeforeEnqueue(transaction: general.postbox.storage, peerId: channel, message: replyTopic)?.threadId == 100, "forum reply derives its actual destination topic")
        general.postbox.storage.messages[id(200, peerId: channel)] = Message(index: index(200, peerId: channel), threadId: nil)
        nagramiXReadAfterUserAction(account: general, peerId: channel, upTo: id(200, peerId: channel)).start()
        check(general.network.requests.isEmpty && general.network.discussionRequests.isEmpty, "unknown forum message scope never permits peer-wide acknowledgement")
        general.postbox.storage.messages[id(2, peerId: channel)] = Message(index: index(2, peerId: channel), threadId: nil)
        nagramiXReadAfterUserAction(account: general, peerId: channel, upTo: id(2, peerId: channel), threadId: 2).start()
        check(general.network.requests.isEmpty && general.network.discussionRequests.last?.0 == 2, "captured topic root context survives a root message without thread metadata")
        general.isSupportUser = true
        check(!productionSupportReadAllowed(account: general), "private support account skips automatic peer-wide enqueue read")
        settings(local: false, action: true)
        check(!productionSupportReadAllowed(account: general), "standalone action mode also blocks automatic support peer read")
        settings(local: false, action: false)
        check(productionSupportReadAllowed(account: general), "ordinary support behavior remains enabled outside private reading")
        settings(local: false, action: false)
        var observed: [NagramiXReadMode] = []
        let subscription = nagramiXReadModeSignal().start(next: { observed.append($0) })
        settings(local: true, action: false); settings(local: true, action: true); settings(local: false, action: true)
        subscription.dispose(); settings(local: true, action: true)
        check(observed == [.standard, .local, .standard], "mode signal observes changes, deduplicates and disposes")
        print("PASS: \(checks) production scoped action/read acknowledgement checks with account/network/transaction doubles")
    }
}
