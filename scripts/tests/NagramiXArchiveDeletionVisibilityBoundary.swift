import Foundation
import CoreFoundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif

// The transition, dust admission, node restoration and weak ownership are
// production code. UIKit/CA snapshots and native engine answers are boundaries.
struct PeerId: Hashable { var value: Int64 = 1; var namespace: Int32 = 0 }
struct MessageId: Hashable { var peerId = PeerId(); var namespace: Int32 = 0; var id: Int32 }
enum EngineMessage { typealias Id = MessageId }
enum Namespaces { enum Message { static let ScheduledCloud: Int32 = 1 } }
struct AutoremoveAttribute { let countdownBeginTime: Int32?; let timeout: Int32 }
struct Message { var stableId: UInt32; var id: MessageId; var autoremoveAttribute: AutoremoveAttribute? }
func autoremoveExpiryTimestamp(countdownBeginTime: Int32, timeout: Int32) -> Int32 { countdownBeginTime + timeout }
enum ChatHistoryEntry {
    // PRODUCTION_MESSAGE_ENTRY_CASE
    // PRODUCTION_GROUP_ENTRY_CASE
    case other
}
struct HistoryView { var filteredEntries: [ChatHistoryEntry] }
struct TransitionOptions: OptionSet { let rawValue: Int; static let AnimateInsertion = Self(rawValue: 1) }
struct Transition { let historyView: HistoryView; var options: TransitionOptions = [.AnimateInsertion] }
struct Image {}
struct Transform {}
func CATransform3DMakeRotation(_ angle: CGFloat, _ x: CGFloat, _ y: CGFloat, _ z: CGFloat) -> Transform { Transform() }
class Layer {
    var sublayers: [DustEffectLayer] = []
    func convert(_ rect: CGRect, to: DustEffectLayer) -> CGRect { rect }
    func addSublayer(_ layer: DustEffectLayer) { sublayers.append(layer) }
}
final class DustEffectLayer {
    var position = CGPoint.zero; var bounds = CGRect.zero; var zPosition: CGFloat = 0; var transform = Transform()
    var becameEmpty: (() -> Void)?; var frames: [CGRect] = []
    func removeFromSuperlayer() {}
    func addItem(frame: CGRect, image: Image) { frames.append(frame) }
}
extension CGRect { var center: CGPoint { CGPoint(x: midX, y: midY) } }
class ItemNode {}
final class MessageItem { var content: [(Message, Int)]; init(_ messages: [Message]) { content = messages.map { ($0, 0) } } }
class ChatMessageItemView: ItemNode {
    var item: MessageItem?; var isHidden = false; var bounds = CGRect(x: 0, y: 0, width: 300, height: 1100)
    let layer = Layer(); var snapshotAvailable = true; var snapshotCalls = 0
    init(_ messages: [Message]) { item = MessageItem(messages) }
    func makeContentSnapshot() -> (Image, CGRect)? { snapshotCalls += 1; return snapshotAvailable ? (Image(), bounds) : nil }
}
final class ChatMessageBubbleItemNode: ChatMessageItemView { var service = false; func isServiceLikeMessage() -> Bool { service } }
final class WeakNodeProbe { weak var node: ChatMessageItemView?; init(_ node: ChatMessageItemView?) { self.node = node } }
final class EngineMessages {
    var deleted: Set<MessageId> = []; var tested: [MessageId] = []
    func synchronouslyIsMessageDeletedInteractively(ids: [MessageId]) -> [MessageId] { tested += ids; return ids.filter { deleted.contains($0) } }
}
final class Engine { let messages = EngineMessages() }
final class Context { let engine = Engine() }
enum NagramiXDeletionEffectSettings { static var enabled = true; static func isEnabled() -> Bool { enabled } }

// PRODUCTION_WEAK_NODE

final class TransitionHarness {
    let context = Context(); let layer = Layer(); var bounds = CGRect(x: 0, y: 0, width: 390, height: 844)
    var historyView: HistoryView?; var ignoreMessageIds: Set<MessageId> = []
    var itemNodes: [ItemNode] = []; var allowDustEffect = true; var rotated = false; var dustEffectLayer: DustEffectLayer?
    private var currentAppliedDeleteAnimationCorrelationIds = Set<UInt32>()
    var applied: Set<UInt32> { currentAppliedDeleteAnimationCorrelationIds }
    var pending: Set<UInt32> { currentDeleteAnimationCorrelationIds }
    var hiddenCount: Int { nagramiXDustHiddenMessageNodes.count }
    func forEachItemNode(_ body: (ItemNode) -> Void) { itemNodes.forEach(body) }
    func forceCandidates(_ ids: Set<UInt32>) { currentDeleteAnimationCorrelationIds = ids }

// PRODUCTION_RESTORE_AND_STORAGE

    func process(_ next: [ChatHistoryEntry], animated: Bool = true) {
        let transition = Transition(historyView: HistoryView(filteredEntries: next), options: animated ? [.AnimateInsertion] : [])
// PRODUCTION_TRANSITION
        historyView = transition.historyView
    }
}
