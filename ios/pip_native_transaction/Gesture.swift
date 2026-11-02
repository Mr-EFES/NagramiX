import UIKit
import Display

// Жест выбирает только момент явного запроса. Размер/положение окна и переход
// принадлежат AVKit: локальную миниатюру внутри fullscreen не создаём.
final class NagramiXPiPGestureController: NSObject, UIGestureRecognizerDelegate {
    private weak var host: UIView?
    private weak var content: UIView?
    private let currentItem: () -> GalleryItemNode?
    private let available: () -> Bool
    private let sourcePreview: (Bool) -> Void
    private var item: GalleryItemNode?
    private var generation = UUID()
    private var touchTimestamp = 0.0
    private var committed = false
    let recognizer = UIPanGestureRecognizer()

    init(host: UIView, content: UIView, background: UIView,
         currentItem: @escaping () -> GalleryItemNode?, available: @escaping () -> Bool,
         sourcePreview: @escaping (Bool) -> Void = { _ in },
         prepareControls: (() -> Void)? = nil) {
        self.host = host; self.content = content
        self.currentItem = currentItem; self.available = available
        self.sourcePreview = sourcePreview
        // Сохраняем сигнатуру интеграции; фон/controls до willStart не меняются.
        _ = background; _ = prepareControls
        super.init()
        self.recognizer.minimumNumberOfTouches = 1
        self.recognizer.maximumNumberOfTouches = 1
        self.recognizer.delegate = self
        self.recognizer.addTarget(self, action: #selector(self.pan(_:)))
        host.addGestureRecognizer(self.recognizer)
    }

    deinit { self.sourcePreview(false) }

    func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool {
        guard self.available(), UIApplication.shared.applicationState == .active,
              let item = self.currentItem(), let content = self.content,
              item.nagramiXCanBeginDirectionalPiPSwipe,
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
              self.currentItem()?.nagramiXCanBeginDirectionalPiPSwipe == true else { return false }
        let velocity = self.recognizer.velocity(in: self.host)
        // Горизонтальное перелистывание остаётся штатной галерее.
        return velocity.x.isFinite && velocity.y.isFinite && abs(velocity.y) > abs(velocity.x)
    }

    func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer,
                           shouldBeRequiredToFailBy otherGestureRecognizer: UIGestureRecognizer) -> Bool {
        return gestureRecognizer === self.recognizer
            && otherGestureRecognizer is TapLongTapOrDoubleTapGestureRecognizer
            && self.currentItem()?.nagramiXCanBeginDirectionalPiPSwipe == true
    }

    func itemChanged() {
        if let item = self.item, item !== self.currentItem() { self.reset(animated: false) }
    }

    func cancel() {
        if self.item?.nagramiXPiPNativeTransitionInFlight == true { return }
        self.reset(animated: false)
    }

    func reset(animated: Bool, cancelPreparation: Bool = true) {
        _ = animated
        self.generation = UUID()
        let item = self.item
        self.item = nil; self.committed = false
        item?.nagramiXPiPSwipeTransitionPending = false
        if let item, !item.nagramiXPiPNativeTransitionInFlight || !cancelPreparation {
            item.nagramiXPiPSwipeView.transform = .identity
        }
        if cancelPreparation { item?.cancelPictureInPictureSwipePreparation() }
        self.sourcePreview(false)
    }

    @objc private func pan(_ gesture: UIPanGestureRecognizer) {
        guard !self.committed else { return }
        switch gesture.state {
        case .began:
            guard self.available(), let item = self.currentItem(), item.nagramiXCanBeginDirectionalPiPSwipe else { return }
            self.generation = UUID()
            self.item = item
            // Удаляем только старую pose отдельной PiP-поверхности, не zoom видео.
            item.nagramiXPiPSwipeView.transform = .identity
        case .changed, .ended:
            guard let item = self.item else { return }
            guard item === self.currentItem(), item.nagramiXCanBeginDirectionalPiPSwipe,
                  self.available(), UIApplication.shared.applicationState == .active else { self.reset(animated: false); return }
            let delta = gesture.translation(in: self.host), velocity = gesture.velocity(in: self.host)
            guard delta.x.isFinite, delta.y.isFinite, velocity.x.isFinite, velocity.y.isFinite else { self.reset(animated: false); return }
            // Нет transform/scale/fade на changed: полноразмерный кадр остаётся
            // в иерархии, пока системный контроллер не подтвердит запуск.
            guard gesture.state == .ended else { return }
            let release = NagramiXPiPReleaseDecision.resolve(x: Double(delta.x), y: Double(delta.y),
                velocityX: Double(velocity.x), velocityY: Double(velocity.y), elapsed: CACurrentMediaTime() - self.touchTimestamp)
            guard release.kind != .cancel else { self.reset(animated: false); return }
            self.committed = true
            item.nagramiXPiPSwipeTransitionPending = true
            let generation = self.generation
            let accepted = item.nagramiXStartDirectionalPiP { [weak self] _ in
                guard let self, self.generation == generation else { return }
                self.reset(animated: false, cancelPreparation: false)
            }
            if !accepted { self.reset(animated: false) }
        case .cancelled, .failed: self.reset(animated: false)
        default: break
        }
    }
}
