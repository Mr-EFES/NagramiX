// UIKit boundary doubles for executing the production gesture controller on
// Linux. Animation timing/rendering and the AVKit window require an iPhone.
import Foundation

struct CGAffineTransform: Equatable {
    var a: CGFloat = 1, b: CGFloat = 0, c: CGFloat = 0, d: CGFloat = 1, tx: CGFloat = 0, ty: CGFloat = 0
    static let identity = Self()
    init() {}
    init(translationX x: CGFloat, y: CGFloat) { self.tx = x; self.ty = y }
    private init(a: CGFloat, b: CGFloat, c: CGFloat, d: CGFloat, tx: CGFloat, ty: CGFloat) {
        self.a = a; self.b = b; self.c = c; self.d = d; self.tx = tx; self.ty = ty
    }
    func scaledBy(x: CGFloat, y: CGFloat) -> Self {
        Self(a: a * x, b: b * x, c: c * y, d: d * y, tx: tx, ty: ty)
    }
    func concatenating(_ o: Self) -> Self {
        Self(a: o.a * a + o.c * b, b: o.b * a + o.d * b,
             c: o.a * c + o.c * d, d: o.b * c + o.d * d,
             tx: o.a * tx + o.c * ty + o.tx, ty: o.b * tx + o.d * ty + o.ty)
    }
    func inverted() -> Self {
        let det = a * d - b * c
        return Self(a: d / det, b: -b / det, c: -c / det, d: a / det,
                    tx: (c * ty - d * tx) / det, ty: (b * tx - a * ty) / det)
    }
    func point(_ p: CGPoint) -> CGPoint { CGPoint(x: a * p.x + c * p.y + tx, y: b * p.x + d * p.y + ty) }
    func rect(_ r: CGRect) -> CGRect {
        let points = [CGPoint(x: r.minX, y: r.minY), CGPoint(x: r.minX, y: r.maxY),
                      CGPoint(x: r.maxX, y: r.minY), CGPoint(x: r.maxX, y: r.maxY)].map(self.point)
        let xs = points.map(\.x), ys = points.map(\.y)
        return CGRect(x: xs.min()!, y: ys.min()!, width: xs.max()! - xs.min()!, height: ys.max()! - ys.min()!)
    }
}

