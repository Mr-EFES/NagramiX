import Foundation

@main struct PiPGestureTests {
    final class Fixture {
        let host = UIView(frame: CGRect(x: 0, y: 0, width: 390, height: 844))
        let content = UIView(frame: CGRect(x: 0, y: 0, width: 390, height: 844))
        let background = UIView(frame: CGRect(x: 0, y: 0, width: 390, height: 844))
        var item: GalleryItemNode!
        var available = true
        var previewVisible = false
        var controller: NagramiXPiPGestureController!
        init(aspect: CGFloat = 16 / 9) {
            content.superview = host; background.superview = host
            host.safeAreaInsets = UIEdgeInsets(top: 44, left: 0, bottom: 34, right: 0)
            item = GalleryItemNode(parent: content, aspect: aspect)
            controller = NagramiXPiPGestureController(host: host, content: content, background: background,
                currentItem: { [weak self] in self?.item }, available: { [weak self] in self?.available == true },
                sourcePreview: { [weak self] visible in self?.previewVisible = visible })
            UIViewPropertyAnimator.started = []; UIAccessibility.isReduceMotionEnabled = false
            UIApplication.shared.applicationState = .active; testClock = 10
        }
        func begin(_ delta: CGPoint) -> Bool {
            let touch = UITouch(view: item.nagramiXPiPSwipeView, timestamp: testClock, point: CGPoint(x: 195, y: 422))
            guard controller.gestureRecognizer(controller.recognizer, shouldReceive: touch),
                  controller.gestureRecognizerShouldBegin(controller.recognizer) else { return false }
            send(.began, delta); return true
        }
        func send(_ state: UIGestureRecognizer.State, _ delta: CGPoint, speed: CGPoint = .zero) {
            controller.recognizer.state = state; controller.recognizer.delta = delta; controller.recognizer.speed = speed
            controller.testDrivePan()
        }
    }

