import Foundation

// UI/engine boundaries only. The validator inserts native selection, draft
// preflight, routing and copy-dispatch code verbatim into these test classes.
typealias MessageId = Int
typealias PeerId = Int
struct User { let id: Int; var botInfo: Int? = nil }
struct Channel { let id: Int; var isForumOrMonoForum = false }
enum EnginePeer {
    typealias Id = Int
    case user(User), channel(Channel), community(Int)
    var id: Int { switch self { case let .user(p): return p.id; case let .channel(p): return p.id; case let .community(id): return id } }
}
struct Message { let id: Int; var ownOnce = false
    func nagramiXAllowsOwnViewOnceCopy(accountPeerId: Int?) -> Bool { ownOnce && accountPeerId == 100 }
}
struct EngineMessage { let value: Message; func _asMessage() -> Message { value } }
struct ChatLocation: Equatable { var peerId: Int? = 1; var threadId: Int64? = nil }
struct Draft: Equatable { var forwardMessageIds: [Int]? = [1]; var editMessage: Int? = nil; var version = 0; var forwardOptionsState: ForwardOptions? = nil }
struct ForwardOptions: Equatable { var hideCaptions = false }
enum Subject { case scheduledMessages, ordinary }
struct PresentationState { var interfaceState = Draft(); var subject = Subject.ordinary }
final class InputPanel { var inputTextState = 0 }
struct ChatSendMessageEffect {}
enum NoError {}
final class Signal<T,E> {
    let onStart: (@escaping (T) -> Void) -> Void
    init(_ onStart: @escaping (@escaping (T) -> Void) -> Void) { self.onStart = onStart }
    @discardableResult func startStandalone(next: @escaping (T) -> Void) -> Int { onStart(next); return 0 }
}
precedencegroup PipeRight {
    associativity: left
    higherThan: DefaultPrecedence
}
infix operator |> : PipeRight
func |> <A,B>(value: A, transform: (A) -> B) -> B { transform(value) }
func take<T,E>(_ count: Int) -> (Signal<T,E>) -> Signal<T,E> { { $0 } }
func deliverOnMainQueue<T,E>(_ value: Signal<T,E>) -> Signal<T,E> { value }
enum TelegramEngine { enum EngineData { enum Item {
    enum Messages { struct Message { let id: Int; init(_ id: Int) { self.id = id } } }
    enum Peer { struct Peer { let id: Int }; struct SendPaidMessageStars { let id: Int } }
} } }
struct EngineDataMap { let ids: [TelegramEngine.EngineData.Item.Messages.Message]; init(_ ids: [TelegramEngine.EngineData.Item.Messages.Message]) { self.ids = ids } }
final class DataEngine {
    typealias Result = ([Int:EngineMessage?], EnginePeer?, Int?)
    var observers: [(Result) -> Void] = []; var queries = 0
    func get(_ map: EngineDataMap, _ peer: TelegramEngine.EngineData.Item.Peer.Peer, _ stars: TelegramEngine.EngineData.Item.Peer.SendPaidMessageStars) -> Signal<Result, NoError> {
        queries += 1
        return Signal { self.observers.append($0) }
    }
    func emit(_ originals: [Message] = [Message(id: 1, ownOnce: true)], peer: EnginePeer? = .user(User(id: 200)), stars: Int? = nil) {
        let next = observers; observers = []
        next.forEach { $0((Dictionary(uniqueKeysWithValues: originals.map { ($0.id, Optional(EngineMessage(value: $0))) }), peer, stars)) }
    }
}
final class Engine { let data = DataEngine() }
final class Account { let peerId = 100; let postbox = Postbox() }
final class Postbox { let mediaBox = 0 }
final class Context { let engine = Engine(); let account = Account() }
final class Interaction { var alerts = 0; func presentController(_ value: Int, _ surface: Int?) { alerts += 1 } }
func nagramiXArchivedCopyAlert(context: Context) -> Int { 1 }
var copyAvailable = true
// The real copier, resource staging, TTL and ownership are executed separately
// by validate_own_once_copy; here only the native Send dispatch is under test.
enum EnqueueMessage {
    enum Grouping { case auto }
    case message(id: Int, once: Bool, local: Bool, threadId: Int64?)
    case forward(source: Int, threadId: Int64?, grouping: Grouping, attributes: [Int], correlationId: Int64?)
    func withUpdatedThreadId(_ value: Int64?) -> EnqueueMessage {
        switch self { case let .message(id, once, local, _): return .message(id: id, once: once, local: local, threadId: value)
        case let .forward(id, _, grouping, attributes, correlation): return .forward(source: id, threadId: value, grouping: grouping, attributes: attributes, correlationId: correlation) }
    }
}
func nagramiXCopyMessagesAsNew(_ messages: [Message], mediaBox: Int, hideCaptions: Bool, forceLocalMedia: Bool, accountPeerId: Int) -> [EnqueueMessage]? {
    guard copyAvailable else { return nil }
    return messages.map { .message(id: $0.id, once: $0.ownOnce, local: forceLocalMedia, threadId: nil) }
}
enum ContactListPeerId: Hashable { case peer(Int) }
enum ContactListPeer: Equatable {
    case peer(peer: EnginePeer, isGlobal: Bool, participantCount: Int?)
    var id: ContactListPeerId { switch self { case let .peer(peer, _, _): return .peer(peer.id) } }
    static func ==(lhs: Self, rhs: Self) -> Bool { lhs.id == rhs.id }
}
final class Contacts {
    var multipleSelection = false; var nagramiXSelectionLimit: Int? = nil
    var state: ContactListNodeGroupSelectionState? = nil
    func updateSelectionState(_ f: (ContactListNodeGroupSelectionState?) -> ContactListNodeGroupSelectionState?) { state = f(state) }
    var selectedPeers: [ContactListPeer] { guard let state else { return [] }; return state.selectedPeerIndices.sorted { $0.value < $1.value }.compactMap { state.selectedPeerMap[$0.key] } }
}
struct ListState { var editing = false; var selectedPeerIds = Set<Int>(); var selectedPeerMap: [Int:EnginePeer] = [:]; var foundPeers: [(EnginePeer, EnginePeer?)] = [] }
final class Chats { var state = ListState(); var selectionLimit = 1000; func updateState(_ f: (ListState) -> ListState) { state = f(state) } }
final class Container { let currentItemNode = Chats() }
final class SelectionController { var multipleSelectionLimit: Int? = nil }
final class SendPanel { var enabled = false; func updateSendButtonEnabled(_ value: Bool, animated: Bool) { enabled = value } }
