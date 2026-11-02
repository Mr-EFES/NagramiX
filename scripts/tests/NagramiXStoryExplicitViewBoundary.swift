import Foundation

// UIKit, Postbox и сеть — границы; SignalKit и вставляемые методы production.
public final class Queue {
    public let queue = DispatchQueue(label: "story-test-boundary")
    public static func mainQueue() -> Queue { Queue() }
    public static func concurrentDefaultQueue() -> Queue { Queue() }
    public func async(_ action: @escaping () -> Void) { action() }
}
func deliverOnMainQueue<T,E>(_ signal: Signal<T,E>) -> Signal<T,E> { signal }
public func deliverOn<T,E>(_ queue: Queue) -> (Signal<T,E>) -> Signal<T,E> { { $0 } }
struct PeerId: Hashable { let value: Int64; func toInt64() -> Int64 { value } }
struct EngineStoryId: Hashable { let peerId: PeerId; let id: Int32 }
struct Peer { let id: PeerId }
enum Api {
    struct InputPeer: Equatable { let id: PeerId }
    enum Bool { case boolTrue, boolFalse }
    struct Request { let peer: InputPeer; let ids: [Int32] }
    enum functions { enum stories {
        static func incrementStoryViews(peer: InputPeer, id: [Int32]) -> Request { Request(peer: peer, ids: id) }
    } }
}
func apiInputPeer(_ peer: Peer) -> Api.InputPeer? { Api.InputPeer(id: peer.id) }
enum RpcError: Error { case failed }
final class Network {
    var requests: [Api.Request] = []
    var subscribers: [Subscriber<Api.Bool, RpcError>] = []
    func request(_ request: Api.Request) -> Signal<Api.Bool, RpcError> {
        requests.append(request)
        return Signal { subscriber in self.subscribers.append(subscriber); return EmptyDisposable }
    }
    func finish(_ success: Bool, error: Bool = false) {
        let subscriber = subscribers.removeFirst()
        if error { subscriber.putError(.failed) }
        else { subscriber.putNext(success ? .boolTrue : .boolFalse); subscriber.putCompletion() }
    }
}
final class Transaction {
    var missing = false
    func getPeer(_ id: PeerId) -> Peer? { missing ? nil : Peer(id: id) }
}
final class Postbox {
    let value = Transaction()
    var transactions = 0
    func transaction<T>(_ f: @escaping (Transaction) -> T) -> Signal<T, NoError> {
        Signal { subscriber in
            self.transactions += 1; subscriber.putNext(f(self.value)); subscriber.putCompletion(); return EmptyDisposable
        }
    }
}
final class Account {
    let peerId: PeerId
    let network = Network()
    let postbox = Postbox()
    init(_ id: Int64 = 1) { peerId = PeerId(value: id) }
}
final class Messages {
    let account: Account
    init(_ account: Account) { self.account = account }
    // ENGINE_METHOD
}
struct Engine { let messages: Messages }
struct Theme { var contextMenu: Theme { self }; var primaryColor: Int { 0 } }
struct PresentationData { func withUpdated(theme: Theme) -> PresentationData { self } }
struct DataPromise { func with<T>(_ f: (PresentationData) -> T) -> T { f(PresentationData()) } }
struct SharedContext { var currentPresentationData: DataPromise { DataPromise() } }
final class AccountContext {
    let account: Account
    let engine: Engine
    let sharedContext = SharedContext()
    var errors: [String] = []
    init(_ account: Account = Account()) { self.account = account; self.engine = Engine(messages: Messages(account)) }
}
struct UIImage {
    enum Mode { case alwaysOriginal }
    init?(systemName: String) {}
    func withTintColor(_ color: Int, renderingMode: Mode) -> UIImage { self }
}
enum ContextMenuActionItemTextColor { case primary, disabled }
final class ContextMenuActionItem {
    enum Result { case `default` }
    final class Action { func dismissWithResult(_ result: Result) {} }
    let text: String
    let action: ((Action) -> Void)?
    init(text: String, textColor: ContextMenuActionItemTextColor, icon: (Theme) -> UIImage?, action: ((Action) -> Void)?) {
        self.text = text; self.action = action
    }
}
enum ContextMenuItem { case action(ContextMenuActionItem) }
enum ToastContent { case info(title: String?, text: String, timeout: Double?, customUndoText: String?) }
final class UndoOverlayController {
    let text: String
    init(presentationData: PresentationData, content: ToastContent, elevatedLayout: Bool, animateInAsReplacement: Bool, action: (Int) -> Bool) {
        switch content { case let .info(_, text, _, _): self.text = text }
    }
}
struct Strings {
    let nagramiXStoryRecordView = "Засчитать просмотр"
    let nagramiXStoryRecordingView = "Засчитываем просмотр…"
    let nagramiXStoryViewRecorded = "Просмотр засчитан"
    let nagramiXStoryServerStealthActive = "Server stealth active"
    let nagramiXStoryRecordViewFailed = "Failed"
}
enum Media { case video, liveStream }
struct StoryItem { var media = Media.video }
struct SliceItem { let id: EngineStoryId; var storyItem = StoryItem() }
struct Slice { var item: SliceItem; var effectivePeer: Peer }
final class StoryItemSetContainerComponent {
    let context: AccountContext
    var slice: Slice
    let nagramiXViewDisclosure: NagramiXStoryViewDisclosure
    var nagramiXAnonymousViewing = true
    var isCentral = true
    var isDismissed = false
    var stealthModeTimeout: Int32?
    let strings = Strings()
    let theme = Theme()
    init(_ context: AccountContext, _ id: EngineStoryId, _ disclosure: NagramiXStoryViewDisclosure = NagramiXStoryViewDisclosure()) {
        self.context = context; slice = Slice(item: SliceItem(id: id), effectivePeer: Peer(id: id.peerId)); nagramiXViewDisclosure = disclosure
    }
    func presentController(_ controller: UndoOverlayController, _ unused: Int?) { context.errors.append(controller.text) }
    // COMPONENT_PROPERTIES
}
struct Transition { static let immediate = Transition() }
final class State { var updates = 0; func updated(transition: Transition) { updates += 1 } }
final class StoryViewHarness {
    var component: StoryItemSetContainerComponent?
    var state: State? = State()
    init(_ component: StoryItemSetContainerComponent) { self.component = component }
    // MENU_METHODS
    func entry(_ snapshot: StoryItemSetContainerComponent) -> ContextMenuActionItem {
        guard case let .action(item) = nagramiXRecordViewItem(snapshot) else { fatalError() }; return item
    }
    func tap(_ snapshot: StoryItemSetContainerComponent) { entry(snapshot).action?(ContextMenuActionItem.Action()) }
}
