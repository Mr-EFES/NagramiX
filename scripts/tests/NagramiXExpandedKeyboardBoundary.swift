import Foundation

// UIKit, keyboard delivery and component boundaries only. Geometry, routing and
// the layout coordination block are extracted unchanged from production.
class UIView {}
final class EmptyInputView: UIView {}
final class Editor: UIView {
    var focused = true
    var reloads = 0
    var nilWrites = 0
    var focusSawSystemKeyboard = false
    var customInputView: UIView? {
        didSet { reloads += 1; if customInputView == nil { nilWrites += 1 } }
    }
    func becomeFirstResponder() -> Bool {
        if !focused && customInputView == nil { focusSawSystemKeyboard = true }
        focused = true
        return true
    }
}
func viewTreeContainsFirstResponder(view: Editor) -> Bool { view.focused }
enum UIAccessibility { static var isReduceMotionEnabled = false }
enum NagramiXFormattingSettings { static var enabled = true }
struct ComponentTransition: Equatable {
    let animated: Bool
    static let immediate = ComponentTransition(animated: false)
    static func spring(duration: Double) -> Self { Self(animated: true) }
}
final class ComponentState {
    var transitions: [ComponentTransition] = []
    func updated(transition: ComponentTransition) { transitions.append(transition) }
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
        func drain() { let pending = work; work.removeAll(); for callback in pending { callback() } }
    }
}
struct Insets { var bottom: CGFloat = 34 }
struct DeviceMetrics {
    var height: CGFloat = 310
    func standardInputHeight(inLandscape: Bool) -> CGFloat { inLandscape ? 216 : height }
}
struct Environment {
    var inputHeight: CGFloat
    var safeInsets = Insets()
    var deviceMetrics = DeviceMetrics()
}
