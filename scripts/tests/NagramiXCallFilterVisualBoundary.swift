import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
#if canImport(Glibc)
import Glibc
#else
import Darwin
#endif
private var assertions = 0
private func expect(_ value: @autoclosure () -> Bool, _ label: String) {
    guard value() else { FileHandle.standardError.write(Data((label + "\n").utf8)); exit(96) }; assertions += 1
}
private typealias UIColor = Int
private enum Alignment { case center }
private extension NSAttributedString {
    convenience init(string: String, font: Double, textColor: UIColor, paragraphAlignment: Alignment) { self.init(string: string) }
}
private struct PresentationStrings {
    let Calls_NoVoiceAndVideoCallsPlaceholder = "all calls"
    let Calls_NoMissedCallsPlacehoder = "missed calls"
    let Calls_StartNewCall = "new call"
}
private struct PresentationTheme {
    struct List { let freeTextColor = 1; let itemAccentColor = 2; let blocksBackgroundColor = 3 }
    struct Chats { let backgroundColor = 4 }
    let list = List(); let chatList = Chats()
}
private final class Layer {
    var animations = 0
    func animateAlpha(from: CGFloat, to: CGFloat, duration: Double, completion: ((Bool) -> Void)? = nil) {
        animations += 1; completion?(true)
    }
}
private struct Image { var size = CGSize(width: 24, height: 24) }
private class Node {
    var alpha: CGFloat = 0
    let layer = Layer()
    var frame = CGRect.zero
    var visibility = false
    var isUserInteractionEnabled = true
    var image: Image? = Image()
    var backgroundColor: UIColor = 0
    func updateLayout(size: CGSize) {}
}
private final class ImmediateTextNode: Node {
    static var measuredHeights: [String: CGFloat] = ["all calls":34,"missed calls":17,"new call":20]
    var maximumNumberOfLines = 3
    var textAlignment = Alignment.center
    var attributedText: NSAttributedString?
    func updateLayout(_ bounds: CGSize) -> CGSize {
        CGSize(width: min(150, max(0, bounds.width)), height: Self.measuredHeights[attributedText?.string ?? ""] ?? 0)
    }
}
private struct Insets { var top: CGFloat = 0; var left: CGFloat = 0; var bottom: CGFloat = 0; var right: CGFloat = 0 }
private struct InsetOptions: OptionSet { let rawValue: Int; static let input = Self(rawValue: 1); static let statusBar = Self(rawValue: 2) }
private struct ContainerViewLayout {
    var size = CGSize(width: 384, height: 832)
    var safeInsets = Insets()
    var baseInsets = Insets(bottom: 64)
    func insets(options: InsetOptions) -> Insets { baseInsets }
}
private enum ContainedViewLayoutTransition {
    case immediate
    func updateFrame(node: Node, frame: CGRect) { node.frame = frame }
}
private func floorToScreenPixels(_ value: CGFloat) -> CGFloat { floor(value * 2) / 2 }
private enum EngineCallList {
    enum Scope { case all, missed }
}
private enum EngineMessage {
    struct Index { let value: Int; static func absoluteUpperBound() -> Self { Self(value: Int.max) } }
}
private enum Location { case changeType(index: EngineMessage.Index) }
private struct CallListNodeLocationAndType { var location: Location; var scope: EngineCallList.Scope }
private struct ViewItem { let highestIndex = EngineMessage.Index(value: 1) }
private struct EngineView { var items: [ViewItem] = [] }
private struct CallView { let originalView = EngineView() }
private struct ValueSignal<T> { let value: T; static func single(_ value: T) -> Self { Self(value: value) } }
private final class EmptyPromise {
    var values: [Bool] = []
    func set(_ signal: ValueSignal<Bool>) { values.append(signal.value) }
}
private final class LocationPromise {
    var values: [CallListNodeLocationAndType] = []
    func set(_ value: CallListNodeLocationAndType) { values.append(value) }
}
private final class Calls {
    enum Mode { case tab, navigation }
    struct State { struct Data { let strings = PresentationStrings(); let theme = PresentationTheme() }; let presentationData = Data() }
    var currentState = State()
    var mode = Mode.tab
    let emptyTextMeasureNode = ImmediateTextNode()
    let emptyTextNode = ImmediateTextNode()
    let emptyAnimationNode = Node()
    let emptyButtonIconNode = Node()
    let emptyButtonTextNode = ImmediateTextNode()
    let emptyButtonNode = Node()
    let listNode = Node()
    let emptyAnimationSize = CGSize(width: 148, height: 148)
    let textFont = 15.0, buttonFont = 17.0
    var backgroundColor: UIColor = 0
    var containerLayout: (ContainerViewLayout, CGFloat)? = (ContainerViewLayout(), 90)
    var callListView: CallView? = CallView()
    var currentLocationAndType = CallListNodeLocationAndType(location: .changeType(index: .absoluteUpperBound()), scope: .all)
    let emptyStatePromise = EmptyPromise()
    let callListLocationAndType = LocationPromise()
// METHODS
    func show(_ type: EngineCallList.Scope, hidden: Bool = false) {
        updateEmptyPlaceholder(theme: currentState.presentationData.theme, strings: currentState.presentationData.strings, type: type, isHidden: hidden)
    }
    var animations: Int { [emptyTextNode,emptyAnimationNode,emptyButtonIconNode,emptyButtonTextNode,listNode].reduce(0) { $0 + $1.layer.animations } }
}
