// Complements the historical recording UIKit boundary, without changing it.
// No Auto Layout engine, text renderer, physical screen or native scroll is run.
extension Font { static func semibold(_ value: CGFloat) -> CGFloat { value } }
extension UIView { func layoutIfNeeded() {} }
final class UIScrollView: UIView {
    enum Adjustment { case never }
    let contentLayoutGuide = UIView(), frameLayoutGuide = UIView()
    var contentInsetAdjustmentBehavior = Adjustment.never
    var bounces = true, isDirectionalLockEnabled = false
    var showsVerticalScrollIndicator = true, showsHorizontalScrollIndicator = true
    var isScrollEnabled = true
    var revealed: [CGRect] = []
    func scrollRectToVisible(_ rect: CGRect, animated: Bool) { revealed.append(rect) }
}
