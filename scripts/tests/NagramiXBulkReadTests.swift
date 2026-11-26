// Deterministic adapters for the Postbox transaction, RPC and scheduler APIs.
// The production capture, network routing, acknowledgements and retry code run above main.
typealias PeerReadState = BulkTestReadState
typealias MTRpcError = TestNetworkError
enum PeerGroupId { case root, archive }
extension Namespaces {
    enum PeerGroup { static let archive = PeerGroupId.archive }
}
extension Namespaces.Message { static let SecretIncoming: Int32 = 4 }
extension Peer {
    var isMonoForum: Bool { (self as? TelegramChannel)?.flags.contains(.isMonoforum) ?? false }
}
extension Transaction {
    func preferenceKeys(withPrefix key: ValueBoxKey) -> [ValueBoxKey] {
        values.keys.filter { $0.getInt64(0) == key.getInt64(0) }
    }
    func getChatListPeers(groupId: PeerGroupId, filterPredicate: Never?, additionalFilter: Never?) -> [Peer] {
        peers.values.filter { (groupId == .archive) == archived.contains($0.id) }
    }
    func getPeerReadStates(_ id: PeerId) -> [(Int32, PeerReadState)]? {
        bulkStates[id]?.map { ($0.key, $0.value) }
    }
    func setLocalReadState(peerId: PeerId, namespace: Int32, state: PeerReadState) {
        bulkStates[peerId, default: [:]][namespace] = state
    }
}
enum TestConnectionStatus { case waitingForNetwork, online }
extension TestNetwork { var connectionStatus: Signal<TestConnectionStatus, NoError> { .single(offline ? .waitingForNetwork : .online) } }
func take<T, E>(_ count: Int) -> (Signal<T, E>) -> Signal<T, E> { { $0 } }
extension Api {
    struct DialogData { let peer: InputPeer }
    enum Dialog { case inputDialogPeer(DialogData) }
}
extension Api.functions.messages {
    static func markDialogUnread(flags: Int32, parentPeer: Api.InputPeer?, peer: Api.Dialog) -> TestRequest<Api.Bool> {
        precondition(flags == 0 || flags == 1)
        return TestRequest(peer: -1, maxId: flags, response: { _ in .boolTrue })
    }
    static func readEncryptedHistory(peer: PeerId, maxDate: Int32) -> TestRequest<Api.Bool> {
        TestRequest(peer: peer.value, maxId: maxDate, response: { _ in .boolTrue })
    }
}
func apiInputSecretChat(_ peer: Peer) -> PeerId? { peer.id }
func filter<T, E>(_ accepts: @escaping (T) -> Bool) -> (Signal<T, E>) -> Signal<T, E> {
    { source in Signal { sub in source.start(next: { if accepts($0) { sub.putNext($0) } }, error: sub.putError, completed: sub.putCompletion) } }
}
func combineLatest<T, E>(_ signals: [Signal<T, E>]) -> Signal<[T], E> {
    Signal { sub in
        var results: [T] = []
        for signal in signals { signal.start(next: { results.append($0) }) }
        precondition(results.count == signals.count)
        sub.putNext(results)
        sub.putCompletion()
        return emptyDisposable
    }
}
func switchToLatest<T, E>(_ signals: Signal<Signal<T, E>, E>) -> Signal<T, E> { signals |> mapToSignal { $0 } }
final class MetaDisposable: Disposable { func set(_ value: Disposable) {} ; func dispose() {} }
final class Queue {
    static func concurrentDefaultQueue() -> Queue { Queue() }
    func async(_ block: @escaping () -> Void) { block() }
}
func deliverOn<T, E>(_ queue: Queue) -> (Signal<T, E>) -> Signal<T, E> { { $0 } }
func timeout<T, E>(_ seconds: Double, queue: Queue, alternate: Signal<T, E>) -> (Signal<T, E>) -> Signal<T, E> { { $0 } }

