import Foundation

// The queue and result sources here let each test decide when UI work arrives.
final class Queue {
    private static let main = Queue()
    private var now = 0.0
    private var tasks: [(Double, () -> Void)] = []
    static func mainQueue() -> Queue { main }
    func async(_ action: @escaping () -> Void) { after(0.0, action) }
    func after(_ delay: Double, _ action: @escaping () -> Void) {
        tasks.append((now + delay, action))
    }
    func advance(_ seconds: Double) {
        now += seconds
        while let index = tasks.indices.filter({ tasks[$0].0 <= now }).min(by: { tasks[$0].0 < tasks[$1].0 }) {
            tasks.remove(at: index).1()
        }
    }
}

enum LookupError: Error { case unavailable }
struct Signal<Value> {
    let subscribe: (@escaping (Value) -> Void, @escaping (LookupError) -> Void) -> Disposable
    func start(next: @escaping (Value) -> Void, error: @escaping (LookupError) -> Void = { _ in }) -> Disposable {
        subscribe(next, error)
    }
}
infix operator |>
func |> <T, V>(value: T, transform: (T) -> V) -> V { transform(value) }
func deliverOnMainQueue<T>(_ signal: Signal<T>) -> Signal<T> { signal }

enum EnginePeer { typealias Id = Int }
enum EngineMessage { typealias Id = Int }
struct Message {
    let id: Int
    let author: Author?
}
struct Author { let id: Int }
final class Lookup {
    var result: (([Int]) -> Void)?
    var error: ((LookupError) -> Void)?
    var starts = 0
    var disposals = 0
    func open() -> Signal<[Int]> {
        Signal { next, failed in
            self.starts += 1
            self.result = next
            self.error = failed
            return ActionDisposable {
                self.result = nil
                self.error = nil
                self.disposals += 1
            }
        }
    }
}
final class Postbox {
    var messages: [Int: Message] = [:]
    func getMessage(_ id: Int) -> Message? { messages[id] }
    func transaction<T>(_ transform: @escaping (Postbox) -> T) -> Signal<T> {
        Signal { next, _ in
            next(transform(self))
            return ActionDisposable {}
        }
    }
}
final class Archive {
    var messages: [Message] = []
    func deletedMessages(peerId: Int, threadId: Int64?, minIndex: Int?, maxIndex: Int?, limit: Int) -> [Message] {
        messages
    }
}
final class Account {
    let lookup = Lookup()
    let postbox = Postbox()
    let nagramiXMessageArchive = Archive()
}
func nagramiXMessagesByAuthor(account: Account, peerId: Int, authorId: Int, threadId: Int64?) -> Signal<[Int]> {
    account.lookup.open()
}
enum NagramiXTabSettings {
    static var current = Settings()
    struct Settings { var showDeletedMessages = true }
}

enum ContainedViewLayoutTransition: Equatable { case immediate, spring }
enum ContextMenuActionResult: Equatable {
    case `default`
    case custom(ContainedViewLayoutTransition)
}
protocol ContextControllerProtocol: AnyObject {
    func dismiss(completion: (() -> Void)?)
}
protocol ContextController: ContextControllerProtocol {
    var dismissed: (() -> Void)? { get set }
    var dismissedForCancel: (() -> Void)? { get set }
}
final class Menu: ContextController {
    var dismissed: (() -> Void)?
    var dismissedForCancel: (() -> Void)?
    var results: [ContextMenuActionResult] = []
    var holdNormalDismissal = false
    private var normalDismissalCompletion: (() -> Void)?
    func dismiss(_ result: ContextMenuActionResult) {
        results.append(result)
        dismissed?()
    }
    func dismiss(completion: (() -> Void)?) {
        results.append(.default)
        normalDismissalCompletion = completion
        if !holdNormalDismissal {
            finishNormalDismissal()
        }
    }
    func finishNormalDismissal() {
        let completion = normalDismissalCompletion
        normalDismissalCompletion = nil
        dismissed?()
        completion?()
    }
    func closeByUser() {
        dismissedForCancel?()
        dismissed?()
    }
}
enum ContextMenuActionItem {
    struct Action {
        let controller: ContextControllerProtocol?
        let dismissWithResult: (ContextMenuActionResult) -> Void
    }
}
class ViewController {
    var dismissals = 0
    func dismiss() { dismissals += 1 }
}
final class Progress: ViewController {
    var cancel: (() -> Void)?
}
enum ProgressType { case loading(cancelled: (() -> Void)?) }
func OverlayStatusController(theme: Int, type: ProgressType) -> ViewController {
    let progress = Progress()
    if case let .loading(cancelled) = type { progress.cancel = cancelled }
    return progress
}
final class Alert: ViewController {}
struct TextAlertAction {
    enum Kind { case defaultAction }
    let type: Kind
    let title: String
    let action: () -> Void
}
func textAlertController(context: Context, updatedPresentationData: Int, title: String?, text: String, actions: [TextAlertAction]) -> Alert {
    Alert()
}
enum Window { case root }
enum PresentationLocation { case window(Window) }
enum UIAccessibility {
    enum Notification { case announcement }
    static var announcements: [String] = []
    static func post(notification: Notification, argument: String) { announcements.append(argument) }
}

