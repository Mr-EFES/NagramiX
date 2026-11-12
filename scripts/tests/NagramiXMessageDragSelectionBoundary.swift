// Explicit test I/O boundary. This does not model real UIKit arbitration/rendering.
typealias Selector = String
class UIView {
    var gestureRecognizers: [UIGestureRecognizer]?
    var offset = CGPoint.zero
    func addGestureRecognizer(_ gesture: UIGestureRecognizer) {
        gesture.view = self
        if gestureRecognizers == nil { gestureRecognizers = [] }
        gestureRecognizers?.append(gesture)
    }
    func convert(_ point: CGPoint, to other: UIView?) -> CGPoint {
        CGPoint(x: point.x + offset.x - (other?.offset.x ?? 0), y: point.y + offset.y - (other?.offset.y ?? 0))
    }
}
class UIEvent {}
class UITouch: Hashable {
    enum TouchType: Int { case direct = 0 }
    var point: CGPoint
    init(_ point: CGPoint) { self.point = point }
    func location(in view: UIView?) -> CGPoint { point }
    static func == (lhs: UITouch, rhs: UITouch) -> Bool { lhs === rhs }
    func hash(into hasher: inout Hasher) { hasher.combine(ObjectIdentifier(self)) }
}
class UIGestureRecognizer {
    enum State { case possible, began, changed, ended, failed, cancelled }
    var state: State = .possible
    weak var view: UIView?
    var point = CGPoint.zero
    var dependencies: [UIGestureRecognizer] = []
    init(target: Any?, action: Selector?) {}
    func location(in other: UIView?) -> CGPoint { view?.convert(point, to: other) ?? point }
    func require(toFail other: UIGestureRecognizer) { dependencies.append(other) }
    func reset() { state = .possible }
    func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent) {}
    func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent) {}
}
class UIPanGestureRecognizer: UIGestureRecognizer {
    var minimumNumberOfTouches = 1
    var maximumNumberOfTouches = Int.max
    var allowedTouchTypes: [NSNumber] = []
    var forwardedMoves = 0
    var touchCount = 0
    override func reset() { super.reset(); touchCount = 0 }
    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent) {
        touchCount += touches.count
        if touchCount > maximumNumberOfTouches { state = state == .possible ? .failed : .cancelled }
    }
    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent) { forwardedMoves += 1 }
}
typealias MessageId = Int
typealias MessageIndex = Int
class Media {}
final class TelegramMediaAction: Media {}
struct Message {
    let id: MessageId
    let index: MessageIndex
    var media: [Media] = []
}
enum ChatHistoryEntry {
    case MessageEntry(Message, Int, Bool, Int?, Int, Int)
    case MessageGroupEntry(Int64, [(Message, Bool, Int, Int, Int?)], Int)
    case UnreadEntry
    var firstIndex: MessageIndex {
        switch self {
        case let .MessageEntry(m, _, _, _, _, _): return m.index
        case let .MessageGroupEntry(_, group, _): return group.first!.0.index
        case .UnreadEntry: return -1
        }
    }
}
final class MessageHistoryView {}
struct ChatHistoryView {
    var originalView = MessageHistoryView()
    var filteredEntries: [ChatHistoryEntry]
    var id: Int32 = 0
}
struct Insets { var left: CGFloat; var top: CGFloat; var bottom: CGFloat }
class ASDisplayNode {}
class ListViewItemNode: ASDisplayNode {}
final class ChatMessageItemView: ListViewItemNode {
    enum Content {
        case message(Message, Int, Int, Int, Int)
        case group([(Message, Int)])
    }
    struct Item { let content: Content }
    var item: Item?
    var listFrame: CGRect?
    init(_ messages: [Message], frame: CGRect) {
        self.listFrame = frame
        self.item = Item(content: messages.count == 1 ? .message(messages[0], 0, 0, 0, 0) : .group(messages.map { ($0, 0) }))
    }
}
enum ListViewScrollDirection { case up, down }
final class ListBackend {
    let view = UIView()
    let scrollGestureHostView = UIView()
    var nodes: [ChatMessageItemView] = []
    var scrolls: [(ListViewScrollDirection, CGFloat)] = []
    var onScroll: (() -> Void)?
    func itemNodeFrame(_ node: ListViewItemNode) -> CGRect? { (node as? ChatMessageItemView)?.listFrame }
    func scrollWithDirection(_ direction: ListViewScrollDirection, distance: CGFloat) -> Bool {
        scrolls.append((direction, distance)); onScroll?(); return true
    }
}
struct SelectionState { var selectedIds: Set<MessageId> }
final class ControllerInteraction {
    var selectionState: SelectionState? = SelectionState(selectedIds: [])
    var calls: [(Set<MessageId>, Bool)] = []
    func toggleMessagesSelection(_ ids: [MessageId], _ value: Bool) {
        calls.append((Set(ids), value))
        if value { selectionState?.selectedIds.formUnion(ids) }
        else { selectionState?.selectedIds.subtract(ids) }
    }
}
enum SwiftSignalKit {
    struct Queue { static func mainQueue() -> Queue { Queue() } }
    final class Timer {
        let timeout: Double
        let completion: () -> Void
        var active = false
        init(timeout: Double, repeat: Bool, completion: @escaping () -> Void, queue: Queue) {
            self.timeout = timeout; self.completion = completion
        }
        func start() { active = true }
        func invalidate() { active = false }
        func fire() { if active { active = false; completion() } }
    }
}
final class ConstantDisplayLinkAnimator {
    let update: () -> Void
    var isPaused = true
    init(update: @escaping () -> Void) { self.update = update }
}
