import Foundation
import UIKit
import Display

// Owns only the inline transition. The floating window belongs to AVKit.
final class NagramiXPiPGestureController: NSObject, UIGestureRecognizerDelegate {
    private final class Surface {
        let item: GalleryItemNode
        let view: UIView
        let background: UIView
        let space: UIView
        let rest: CGAffineTransform
        let initial: CGAffineTransform
        let source: CGRect
        let viewport: CGRect
        let safeArea: CGRect
        let controlsWereVisible: Bool
        let initialBackgroundAlpha: CGFloat
        let restBackgroundAlpha: CGFloat
        var translation = CGPoint.zero
        init(item: GalleryItemNode, space: UIView, host: UIView, background: UIView,
             rest: CGAffineTransform, restBackgroundAlpha: CGFloat) {
            self.item = item; self.view = item.nagramiXPiPSwipeView; self.space = space
            self.background = background
            self.rest = rest; self.initial = self.view.transform
            self.initialBackgroundAlpha = background.alpha
            self.restBackgroundAlpha = restBackgroundAlpha
            self.controlsWereVisible = item.controlsVisibility()
            self.source = item.nagramiXPiPSourceFrame(in: space)
            self.viewport = host.convert(host.bounds, to: space)
            self.safeArea = host.convert(host.bounds.inset(by: host.safeAreaInsets).insetBy(dx: 12, dy: 12), to: space)
        }
        func pose() -> NagramiXPiPSourceGeometry? {
            return NagramiXPiPSourceGeometry.resolve(source: self.source, viewport: self.viewport,
                safeArea: self.safeArea, translation: self.translation)
        }
        func transform(for pose: NagramiXPiPSourceGeometry) -> CGAffineTransform {
            let pivot = CGPoint(x: self.view.center.x + self.initial.tx, y: self.view.center.y + self.initial.ty)
            let scaled = CGPoint(x: pivot.x + (self.source.midX - pivot.x) * pose.scale,
                                 y: pivot.y + (self.source.midY - pivot.y) * pose.scale)
            return self.initial.scaledBy(x: pose.scale, y: pose.scale)
                .concatenating(CGAffineTransform(translationX: pose.frame.midX - scaled.x, y: pose.frame.midY - scaled.y))
        }
    }

    private weak var host: UIView?
    private weak var content: UIView?
    private weak var background: UIView?
    private let currentItem: () -> GalleryItemNode?
    private let available: () -> Bool
    private let sourcePreview: (Bool) -> Void
    private var surface: Surface?
    private var returning: Surface?
    private var animator: UIViewPropertyAnimator?
    private var generation = UUID()
    private var touchTimestamp = 0.0
    private var committed = false
    let recognizer = UIPanGestureRecognizer()

    init(host: UIView, content: UIView, background: UIView,
         currentItem: @escaping () -> GalleryItemNode?, available: @escaping () -> Bool,
         sourcePreview: @escaping (Bool) -> Void = { _ in }) {
        self.host = host; self.content = content; self.background = background
        self.currentItem = currentItem; self.available = available
        self.sourcePreview = sourcePreview
        super.init()
        self.recognizer.minimumNumberOfTouches = 1
        self.recognizer.maximumNumberOfTouches = 1
        self.recognizer.delegate = self
        self.recognizer.addTarget(self, action: #selector(self.pan(_:)))
        host.addGestureRecognizer(self.recognizer)
    }

    deinit { self.animator?.stopAnimation(true); self.sourcePreview(false) }

    func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool {
        guard self.available(), UIApplication.shared.applicationState == .active,
              let item = self.currentItem(), let content = self.content,
              item.nagramiXCanBeginDirectionalPiPSwipe || item.nagramiXBlocksPiPSourcePan,
              touch.view?.isDescendant(of: content) == true,
              item.view.bounds.contains(touch.location(in: item.view)) else { return false }
        var view = touch.view
        while let current = view, current !== self.host {
            if current is UISlider || current is UISwitch { return false }
            view = current.superview
        }
        self.touchTimestamp = touch.timestamp
        return true
    }

    func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        guard self.available(), UIApplication.shared.applicationState == .active,
              let item = self.currentItem(), item.nagramiXCanBeginDirectionalPiPSwipe || item.nagramiXBlocksPiPSourcePan else { return false }
        let velocity = self.recognizer.velocity(in: self.host)
        return velocity.x.isFinite && velocity.y.isFinite
    }

