import Foundation

// In-memory Postbox, presentation and transport boundaries. Store decisions and the
// chat's actual subscription/confirmation methods are injected by the validator.
enum NoError: Error {}
struct PeerId: Hashable {
    var id: Int64
    var namespace: Int
    init(_ value: Int64) { id = value; namespace = value == 100 ? 1 : 0 }
    func toInt64() -> Int64 { id }
}
struct MessageId: Hashable, Comparable {
    let peerId: PeerId
    let id: Int
    static func < (lhs: Self, rhs: Self) -> Bool { lhs.id < rhs.id }
}
enum Namespaces { enum Peer { static let CloudChannel = 1 } }
struct Disposable { var dispose: () -> Void = {} }
final class MetaDisposable {
    private var current: Disposable?
    func set(_ next: Disposable?) { current?.dispose(); current = next }
}
struct Signal<V, E> {
    let observe: (@escaping (V) -> Void) -> Disposable
    static func single(_ value: V) -> Self { Self { f in f(value); return Disposable() } }
    func startStrict(next: @escaping (V) -> Void) -> Disposable { observe(next) }
    func startStandalone(next: @escaping (V) -> Void) -> Disposable { observe(next) }
}
infix operator |>: AdditionPrecedence
func |> <V,R>(v: V, f: (V) -> R) -> R { f(v) }
func deliverOnMainQueue<V,E>(_ s: Signal<V,E>) -> Signal<V,E> { s }
func mapToSignal<V,R,E>(_ f: @escaping (V) -> Signal<R,E>) -> (Signal<V,E>) -> Signal<R,E> {
    { input in Signal { receive in
        let inner = MetaDisposable()
        let outer = input.observe { inner.set(f($0).observe(receive)) }
        return Disposable { outer.dispose(); inner.set(nil) }
    } }
}
enum PostboxViewKey: Hashable { case messages(Set<MessageId>), cachedPeerDataWithMessages(peerId: PeerId) }
struct Message {}
struct CachedChannelData { var sendAsPeerId: PeerId? }
struct MessagesView { var messages: [MessageId: Message] }
struct CachedPeerDataView { var cachedPeerData: Any? }
struct View { var views: [PostboxViewKey: Any] }
struct EnginePeer {
    var compactDisplayTitle: String
    init(_ title: String) { compactDisplayTitle = title }
}
final class DB {
    var messages: [MessageId: Message] = [:]
    var channel: CachedChannelData?
    var listeners: [UUID: () -> Void] = [:]
    func getPeer(_ id: PeerId) -> String? { "peer-\(id.id)" }
    func transaction<V>(_ f: (DB) -> V) -> Signal<V,NoError> { .single(f(self)) }
    func combinedView(keys: [PostboxViewKey]) -> Signal<View,NoError> {
        Signal { f in
            let token = UUID()
            func emit() {
                var view = View(views: [:])
                for k in keys {
                    switch k {
                    case let .messages(ids): view.views[k] = MessagesView(messages: self.messages.filter { ids.contains($0.key) })
                    case .cachedPeerDataWithMessages: view.views[k] = CachedPeerDataView(cachedPeerData: self.channel)
                    }
                }
                f(view)
            }
            self.listeners[token] = emit
            emit()
            return Disposable { self.listeners.removeValue(forKey: token) }
        }
    }
    func changed() { for emit in Array(listeners.values) { emit() } }
}
struct Value { var value: String? }
struct Record {
    var messageId: MessageId
    var peerId: Int64 { messageId.peerId.toInt64() }
    var threadId: Int64?
    var sendAsPeerId: Int64?
    var revision: UInt32
    var reactions = [Value(value: "ok")]
    var isLarge = false
    var storeAsRecentlyUsed = false
}
final class NagramiXDeferredReactionsStore {
    let accountPeerId = PeerId(1)
    let lock = NSLock()
    var records: [String: Record] = [:]
    var revision: UInt32 = 0
    var inFlight: Set<Intent> = []
    var retryAfterFlight: Set<Intent> = []
    var changed: () -> Void = {}
    static func key(_ id: MessageId) -> String { "\(id.peerId.id):\(id.id)" }
    func publish() { changed() }
    func stage(_ id: MessageId, _ sender: PeerId) {
        revision += 1
        records[Self.key(id)] = Record(messageId: id, sendAsPeerId: sender.id, revision: revision)
        publish()
    }
    // STORE
}
final class Archive { let deferredReactions = NagramiXDeferredReactionsStore() }
final class Account {
    let nagramiXMessageArchive = Archive()
    let postbox = DB()
    let peerId = PeerId(1)
    var sent: [(MessageId,PeerId)] = []
    var delay = false
    var transactions: [() -> Void] = []
}
func nagramiXEnqueueReactions(account: Account, messageIds: [MessageId], reactions: [String], isLarge: Bool, storeAsRecentlyUsed: Bool, add: Bool, expectedSender: PeerId?, shouldApply: (() -> Bool)?) -> Signal<Bool,NoError> {
    Signal { receive in
        let perform = {
            if let shouldApply, !shouldApply() { receive(false); return }
            let messageIds = messageIds.filter { account.postbox.messages[$0] != nil }
            let sendAsPeerId = account.postbox.channel?.sendAsPeerId ?? account.peerId
            // NATIVE GUARD
            account.sent.append(contentsOf: messageIds.map { ($0, sendAsPeerId) })
            receive(true)
        }
        if account.delay { account.transactions.append(perform) } else { perform() }
        return Disposable()
    }
}
struct TextAlertAction {
    enum Kind { case genericAction, defaultAction }
    var type: Kind
    var title: String
    var action: () -> Void
}
final class AlertController {
    var actions: [TextAlertAction] = []
    var text = ""
    var dismissed: ((Bool) -> Void)?
    func dismiss() { dismissed?(false) }
}
struct Strings {
    let PeerInfo_AllowedReactions_Title = "Reactions", Conversation_SendMesageAs = "Send as…", Common_Cancel = "Cancel", Common_OK = "OK"
}
struct Context { let account = Account() }
struct Presentation { let strings = Strings() }
struct Place { var peerId: PeerId? = PeerId(100); var threadId: Int64? }
enum ChatMode { enum Style { case `default` }; case standard(Style) }
struct InterfaceState { var mode = ChatMode.standard(.default) }
enum ChatSubject { case message, search }
enum PresentationLocation { enum Window { case root }; case window(Window) }
final class Navigation { weak var topViewController: Chat? }
func textAlertController(context: Context, title: String, text: String, actions: [TextAlertAction], dismissOnOutsideTap: Bool) -> AlertController {
    precondition(!dismissOnOutsideTap)
    let alert = AlertController(); alert.actions = actions; alert.text = text; return alert
}
final class Chat {
    let context = Context(), presentationData = Presentation(), presentationInterfaceState = InterfaceState()
    var subject: ChatSubject?
    let effectiveNavigationController: Navigation? = Navigation()
    var chatLocation = Place()
    var nagramiXReadHistoryDisabled = false, nagramiXVisibleForDeferredReactions = true, isUpdatingChatLocationThread = false, canReadHistoryValue = true
    var alerts: [AlertController] = []
    func present(_ alert: AlertController, in location: PresentationLocation) { alerts.append(alert) }
    // CHAT
}
@main enum Checks {
    static func main() {
        let chat = Chat(), db = chat.context.account.postbox, account = chat.context.account
        let store = account.nagramiXMessageArchive.deferredReactions
        chat.effectiveNavigationController?.topViewController = chat
        store.changed = { [weak chat] in chat?.nagramiXFlushDeferredReactionsIfActive() }
        let id = MessageId(peerId: PeerId(100), id: 10), a = PeerId(2), b = PeerId(3)
        db.channel = CachedChannelData(sendAsPeerId: a)
        store.stage(id, a)
        precondition(store.records.count == 1 && account.sent.isEmpty)
        db.messages[id] = Message(); db.changed()
        precondition(store.records.isEmpty && account.sent.count == 1 && account.sent[0].1 == a)

        db.channel = CachedChannelData(sendAsPeerId: b)
        store.stage(id, a); db.changed()
        precondition(chat.alerts.count == 1 && chat.alerts[0].text.contains("peer-2 → peer-3"))
        chat.alerts[0].actions[0].action()
        precondition(store.records.isEmpty && account.sent.count == 1)
        store.stage(id, a)
        let staleAlert = chat.alerts.last!
        store.stage(id, a)
        staleAlert.actions[1].action()
        precondition(account.sent.count == 1 && store.records.count == 1)
        chat.alerts.last!.actions[1].action()
        precondition(account.sent.count == 2 && account.sent.last!.1 == b && store.records.isEmpty)

        account.delay = true
        store.stage(id, b)
        db.channel = CachedChannelData(sendAsPeerId: a)
        account.transactions.removeFirst()()
        precondition(account.sent.count == 2 && store.records.count == 1)
        db.changed()
        let whileVisible = chat.alerts.last!
        chat.nagramiXVisibleForDeferredReactions = false; chat.nagramiXFlushDeferredReactionsIfActive()
        whileVisible.actions[1].action()
        precondition(account.sent.count == 2 && store.records.count == 1 && db.listeners.isEmpty)
        chat.nagramiXVisibleForDeferredReactions = true; chat.nagramiXFlushDeferredReactionsIfActive()
        chat.alerts.last!.actions[1].action()
        db.messages.removeAll(); account.transactions.removeFirst()()
        precondition(store.records.count == 1 && account.sent.count == 2)
        account.delay = false
        db.messages[id] = Message(); db.changed()
        precondition(store.records.isEmpty && account.sent.count == 3 && account.sent.last!.1 == a)
        print("PASS delayed messages, sender confirmation, cancellation, stale choice, active chat and native enqueue races")
    }
}