struct Location {
    var peerId: Int? = 1
    var threadId: Int64?
}
struct Strings {
    let Common_OK = "OK"
    let nagramiXAuthorSelectionEmpty = "Empty"
    let nagramiXAuthorSelectionFailed = "Failed"
    func VoiceOver_Chat_MessagesSelected(_ count: Int32) -> String { "Selected \(count)" }
}
struct PresentationData {
    let theme = 0
    let strings = Strings()
}
struct DataSource {
    func with<T>(_ transform: (PresentationData) -> T) -> T { transform(PresentationData()) }
}
struct Context {
    let account = Account()
    let sharedContext = SharedContext()
    struct SharedContext { let currentPresentationData = DataSource() }
}
struct InterfaceState {
    var selectionState: Selection?
    struct Selection { let selectedIds: Set<Int> }
    func withUpdatedSelectedMessages(_ ids: [Int]) -> InterfaceState {
        InterfaceState(selectionState: Selection(selectedIds: Set(ids)))
    }
}
struct ChatPresentationInterfaceState {
    var interfaceState = InterfaceState()
    var subject: String?
    var showCommands = true
    func updatedInterfaceState(_ transform: (InterfaceState) -> InterfaceState) -> Self {
        var next = self
        next.interfaceState = transform(interfaceState)
        return next
    }
    func updatedShowCommands(_ value: Bool) -> Self {
        var next = self
        next.showCommands = value
        return next
    }
}
final class ChatControllerImpl {
    let context = Context()
    let presentationData = PresentationData()
    let updatedPresentationData = 0
    var chatLocation = Location()
    var presentationInterfaceState = ChatPresentationInterfaceState()
    var isNodeLoaded = true
    var currentContextController: ContextController?
    let nagramiXSelectAuthorDisposable = MetaDisposable()
    var nagramiXSelectAuthorGeneration: UInt64 = 0
    var nagramiXIsSelectingAuthorMessages = false
    var nagramiXSelectedAuthorMessageIds: Set<Int>?
    var presented: [ViewController] = []
    var requests = 0
    var requiresVoiceConfirmation = false
    var voiceConfirmation: (() -> Void)?
    var waitForLayout = false
    var layoutCompletion: (() -> Void)?

    func present(_ controller: ViewController, in location: PresentationLocation) { presented.append(controller) }
    func presentVoiceMessageDiscardAlert(action: @escaping () -> Void, alertAction: (() -> Void)?, delay: Bool) -> Bool {
        if requiresVoiceConfirmation {
            alertAction?()
            voiceConfirmation = action
            return true
        }
        action()
        return false
    }
    func updateChatPresentationInterfaceState(animated: Bool, interactive: Bool, _ update: (ChatPresentationInterfaceState) -> ChatPresentationInterfaceState, completion: @escaping (ContainedViewLayoutTransition) -> Void) {
        precondition(animated && interactive)
        requests += 1
        presentationInterfaceState = update(presentationInterfaceState)
        if waitForLayout {
            layoutCompletion = { completion(.spring) }
        } else {
            completion(.spring)
        }
    }
}

// ACTUAL_AUTHOR_PRESENTATION

private func check(_ condition: @autoclosure () -> Bool, _ message: String) {
    if !condition() {
        print("FAIL: \(message)")
        exit(91)
    }
}

@main enum AuthorSelectionChecks {
    private static let author = Author(id: 34)

    private static func start(ids: [Int] = [1, 2], requiresVoice: Bool = false, archived: Bool = false) -> (ChatControllerImpl, Menu) {
        let chat = ChatControllerImpl()
        let menu = Menu()
        chat.currentContextController = menu
        chat.requiresVoiceConfirmation = requiresVoice
        for id in ids { chat.context.account.postbox.messages[id] = Message(id: id, author: author) }
        let action = ContextMenuActionItem.Action(controller: menu, dismissWithResult: { [weak menu] in menu?.dismiss($0) })
        chat.checkAuthorFlow(author.id, action, archived: archived)
        return (chat, menu)
    }

