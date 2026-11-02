// UIKit/AsyncDisplayKit boundaries for the extracted native zoom layout.
// This models final geometry, not UIKit rendering or animation timing.
import Foundation

struct CATransform3D { var m11: CGFloat = 1; var m12: CGFloat = 0; var m13: CGFloat = 0 }
let CATransform3DIdentity = CATransform3D()
final class Layer {
    var transform = CATransform3DIdentity
    var scaleAnimations = 0
    func animateScale(from: CGFloat, to: CGFloat, duration: Double, timingFunction: String) {
        precondition(from.isFinite && to.isFinite && duration > 0)
        scaleAnimations += 1
    }
}
class UIView {
    let layer = Layer()
    var bounds = CGRect.zero
    var center = CGPoint.zero
    var frame: CGRect {
        get {
            let scale = layer.transform.m11
            let size = CGSize(width: bounds.width * scale, height: bounds.height * scale)
            return CGRect(x: center.x - size.width / 2, y: center.y - size.height / 2,
                          width: size.width, height: size.height)
        }
        set {
            let scale = layer.transform.m11
            precondition(scale > 0)
            bounds.size = CGSize(width: newValue.width / scale, height: newValue.height / scale)
            center = CGPoint(x: newValue.midX, y: newValue.midY)
        }
    }
    func removeFromSuperview() {}
}
class TilingView: UIView {
    func setMaximumZoomScale(_ scale: CGFloat, normalizedSize: CGSize) {}
}
final class UIScrollView: UIView {
    var child: UIView?
    var zoomChanged: (() -> Void)?
    var contentSize = CGSize.zero
    var isScrollEnabled = false
    var minimumZoomScale: CGFloat = 1 {
        didSet { if zoomScale < minimumZoomScale { zoomScale = minimumZoomScale } }
    }
    var maximumZoomScale: CGFloat = 1 {
        didSet { if zoomScale > maximumZoomScale { zoomScale = maximumZoomScale } }
    }
    var zoomScale: CGFloat = 1 {
        didSet {
            guard let child else { return }
            child.layer.transform = CATransform3D(m11: zoomScale)
            contentSize = CGSize(width: child.bounds.width * zoomScale, height: child.bounds.height * zoomScale)
            if oldValue != zoomScale { zoomChanged?() }
        }
    }
}
class ASDisplayNode {
    private let backingView: UIView
    init(view: UIView = UIView()) { backingView = view }
    var view: UIView { backingView }
    var layer: Layer { view.layer }
    var frame: CGRect { get { view.frame } set { view.frame = newValue } }
    var transform: CATransform3D { get { layer.transform } set { layer.transform = newValue } }
}
final class ASScrollNode: ASDisplayNode {
    private let scrollView = UIScrollView()
    override var view: UIScrollView { scrollView }
    func addSubnode(_ node: ASDisplayNode) { view.child = node.view }
}
struct ContainerViewLayout { let size: CGSize }
enum Curve { case system; var timingFunction: String { "system" } }
enum ContainedViewLayoutTransition {
    case immediate
    case animated(duration: Double, curve: Curve)
    var isAnimated: Bool { if case .animated = self { return true }; return false }
    func updateFrame(node: ASDisplayNode, frame: CGRect) { node.frame = frame }
    func updateFrame(view: UIView, frame: CGRect) { view.frame = frame }
    func animatePosition(node: ASDisplayNode, from: CGPoint) {
        precondition(from.x.isFinite && from.y.isFinite)
    }
}
class GalleryItemNode {
    func containerLayoutUpdated(_ layout: ContainerViewLayout, navigationBarHeight: CGFloat,
                                transition: ContainedViewLayoutTransition) {}
}
extension CGSize {
    func equalTo(_ other: CGSize) -> Bool { self == other }
    func fitted(_ size: CGSize) -> CGSize {
        var fittedSize = self
        if fittedSize.width > size.width {
            fittedSize = CGSize(width: size.width, height: floor(fittedSize.height * size.width / max(fittedSize.width, 1)))
        }
        if fittedSize.height > size.height {
            fittedSize = CGSize(width: floor(fittedSize.width * size.height / max(fittedSize.height, 1)), height: size.height)
        }
        return fittedSize
    }
}