@main struct BulkReadTests {
    static func main() {
        let account = Account()
        let db = account.postbox.storage
        let dm = PeerId(namespace: 0, value: 7)
        let other = PeerId(namespace: 0, value: 8)
        let secret = PeerId(namespace: Namespaces.Peer.SecretChat, value: 9)
        let forum = PeerId(namespace: Namespaces.Peer.CloudChannel, value: 20)
        db.peers = [dm: Peer(id: dm), other: Peer(id: other), secret: Peer(id: secret), forum: TelegramChannel(id: forum)]
        db.archived.insert(dm)
        func unread(_ peer: PeerId, maxId: Int32, incoming: Int32, marked: Bool = false) {
            db.bulkStates[peer] = [0: .idBased(maxIncomingReadId: incoming, maxOutgoingReadId: 2, maxKnownId: maxId, count: maxId-incoming, markedUnread: marked)]
        }
        unread(dm, maxId: 19, incoming: 5)
        unread(other, maxId: 3, incoming: 3, marked: true)
        let first = MessageIndex(id: MessageId(peerId: secret, namespace: 4, id: 1), timestamp: 10)
        let last = MessageIndex(id: MessageId(peerId: secret, namespace: 4, id: 2), timestamp: 20)
        db.messages[last.id] = Message(index: last, threadId: nil)
        db.bulkStates[secret] = [4: .indexBased(maxIncomingReadIndex: first, maxOutgoingReadIndex: first, count: 1, markedUnread: false)]
        for i in 1 ... 108 {
            db.threads[forum, default: [:]][Int64(i)] = MessageHistoryThreadData(maxIncomingReadId: 10, incomingUnreadCount: 1, maxKnownMessageId: Int32(20 + i))
        }
        var emitted = false
        nagramiXBulkReadMessages(account: account, onServer: false).start(next: { precondition($0 == nil); emitted = true })
        precondition(emitted && account.network.requests.isEmpty && account.network.discussionRequests.isEmpty)
        precondition(db.bulkStates.values.flatMap { $0.values }.allSatisfy { !$0.isUnread })
        precondition(db.threads[forum]!.values.allSatisfy { $0.incomingUnreadCount == 0 })
        guard case let .idBased(maximum, _, _, _, _)? = nagramiXNativePushState(transaction: db, peerId: dm, state: db.bulkStates[dm]![0]!) else { fatalError() }
        precondition(maximum == 5)
        guard case let .indexBased(secretBound, _, _, _)? = nagramiXNativePushState(transaction: db, peerId: secret, state: db.bulkStates[secret]![4]!) else { fatalError() }
        precondition(secretBound.timestamp == 10)
        account.network.offline = true
        nagramiXBulkReadMessages(account: account, onServer: true).start(next: { precondition($0 != nil) })
        precondition(account.network.requests.isEmpty && account.network.discussionRequests.isEmpty)
        account.network.offline = false
        // A server failure only for topics. The remaining batch survives newer arrivals.
        account.network.discussionResult = .boolFalse
        var retry: NagramiXBulkReadBatch?
        nagramiXBulkReadMessages(account: account, onServer: true).start(next: { retry = $0 })
        precondition(retry != nil && account.network.discussionRequests.count == 108)
        precondition(account.network.requests.contains { $0 == (7, 19) } && account.network.requests.contains { $0 == (9, 20) })
        precondition(account.network.requests.contains { $0 == (-1, 0) })
        let sent = account.network.requests.count
        unread(dm, maxId: 22, incoming: 19)
        db.threads[forum]![5]!.maxKnownMessageId = 200
        db.threads[forum]![5]!.incomingUnreadCount = 1
        nagramiXBulkReadMessages(account: account, onServer: false).start()
        account.network.discussionResult = .boolTrue
        retry!.send().start(next: { precondition($0 == nil) })
        precondition(account.network.requests.count == sent)
        precondition(account.network.discussionRequests.suffix(108).contains { $0 == (5, 25) })
        precondition(!account.network.discussionRequests.contains { $0 == (5, 200) })
        precondition(nagramiXHasPrivateRead(transaction: db, peerId: forum, threadId: 5))
        precondition(nagramiXHasPrivateRead(transaction: db, peerId: dm))
        let independent = Account()
        nagramiXBulkReadMessages(account: independent, onServer: true).start()
        precondition(independent.network.requests.isEmpty)
        print("PASS local/offline, archive, manual marks, secret date, 108 topics, failures, immutable retry, account isolation")
    }
}