    static func main() {
        do {
            let (chat, menu) = start()
            chat.waitForLayout = true
            chat.context.account.lookup.result?([2, 1, 2])
            Queue.mainQueue().advance(1.0)
            check(chat.presented.isEmpty, "quick lookup never presents a progress overlay")
            check(chat.requests == 1 && chat.nagramiXSelectedAuthorMessageIds == Set([1, 2]), "final IDs are selected in one update")
            check(menu.results.isEmpty, "menu waits for the chat layout transition")
            chat.layoutCompletion?()
            check(menu.results == [.custom(.spring)], "one native transition dismisses the menu")
            check(UIAccessibility.announcements.last == "Selected 2", "the final count is announced")
        }

        do {
            let (chat, menu) = start()
            Queue.mainQueue().advance(0.34)
            check(chat.presented.isEmpty, "HUD waits for a noticeable delay")
            Queue.mainQueue().advance(0.02)
            let progress = chat.presented.first as? Progress
            check(chat.presented.count == 1 && progress != nil && menu.results == [.default], "a slow lookup shows one HUD after the menu closes")
            chat.context.account.lookup.result?([1, 2])
            Queue.mainQueue().advance(0.0)
            check(progress?.dismissals == 1 && chat.requests == 1 && menu.results == [.default], "slow result uses the shared layout update without dismissing the menu twice")
        }

        for cancelBeforeClosure in [false, true] {
            let (chat, menu) = start()
            menu.holdNormalDismissal = true
            Queue.mainQueue().advance(0.36)
            check(chat.presented.isEmpty && menu.results == [.default], "no HUD while the menu is animating out")
            chat.context.account.lookup.result?([1, 2])
            check(chat.requests == 0, "result waits for the in-flight menu dismissal")
            if cancelBeforeClosure {
                chat.nagramiXCancelAuthorSelection()
            }
            menu.finishNormalDismissal()
            Queue.mainQueue().advance(0.0)
            check(chat.requests == (cancelBeforeClosure ? 0 : 1), "pending result is applied only after dismissal if still active")
            check(chat.presented.isEmpty && menu.results == [.default], "completion shows no HUD and dismisses only once")
        }

        for cancelFromHUD in [false, true] {
            let (chat, menu) = start()
            let lateResult = chat.context.account.lookup.result
            if cancelFromHUD {
                Queue.mainQueue().advance(0.4)
                (chat.presented.first as? Progress)?.cancel?()
            } else {
                menu.closeByUser()
            }
            lateResult?([1, 2])
            Queue.mainQueue().advance(1.0)
            check(chat.requests == 0 && chat.context.account.lookup.disposals == 1, "cancel drops even an already queued result")
            check(!chat.nagramiXIsSelectingAuthorMessages, "cancel releases the ability to select again")
        }

        for change in ["chat", "thread", "selection", "disappear", "menu"] {
            let (chat, menu) = start()
            let lateResult = chat.context.account.lookup.result
            switch change {
            case "chat": chat.chatLocation.peerId = 99
            case "thread": chat.chatLocation.threadId = 15
            case "selection":
                chat.presentationInterfaceState.interfaceState = InterfaceState(selectionState: .init(selectedIds: [9]))
            case "disappear": chat.nagramiXCancelAuthorSelection()
            default: chat.currentContextController = Menu()
            }
            lateResult?([1, 2])
            Queue.mainQueue().advance(0.4)
            check(chat.requests == 0 && menu.results == [.default], "stale result does not change the UI after \(change)")
        }

        do {
            let (chat, menu) = start(requiresVoice: true, archived: true)
            chat.context.account.nagramiXMessageArchive.messages = [Message(id: 3, author: author)]
            chat.context.account.lookup.result?([1, 2])
            check(menu.results == [.custom(.immediate)] && chat.requests == 0, "native recording confirmation closes menu without committing")
            check(!chat.nagramiXIsSelectingAuthorMessages, "declining the confirmation cannot lock selection")
            chat.context.account.postbox.messages.removeValue(forKey: 1)
            chat.context.account.nagramiXMessageArchive.messages.append(Message(id: 4, author: author))
            chat.voiceConfirmation?()
            Queue.mainQueue().advance(0.5)
            check(chat.requests == 1 && chat.nagramiXSelectedAuthorMessageIds == Set([2, 3]), "confirmation respects current history and original archive scope")
            check(menu.results.count == 1 && chat.presented.isEmpty, "confirmation cannot close the same menu again or leave a stale HUD")
        }

        for empty in [true, false] {
            let (chat, menu) = start()
            if empty { chat.context.account.lookup.result?([]) }
            else { chat.context.account.lookup.error?(.unavailable) }
            Queue.mainQueue().advance(0.5)
            check(chat.requests == 0 && menu.results == [.default] && chat.presented.count == 1 && chat.presented[0] is Alert, "empty result and lookup error use the native alert")
        }
        print("PASS quick, slow, cancelled, stale, recording, empty and failed author selection")
    }
}
