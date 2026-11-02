import Foundation

@main struct EntryGestureTests {
    static func main() {
        NativeGestureTests.main()
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ message: String) {
            checks += 1
            if !value() {
                FileHandle.standardError.write(Data(("FAIL: " + message + "\n").utf8))
                exit(1)
            }
        }
        for synchronous in [false, true] {
            for result in [false, true] {
                let f = NativeGestureTests.Fixture()
                if synchronous { f.item.synchronousResult = result }
                f.begin(); f.send(.ended, CGPoint(x: 0, y: 200))
                if !synchronous { f.item.complete(result) }
                check(f.item.failureCount == (result ? 0 : 1), "rejected swipe reports once; successful swipe stays silent")
                check(!f.item.nagramiXPiPSwipeTransitionPending, "completion releases pending gesture")
                f.item.complete(false)
                check(f.item.failureCount == (result ? 0 : 1), "late duplicate callback cannot show another failure")
            }
        }
        do {
            let f = NativeGestureTests.Fixture(); f.item.requestAccepted = false
            f.begin(); f.send(.ended, CGPoint(x: 0, y: -200))
            check(f.item.failureCount == 1 && !f.item.nagramiXPiPSwipeTransitionPending, "synchronous admission rejection reports once")
            f.item.requestAccepted = true; f.begin(); f.send(.ended, CGPoint(x: 0, y: -200)); f.item.complete(true)
            check(f.item.startCount == 2 && f.item.failureCount == 1, "retry after rejection can succeed")
        }
        do {
            let f = NativeGestureTests.Fixture(); f.begin(); f.send(.cancelled, .zero)
            check(f.item.failureCount == 0 && f.item.startCount == 0, "canceled touch never reports a PiP failure")
            f.begin(); f.send(.ended, CGPoint(x: 0, y: 200)); f.controller.cancel(); f.item.complete(false)
            check(f.item.failureCount == 0 && !f.item.nagramiXPiPSwipeTransitionPending, "canceled request ignores a stale failure")
        }
        do {
            let f = NativeGestureTests.Fixture(); f.begin(); f.send(.ended, CGPoint(x: 0, y: 200))
            let old = f.item!
            f.item = GalleryItemNode(parent: f.content, aspect: 1)
            f.controller.itemChanged(); old.complete(false)
            check(old.failureCount == 0 && f.item.failureCount == 0, "paging cannot show a failure over a different video")
        }
        do {
            let f = NativeGestureTests.Fixture(); f.begin()
            UIApplication.shared.applicationState = .inactive
            f.send(.ended, CGPoint(x: 0, y: 200))
            check(f.item.failureCount == 0 && f.item.startCount == 0, "inactive application does not present feedback")
        }
        print("PASS: \(checks) actual gesture feedback/retry/cancel/stale checks; UIKit/AVKit boundary")
    }
}
