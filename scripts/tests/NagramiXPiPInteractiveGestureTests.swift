import Foundation

@main struct NativeGestureTests {
    final class Fixture {
        let host: UIView
        let content: UIView
        let background: UIView
        var item: GalleryItemNode!
        var available = true
        var prepareControls = 0
        var preview = false
        var controller: NagramiXPiPGestureController!
        init(_ landscape: Bool = false, _ aspect: CGFloat = 16 / 9) {
            let frame = CGRect(x: 0, y: 0, width: landscape ? 844 : 390, height: landscape ? 390 : 844)
            host = UIView(frame: frame); content = UIView(frame: frame); background = UIView(frame: frame)
            content.superview = host; background.superview = host
            item = GalleryItemNode(parent: content, aspect: aspect)
            controller = NagramiXPiPGestureController(host: host, content: content, background: background,
                currentItem: { [weak self] in self?.item }, available: { [weak self] in self?.available == true },
                sourcePreview: { [weak self] in self?.preview = $0 }, prepareControls: { [weak self] in self?.prepareControls += 1 })
            UIApplication.shared.applicationState = .active; testClock = 10
        }
        func begin() {
            controller.recognizer.speed = CGPoint(x: 0, y: 200)
            let touch = UITouch(view: item.nagramiXPiPSwipeView, timestamp: testClock, point: item.view.center)
            precondition(controller.gestureRecognizer(controller.recognizer, shouldReceive: touch))
            precondition(controller.gestureRecognizerShouldBegin(controller.recognizer))
            send(.began, .zero)
        }
        func send(_ state: UIGestureRecognizer.State, _ delta: CGPoint, _ velocity: CGPoint = .zero) {
            controller.recognizer.state = state; controller.recognizer.delta = delta; controller.recognizer.speed = velocity
            controller.testDrivePan()
        }
    }
    static func main() {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool) { precondition(value()); checks += 1 }
        for landscape in [false, true] {
            for aspect: CGFloat in [16 / 9, 9 / 16, 1] {
                for direction: CGFloat in [-1, 1] {
                    for result in [false, true] {
                        let f = Fixture(landscape, aspect)
                        let original = f.item.nagramiXPiPSourceFrame(in: f.item.view)
                        f.begin()
                        for distance: CGFloat in [1, 20, 60, 200, 350] {
                            f.send(.changed, CGPoint(x: 0, y: distance * direction))
                            check(f.item.nagramiXPiPSourceFrame(in: f.item.view) == original.offsetBy(dx: 0, dy: min(120, distance) * direction))
                            check(f.item.nagramiXPiPSwipeView.transform == CGAffineTransform(translationX: 0, y: min(120, distance) * direction) && f.background.alpha == 1)
                            check(f.item.controlsVisible && !f.preview && f.prepareControls == 0)
                            check(f.item.prepareCount == 0 && f.item.startCount == 0)
                        }
                        testClock += 0.3
                        f.send(.ended, CGPoint(x: 0, y: 200 * direction), CGPoint(x: 0, y: 600 * direction))
                        check(f.item.startCount == 1 && f.item.startFrames[0] == original.offsetBy(dx: 0, dy: 120 * direction))
                        check(f.item.controlsVisible && f.item.nagramiXPiPSwipeTransitionPending)
                        f.item.complete(result)
                        check(!f.item.nagramiXPiPSwipeTransitionPending && f.item.nagramiXPiPSwipeView.transform == .identity)
                        f.send(.ended, CGPoint(x: 0, y: 200 * direction))
                        check(f.item.startCount == 1)
                    }
                }
            }
        }
        do {
            let f = Fixture(); f.begin(); f.send(.changed, CGPoint(x: 0, y: 80)); f.send(.cancelled, .zero)
            check(f.item.startCount == 0 && f.item.controlsVisible && !f.item.nagramiXPiPSwipeTransitionPending)
            f.begin(); f.send(.ended, CGPoint(x: 0, y: 3))
            check(f.item.startCount == 0)
        }
        for synchronous in [false, true] {
            let f = Fixture(); f.item.synchronousResult = synchronous
            f.begin(); f.send(.ended, CGPoint(x: 0, y: 200))
            check(f.item.startCount == 1 && !f.item.nagramiXPiPSwipeTransitionPending)
        }
        do {
            let f = Fixture(); f.begin(); f.item.requestAccepted = false
            f.send(.ended, CGPoint(x: 0, y: 200))
            check(!f.item.nagramiXPiPSwipeTransitionPending && f.item.controlsVisible)
            f.item.requestAccepted = true; f.begin(); f.send(.ended, CGPoint(x: 0, y: 200))
            let previous = f.item!
            f.item = GalleryItemNode(parent: f.content, aspect: 1)
            f.controller.itemChanged(); previous.complete(false)
            check(f.item.startCount == 0 && f.item.controlsVisible)
        }
        do {
            let f = Fixture()
            for velocity in [CGPoint(x: 200, y: 0), CGPoint(x: 200, y: 100), CGPoint(x: CGFloat.nan, y: 200)] {
                f.controller.recognizer.speed = velocity
                check(!f.controller.gestureRecognizerShouldBegin(f.controller.recognizer))
            }
            f.item.nagramiXPiPSwipeView.transform = CGAffineTransform(translationX: 90, y: -300).scaledBy(x: 0.3, y: 0.3)
            f.begin()
            check(f.item.nagramiXPiPSwipeView.transform == .identity)
            UIApplication.shared.applicationState = .inactive
            f.send(.ended, CGPoint(x: 0, y: 200))
            check(f.item.startCount == 0 && f.item.controlsVisible)
        }
        print("PASS: \(checks) interactive gesture checks, full-size source throughout, portrait/landscape/aspects, up/down, failures, stale callbacks, horizontal paging; UIKit/AVKit pending")
    }
}