struct UIEdgeInsets { var top: CGFloat = 0, left: CGFloat = 0, bottom: CGFloat = 0, right: CGFloat = 0 }
extension CGRect {
    func inset(by i: UIEdgeInsets) -> CGRect {
        CGRect(x: minX + i.left, y: minY + i.top, width: width - i.left - i.right, height: height - i.top - i.bottom)
    }
}
final class TestLayer {
    var opacity: Float = 1
    var transform = CGAffineTransform.identity
    var presented: TestLayer?
    func presentation() -> TestLayer? { self.presented }
    func affineTransform() -> CGAffineTransform { self.transform }
}
class UIView: NSObject {
    let layer = TestLayer()
    var bounds: CGRect
    var center: CGPoint
    var safeAreaInsets = UIEdgeInsets()
    weak var superview: UIView?
    var transform = CGAffineTransform.identity { didSet { self.layer.transform = self.transform } }
    var alpha: CGFloat = 1 { didSet { self.layer.opacity = Float(self.alpha) } }
    init(frame: CGRect) { self.bounds = CGRect(origin: .zero, size: frame.size); self.center = CGPoint(x: frame.midX, y: frame.midY) }
    static func performWithoutAnimation(_ body: () -> Void) { body() }
    func addGestureRecognizer(_ gesture: UIGestureRecognizer) {}
    func isDescendant(of view: UIView) -> Bool {
        var current: UIView? = self
        while let next = current { if next === view { return true }; current = next.superview }
        return false
    }
    private func toRoot() -> CGAffineTransform {
        let local = CGAffineTransform(translationX: -bounds.midX, y: -bounds.midY)
            .concatenating(transform).concatenating(CGAffineTransform(translationX: center.x, y: center.y))
        return superview.map { local.concatenating($0.toRoot()) } ?? local
    }
    func convert(_ rect: CGRect, to view: UIView) -> CGRect { toRoot().concatenating(view.toRoot().inverted()).rect(rect) }
}
class UISlider: UIView {}
class UISwitch: UIView {}
protocol UIGestureRecognizerDelegate: AnyObject {}
class UIGestureRecognizer: NSObject {
    enum State { case possible, began, changed, ended, cancelled, failed }
    var state = State.possible
}
final class UIPanGestureRecognizer: UIGestureRecognizer {
    var minimumNumberOfTouches = 0, maximumNumberOfTouches = 0
    weak var delegate: UIGestureRecognizerDelegate?
    var delta = CGPoint.zero, speed = CGPoint.zero
    func addTarget(_ target: AnyObject, action: Int) {}
    func translation(in view: UIView?) -> CGPoint { delta }
    func velocity(in view: UIView?) -> CGPoint { speed }
}
class TapLongTapOrDoubleTapGestureRecognizer: UIGestureRecognizer {}
final class UITouch {
    let view: UIView?
    let timestamp: Double
    let point: CGPoint
    init(view: UIView?, timestamp: Double, point: CGPoint) { self.view = view; self.timestamp = timestamp; self.point = point }
    func location(in view: UIView) -> CGPoint { self.point }
}
enum UIAccessibility { static var isReduceMotionEnabled = false }
final class UIApplication {
    enum State { case active, inactive, background }
    static let shared = UIApplication()
    var applicationState = State.active
}
var testClock = 10.0
func CACurrentMediaTime() -> Double { testClock }
final class UIViewPropertyAnimator {
    enum Curve { case easeInOut, easeOut }
    enum Position { case start, current, end }
    static var started: [UIViewPropertyAnimator] = []
    let duration: Double
    private let animations: () -> Void
    private var completions: [(Position) -> Void] = []
    init(duration: Double, curve: Curve, animations: @escaping () -> Void) { self.duration = duration; self.animations = animations }
    func addCompletion(_ block: @escaping (Position) -> Void) { completions.append(block) }
    func startAnimation() { Self.started.append(self); animations() }
    func stopAnimation(_ withoutFinishing: Bool) {}
    // Deliberately permit a late completion after stopAnimation to test the
    // production generation guard, rather than making the double protect it.
    func finish() { let blocks = completions; completions = []; blocks.forEach { $0(.end) } }
}

final class GalleryItemNode: NSObject {
    let view: UIView
    let nagramiXPiPSwipeView: UIView
    let sourceRect: CGRect
    var permitted = true, preparationAccepted = true, requestAccepted = true
    var nativeRequest = false, nagramiXPiPNativeTransitionInFlight = false
    var nagramiXPiPSwipeTransitionPending = false
    var controlsVisible = true
    var prepareCount = 0, startCount = 0, cancelCount = 0
    var startFrames: [CGRect] = []
    var completions: [(Bool) -> Void] = []
    var synchronousResult: Bool?
    var nagramiXCanBeginDirectionalPiPSwipe: Bool { permitted && !nativeRequest }
    var nagramiXBlocksPiPSourcePan: Bool { nativeRequest || nagramiXPiPSwipeTransitionPending }
    init(parent: UIView, aspect: CGFloat) {
        view = UIView(frame: parent.bounds); view.superview = parent
        nagramiXPiPSwipeView = UIView(frame: parent.bounds); nagramiXPiPSwipeView.superview = view
        let width = min(parent.bounds.width, parent.bounds.height * aspect), height = width / aspect
        sourceRect = CGRect(x: (parent.bounds.width - width) / 2, y: (parent.bounds.height - height) / 2, width: width, height: height)
    }
    func nagramiXPiPSourceFrame(in view: UIView) -> CGRect { nagramiXPiPSwipeView.convert(sourceRect, to: view) }
    func controlsVisibility() -> Bool { controlsVisible }
    func updateControlsVisibility(_ value: Bool) { controlsVisible = value }
    func prepareForPictureInPictureSwipe() -> Bool { prepareCount += 1; return preparationAccepted }
    func nagramiXStartDirectionalPiP(completion: @escaping (Bool) -> Void) -> Bool {
        startCount += 1; startFrames.append(nagramiXPiPSourceFrame(in: view))
        if requestAccepted {
            nativeRequest = true; completions.append(completion)
            if let result = synchronousResult { complete(result) }
        }
        return requestAccepted
    }
    func cancelPictureInPictureSwipePreparation() { cancelCount += 1; nativeRequest = false }
    func complete(_ value: Bool) { nativeRequest = false; completions.last?(value) }
}