    static func main() {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ name: String) { precondition(value(), name); checks += 1 }
        func equal(_ a: CGRect, _ b: CGRect) -> Bool {
            abs(a.minX - b.minX) < 0.00001 && abs(a.minY - b.minY) < 0.00001
                && abs(a.width - b.width) < 0.00001 && abs(a.height - b.height) < 0.00001
        }
        for aspect: CGFloat in [16 / 9, 9 / 16, 1] {
            for delta in [CGPoint(x: 0, y: -120), CGPoint(x: 0, y: 120), CGPoint(x: -120, y: 0), CGPoint(x: 120, y: 0)] {
                for held in [false, true] {
                    let f = Fixture(aspect: aspect)
                    check(f.begin(.zero), "gesture accepted")
                    check(f.item.prepareCount == 1 && f.item.startCount == 0, "warm binding without native start during touch")
                    check(f.previewVisible, "chat poster revealed before the gallery background fades")
                    f.send(.changed, delta)
                    let last = f.item.nagramiXPiPSourceFrame(in: f.item.view), alpha = f.background.alpha
                    check(alpha < 1 && alpha > 0, "background reveals underlying app during motion")
                    check(f.item.nagramiXPiPSwipeTransitionPending && !f.item.controlsVisible, "drag hides native controls")
                    check(f.item.startCount == 0, "drag never starts PiP before release")
                    testClock += held ? 1 : 0.15
                    f.send(.ended, delta, speed: CGPoint(x: delta.x * 8, y: delta.y * 8))
                    check(f.item.startCount == 1 && equal(last, f.item.startFrames[0]), "AVKit receives exact final live rectangle")
                    check(equal(last, f.item.nagramiXPiPSourceFrame(in: f.item.view)), "no scale or position snap at release")
                    check(f.background.alpha == alpha && UIViewPropertyAnimator.started.isEmpty, "no intermediate edge flight or background reset")
                    f.item.complete(true)
                    check(equal(last, f.item.nagramiXPiPSourceFrame(in: f.item.view)), "didStart preserves source until real dismissal")
                    f.send(.ended, delta)
                    check(f.item.startCount == 1, "duplicate ended cannot request a second window")
                    f.controller.reset(animated: false, cancelPreparation: false)
                    check(f.item.nagramiXPiPSwipeView.transform == .identity && f.background.alpha == 1, "hidden gallery/restoration returns original geometry")
                    check(f.item.cancelCount == 0 && !f.item.nagramiXPiPSwipeTransitionPending, "successful handoff never cancels the live system player")
                    check(!f.previewVisible, "dismissal releases only the gesture preview lease")
                }
            }
        }
        do {
            let f = Fixture(); _ = f.begin(CGPoint(x: 0, y: 8)); testClock += 0.1
            f.send(.ended, CGPoint(x: 0, y: 8))
            check(f.item.startCount == 0 && UIViewPropertyAnimator.started.count == 1, "small swipe returns in one animation")
            check(f.item.nagramiXPiPSwipeTransitionPending, "button stays blocked while returning")
            check(f.previewVisible, "poster remains visible throughout cancellation animation")
            check(f.background.alpha == 1 && f.item.nagramiXPiPSwipeView.transform == .identity && f.item.controlsVisible, "return animator restores video/background/controls together")
            UIViewPropertyAnimator.started.last!.finish()
            check(!f.item.nagramiXPiPSwipeTransitionPending, "return completion releases button")
            check(!f.previewVisible, "completed cancellation restores ordinary gallery hiding")
        }
        for synchronousRejection in [false, true] {
            let f = Fixture(); f.item.requestAccepted = !synchronousRejection
            _ = f.begin(.zero); f.send(.changed, CGPoint(x: 0, y: -100)); testClock += 0.15
            f.send(.ended, CGPoint(x: 0, y: -100), speed: CGPoint(x: 0, y: -800))
            if !synchronousRejection { f.item.complete(false) }
            check(UIViewPropertyAnimator.started.count == 1 && f.background.alpha == 1, "native rejection has one reversible return")
            UIViewPropertyAnimator.started.last!.finish()
            check(!f.item.nagramiXPiPSwipeTransitionPending, "rejection allows retry")
        }
        do {
            let f = Fixture(); f.item.synchronousResult = false
            _ = f.begin(.zero); testClock += 0.15
            f.send(.ended, CGPoint(x: 0, y: -100), speed: CGPoint(x: 0, y: -900))
            check(UIViewPropertyAnimator.started.count == 1 && f.background.alpha == 1,
                "synchronous native failure cannot leave a committed or invisible gallery")
            UIViewPropertyAnimator.started.last!.finish()
            check(!f.item.nagramiXPiPSwipeTransitionPending, "synchronous failure releases source after return")
        }
        do {
            let f = Fixture(); _ = f.begin(.zero); f.send(.changed, CGPoint(x: 0, y: 100))
            testClock += 0.15; f.send(.ended, CGPoint(x: 0, y: 100), speed: CGPoint(x: 0, y: 900))
            let old = f.item!, stale = old.completions[0]
            f.item = GalleryItemNode(parent: f.content, aspect: 1); f.controller.itemChanged()
            check(!old.nagramiXPiPSwipeTransitionPending && f.background.alpha == 1, "item change restores old source")
            check(f.begin(.zero), "next video can start its own gesture")
            f.send(.changed, CGPoint(x: 0, y: -70)); let last = f.item.nagramiXPiPSwipeView.transform, alpha = f.background.alpha
            stale(false)
            check(f.item.nagramiXPiPSwipeView.transform == last && f.background.alpha == alpha, "stale native completion cannot reset next video")
        }
        do {
            let f = Fixture(); _ = f.begin(CGPoint(x: 0, y: 60)); f.send(.cancelled, .zero)
            let oldAnimator = UIViewPropertyAnimator.started.last!
            let presented = TestLayer(); presented.transform = CGAffineTransform(translationX: 0, y: 45).scaledBy(x: 0.8, y: 0.8)
            let presentedBackground = TestLayer(); presentedBackground.opacity = 0.6
            f.item.nagramiXPiPSwipeView.layer.presented = presented; f.background.layer.presented = presentedBackground
            check(f.begin(.zero), "return can be interrupted by a new finger movement")
            check(f.item.nagramiXPiPSwipeView.transform == presented.transform && abs(f.background.alpha - 0.6) < 0.000001, "interruption starts at presentation geometry/opacity")
            f.item.nagramiXPiPSwipeView.layer.presented = nil; f.background.layer.presented = nil
            oldAnimator.finish()
            check(f.item.nagramiXPiPSwipeTransitionPending, "late return callback cannot clear new transition")
            check(f.previewVisible, "late cancellation must not hide the next gesture's poster")
            f.send(.cancelled, .zero); UIViewPropertyAnimator.started.last!.finish()
            check(f.item.nagramiXPiPSwipeView.transform == .identity && f.background.alpha == 1, "second cancellation restores original baseline")
        }
        do {
            let f = Fixture(); _ = f.begin(CGPoint(x: 0, y: 60)); f.send(.cancelled, .zero)
            let old = f.item!, animator = UIViewPropertyAnimator.started.last!
            f.item = GalleryItemNode(parent: f.content, aspect: 9 / 16); f.controller.itemChanged()
            check(!old.nagramiXPiPSwipeTransitionPending && f.background.alpha == 1, "changing videos during return releases old source")
            _ = f.begin(CGPoint(x: 0, y: -80)); let alpha = f.background.alpha
            animator.finish()
            check(f.item.nagramiXPiPSwipeTransitionPending && f.background.alpha == alpha, "old return cannot alter a different video's drag")
        }
        do {
            let f = Fixture(); _ = f.begin(CGPoint(x: 0, y: 70))
            f.item.nagramiXPiPNativeTransitionInFlight = true
            let transform = f.item.nagramiXPiPSwipeView.transform, alpha = f.background.alpha
            f.controller.cancel()
            check(f.item.nagramiXPiPSwipeTransitionPending && f.item.nagramiXPiPSwipeView.transform == transform && f.background.alpha == alpha,
                "resign active during native start does not detach or reset the source")
            f.item.nagramiXPiPNativeTransitionInFlight = false; UIAccessibility.isReduceMotionEnabled = true
            f.controller.cancel()
            check(UIViewPropertyAnimator.started.isEmpty && f.background.alpha == 1, "Reduce Motion cancellation is immediate")
        }
        do {
            let f = Fixture(); f.item.permitted = false
            check(!f.begin(.zero), "disabled/zoomed source preserves native gestures")
            f.item.permitted = true; UIApplication.shared.applicationState = .background
            check(!f.begin(.zero), "background app cannot acquire gesture")
            UIApplication.shared.applicationState = .active
            for control in [UISlider(frame: f.content.bounds), UISwitch(frame: f.content.bounds)] {
                control.superview = f.content
                let touch = UITouch(view: control, timestamp: testClock, point: CGPoint(x: 195, y: 422))
                check(!f.controller.gestureRecognizer(f.controller.recognizer, shouldReceive: touch), "slider/switch keep their touches")
            }
            _ = f.begin(.zero); f.send(.changed, CGPoint(x: CGFloat.nan, y: 1))
            UIViewPropertyAnimator.started.last!.finish()
            check(f.item.startCount == 0 && !f.item.nagramiXPiPSwipeTransitionPending && f.background.alpha == 1, "nonfinite gesture restores safely")
        }
        print("PASS: \(checks) production gesture handoff/cancellation/background checks")
    }
}