    func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer,
                           shouldBeRequiredToFailBy otherGestureRecognizer: UIGestureRecognizer) -> Bool {
        // The gallery's tap recognizer ends a long tap after 0.3s even without
        // a long-tap action. It must not win while the user holds before dragging.
        // A stationary tap/double tap is delivered normally when this pan fails.
        return gestureRecognizer === self.recognizer
            && otherGestureRecognizer is TapLongTapOrDoubleTapGestureRecognizer
            && self.currentItem()?.nagramiXCanBeginDirectionalPiPSwipe == true
    }

    func itemChanged() {
        if let surface = self.surface ?? self.returning, surface.item !== self.currentItem() { self.reset(animated: false) }
    }

    func cancel() {
        // iOS can resign active while its own PiP animation is in progress.
        if self.surface?.item.nagramiXPiPNativeTransitionInFlight == true { return }
        self.reset(animated: false)
    }

    func reset(animated: Bool, cancelPreparation: Bool = true) {
        guard let surface = self.surface ?? self.returning else { return }
        self.generation = UUID()
        let generation = self.generation
        self.surface = nil; self.returning = nil; self.committed = false
        let presented = surface.view.layer.presentation()?.affineTransform() ?? surface.view.transform
        let backgroundAlpha = CGFloat(surface.background.layer.presentation()?.opacity ?? Float(surface.background.alpha))
        self.animator?.stopAnimation(true); self.animator = nil
        let animateReturn = animated && !UIAccessibility.isReduceMotionEnabled
        surface.item.nagramiXPiPSwipeTransitionPending = animateReturn
        surface.view.transform = presented
        surface.background.alpha = backgroundAlpha
        if animateReturn {
            self.returning = surface
            let animator = UIViewPropertyAnimator(duration: 0.2, curve: .easeInOut) {
                surface.view.transform = surface.rest
                surface.background.alpha = surface.restBackgroundAlpha
            }
            animator.addCompletion { [weak self] _ in
                guard let self, self.generation == generation else { return }
                surface.item.nagramiXPiPSwipeTransitionPending = false
                self.returning = nil; self.animator = nil
                self.sourcePreview(false)
            }
            self.animator = animator; animator.startAnimation()
        } else {
            surface.view.transform = surface.rest
            surface.background.alpha = surface.restBackgroundAlpha
            self.sourcePreview(false)
        }
        if cancelPreparation {
            surface.item.cancelPictureInPictureSwipePreparation()
            if surface.item === self.currentItem(), self.available() {
                surface.item.updateControlsVisibility(surface.controlsWereVisible)
            }
        }
    }

    @objc private func pan(_ gesture: UIPanGestureRecognizer) {
        guard !self.committed else { return }
        switch gesture.state {
        case .began:
            guard let host = self.host, let background = self.background, let item = self.currentItem(),
                  item.nagramiXCanBeginDirectionalPiPSwipe, item.prepareForPictureInPictureSwipe(),
                  let space = item.nagramiXPiPSwipeView.superview else { return }
            let view = item.nagramiXPiPSwipeView
            let rest = self.returning?.view === view ? self.returning!.rest : view.transform
            let restBackgroundAlpha = self.returning?.view === view ? self.returning!.restBackgroundAlpha : background.alpha
            let presented = view.layer.presentation()?.affineTransform() ?? view.transform
            let backgroundAlpha = CGFloat(background.layer.presentation()?.opacity ?? Float(background.alpha))
            self.animator?.stopAnimation(true); self.animator = nil; self.returning = nil
            view.transform = presented
            background.alpha = backgroundAlpha
            self.generation = UUID()
            self.surface = Surface(item: item, space: space, host: host, background: background,
                rest: rest, restBackgroundAlpha: restBackgroundAlpha)
            item.nagramiXPiPSwipeTransitionPending = true
            // The gallery still owns playback. Reveal only the chat's static
            // source preview before making its background transparent.
            self.sourcePreview(true)
            item.updateControlsVisibility(false)
            fallthrough
        case .changed, .ended:
            guard let surface = self.surface else { return }
            guard surface.item === self.currentItem(), surface.item.nagramiXCanBeginDirectionalPiPSwipe,
                  self.available(), UIApplication.shared.applicationState == .active else { self.reset(animated: true); return }
            let delta = gesture.translation(in: surface.space), velocity = gesture.velocity(in: surface.space)
            guard delta.x.isFinite, delta.y.isFinite, velocity.x.isFinite, velocity.y.isFinite else { self.reset(animated: true); return }
            surface.translation = delta
            guard let pose = surface.pose() else { self.reset(animated: true); return }
            UIView.performWithoutAnimation {
                surface.view.transform = surface.transform(for: pose)
                surface.background.alpha = surface.initialBackgroundAlpha * (1 - pose.progress)
            }
            guard gesture.state == .ended else { return }
            let release = NagramiXPiPReleaseDecision.resolve(x: Double(delta.x), y: Double(delta.y),
                velocityX: Double(velocity.x), velocityY: Double(velocity.y), elapsed: CACurrentMediaTime() - self.touchTimestamp)
            guard release.kind != .cancel else { self.reset(animated: true); return }
            self.committed = true
            surface.item.nagramiXPiPSwipeTransitionPending = true
            let generation = self.generation
            // One handoff: no preliminary edge flight, scale snap, or timer
            // between the final finger-driven frame and the AVKit animation.
            let accepted = surface.item.nagramiXStartDirectionalPiP { [weak self] started in
                guard let self, self.generation == generation else { return }
                if !started { self.reset(animated: true) }
                // Success remains frozen until the gallery actually dismisses.
            }
            if !accepted { self.reset(animated: true) }
        case .cancelled, .failed: self.reset(animated: true)
        default: break
        }
    }
}
