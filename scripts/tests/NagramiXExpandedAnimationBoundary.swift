import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif

// UIKit/Core Animation/keyboard delivery boundaries. The real transition's
// setFrame method, panel presenter, mode policy and editor routes run below.
enum Timeline { static var now: Double = 0 }
final class CALayer {
    struct Motion {
        let from: CGPoint; let to: CGPoint; let start: Double; let duration: Double
        let completion: ((Bool) -> Void)?
    }
    var position = CGPoint.zero
    var bounds = CGRect.zero
    let anchorPoint = CGPoint(x: 0.5, y: 0.5)
    var motion: Motion?
    var starts: [Motion] = []
    var completions: [((Bool) -> Void)] = []
    func animation(forKey key: String) -> Int? { key == "position" && motion != nil ? 1 : nil }
    func presentation() -> CALayer? {
        guard let motion else { return nil }
        let result = CALayer(); result.bounds = bounds
        let progress = CGFloat(min(1, max(0, (Timeline.now - motion.start) / motion.duration)))
        result.position = CGPoint(x: motion.from.x + (motion.to.x - motion.from.x) * progress,
                                  y: motion.from.y + (motion.to.y - motion.from.y) * progress)
        return result
    }
    func removeAnimation(forKey key: String) {
        if key == "position" { let old = motion; motion = nil; old?.completion?(false) }
    }
    func start(from: CGPoint, to: CGPoint, duration: Double, completion: ((Bool) -> Void)?) {
        removeAnimation(forKey: "position")
        if from == to { completion?(true); return }
        let value = Motion(from: from, to: to, start: Timeline.now, duration: duration, completion: completion)
        motion = value; starts.append(value)
        if let completion { completions.append(completion) }
    }
    func finish(_ completed: Bool = true) { let old = motion; motion = nil; old?.completion?(completed) }
}
class UIView {
    let layer = CALayer()
    var isHidden = false
    var frame: CGRect {
        get { CGRect(x: layer.position.x - layer.bounds.width * 0.5, y: layer.position.y - layer.bounds.height * 0.5, width: layer.bounds.width, height: layer.bounds.height) }
        set { layer.bounds.size = newValue.size; layer.position = CGPoint(x: newValue.midX, y: newValue.midY) }
    }
    var bounds: CGRect { get { layer.bounds } set { layer.bounds = newValue } }
    func addSubview(_ view: UIView) {}
}
struct ComponentTransition: Equatable {
    enum Animation: Equatable {
        enum Curve: Equatable { case spring, keyboard, linear }
        case none
        case curve(duration: Double, curve: Curve)
        var isImmediate: Bool { if case .none = self { return true }; return false }
    }
    var animation: Animation
    static let immediate = Self(animation: .none)
    static func spring(duration: Double) -> Self { Self(animation: .curve(duration: duration, curve: .spring)) }
    func animatePosition(view: UIView, from: CGPoint, to: CGPoint, completion: ((Bool) -> Void)?) {
        if case let .curve(duration, _) = animation { view.layer.start(from: from, to: to, duration: duration, completion: completion) }
    }
    func animateBoundsSize(view: UIView, from: CGSize, to: CGSize) {}
    // The native setFrame method is inserted here by the validator.
}
final class EmptyInputView: UIView {}
final class Editor: UIView {
    var focused = true
    var reloads = 0
    var changedInputView: (() -> Void)?
    var customInputView: UIView? { didSet { reloads += 1; changedInputView?() } }
    func becomeFirstResponder() -> Bool { focused = true; return true }
}
func viewTreeContainsFirstResponder(view: Editor) -> Bool { view.focused }
enum UIAccessibility { static var isReduceMotionEnabled = false }
enum NagramiXFormattingSettings { static var enabled = true }
final class ComponentState {
    var last = ComponentTransition.immediate
    func updated(transition: ComponentTransition) { last = transition }
}
struct Deadline {
    static func now() -> Self { Self() }
    static func +(lhs: Self, rhs: Double) -> Self { lhs }
}
enum DispatchQueue {
    static let main = Queue()
    final class Queue {
        var work: [() -> Void] = []
        func asyncAfter(deadline: Deadline, execute: @escaping () -> Void) { work.append(execute) }
    }
}
struct Insets { var left: CGFloat = 0; var right: CGFloat = 0; var bottom: CGFloat = 34 }
struct DeviceMetrics { func standardInputHeight(inLandscape: Bool) -> CGFloat { inLandscape ? 216 : 310 } }
enum ViewControllerComponentContainer {
    struct Environment { var inputHeight: CGFloat; var safeInsets = Insets(); var deviceMetrics = DeviceMetrics(); var metrics = 0 }
}
final class ChatEntityKeyboardInputNode {
    let view = UIView()
    var clipsToBounds = false
    var externalTopPanelContainerImpl: Int?
    var visibleRequests: [Bool] = []
    init(_ data: Int) {}
    func updateLayout(width: CGFloat, leftInset: CGFloat, rightInset: CGFloat, bottomInset: CGFloat, standardInputHeight: CGFloat, inputHeight: CGFloat, maximumHeight: CGFloat, inputPanelHeight: CGFloat, transition: ComponentTransition, interfaceState: Int, layoutMetrics: Int, deviceMetrics: DeviceMetrics, isVisible: Bool, isExpanded: Bool) -> (CGFloat, CGFloat) {
        visibleRequests.append(isVisible)
        return (standardInputHeight, 0)
    }
}
