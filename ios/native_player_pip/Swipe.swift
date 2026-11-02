import UIKit

final class NagramiXNativePlayerSwipe: NSObject, UIGestureRecognizerDelegate {
    let recognizer = UIPanGestureRecognizer()
    private let available: (CGPoint) -> Bool
    private let commit: () -> Void
    init(host: UIView, available: @escaping (CGPoint) -> Bool, commit: @escaping () -> Void) {
        self.available = available; self.commit = commit
        super.init()
        self.recognizer.delegate = self
        self.recognizer.maximumNumberOfTouches = 1
        self.recognizer.addTarget(self, action: #selector(self.pan(_:)))
        host.addGestureRecognizer(self.recognizer)
    }
    func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool {
        var view = touch.view
        while let current = view {
            if current is UIControl { return false }
            view = current.superview
        }
        return self.available(touch.location(in: gestureRecognizer.view))
    }
    func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        let velocity = self.recognizer.velocity(in: gestureRecognizer.view)
        return velocity.x.isFinite && velocity.y.isFinite && abs(velocity.y) > abs(velocity.x) * 1.3
            && self.available(self.recognizer.location(in: gestureRecognizer.view))
    }
    @objc private func pan(_ gesture: UIPanGestureRecognizer) {
        guard gesture.state == .ended else { return }
        let distance = gesture.translation(in: gesture.view), velocity = gesture.velocity(in: gesture.view)
        guard distance.y.isFinite, velocity.y.isFinite,
              abs(distance.y) >= 55 || (abs(distance.y) >= 18 && abs(velocity.y) >= 650) else { return }
        self.commit()
    }
}
