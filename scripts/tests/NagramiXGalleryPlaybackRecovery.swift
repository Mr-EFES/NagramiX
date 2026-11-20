import Foundation
import CoreFoundation

class UIGestureRecognizer {}
final class UIPanGestureRecognizer: UIGestureRecognizer {
    var speed = CGPoint.zero
    var delta = CGPoint.zero
    func velocity(in view: UIScrollView) -> CGPoint { speed }
    func translation(in view: UIScrollView) -> CGPoint { delta }
}
class UIScrollView {
    let panGestureRecognizer = UIPanGestureRecognizer()
    var allowed = true
    func gestureRecognizerShouldBegin(_ gesture: UIGestureRecognizer) -> Bool { allowed }
}
// DISMISS SCROLL VIEW

class Item {}
final class Pager {
    weak var central: Item?
    func centralItemNode() -> Item? { central }
}
final class Gallery {
    let pager = Pager()
    var alpha = 1.0
    var view: Gallery { self }
    var nagramiXPiPGalleryNode: Gallery? { self }
}
final class Decoration {
    func setNagramiXPiPTransitionActive(_ enabled: Bool) {}
}
typealias GalleryVideoDecoration = Decoration
final class Surface {
    var decoration: AnyObject?
    var view: Surface { self }
    var window: Int? = 1
    var bounds = CGRect(x: 0, y: 0, width: 320, height: 240)
    var ownsContentNode = true
}
// VISUAL STATE
final class Restore: Item {
    let gallery = Gallery()
    var videoNode: Surface? = Surface()
    var nagramiXPiPSourceVideoNode: Surface?
    fileprivate var nagramiXPiPVisualState = NagramiXNativePiPVisualState()
    var nagramiXPiPHandoffGeneration: Int { nagramiXPiPVisualState.generation }
    var nagramiXWebPiPTransitionStarted = false
    var nagramiXPiPDeferredDimensions: CGSize?
    var nagramiXPiPRevealScheduled = false
    var nagramiXPiPRestoreDeadline = 1.0
    var dismissed = false
    var cleanups: [String] = []
    func galleryController() -> Gallery? { gallery }
    func nagramiXNativePiPRendererReady() -> Bool { false }
    func nagramiXApplyVideoDimensions(_ size: CGSize, afterPiPStop: Bool) {}
    func nagramiXFinishSystemWebPiP(stop: Bool) { cleanups.append("web"); nagramiXPiPVisualState.cancel() }
    func nagramiXFinishNativePiPVisualTransition(animated: Bool) { cleanups.append("native"); nagramiXPiPVisualState.cancel() }
    func completeCustomDismiss(_ pip: Bool) { dismissed = true }
    // FINISH RESTORE
}
func CACurrentMediaTime() -> Double { 10 }

enum MediaPlayerPlaybackStatus: Equatable {
    case playing, paused, buffering(initial: Bool, whilePlaying: Bool, progress: Double, display: Bool)
}
struct MediaPlayerStatus {
    var generationTimestamp: Double, duration: Double, dimensions: CGSize, timestamp: Double, baseRate: Double
    var seekId: Int, status: MediaPlayerPlaybackStatus, soundEnabled: Bool
}
protocol WebEmbedImplementation {}
struct FixtureAppBundle {
    let bundleIdentifier: String? = "com.Mr-EFES.NagramiX"
    func path(forResource name: String, ofType type: String) -> String? {
        URL(fileURLWithPath: #filePath).deletingLastPathComponent().appendingPathComponent(name + "." + type).path
    }
}
func getAppBundle() -> FixtureAppBundle { FixtureAppBundle() }
struct WKUserScript {
    enum InjectionTime { case atDocumentEnd }
    let source: String, injectionTime: InjectionTime, forMainFrameOnly: Bool
}
class WKUserContentController {
    func addUserScript(_ script: WKUserScript) {}
}
class WKWebView {
    var origin: URL?, html = ""
    func loadHTMLString(_ html: String, baseURL: URL?) { self.html = html; self.origin = baseURL }
}
class Queue {
    static func mainQueue() -> Queue { Queue() }
    func async(_ job: () -> Void) { job() }
    func after(_ seconds: Double, _ job: () -> Void) { job() }
}
// YOUTUBE CONTROLLER

@main struct Tests {
    static func main() {
        let scroll = GalleryDismissScrollView()
        let pan = scroll.panGestureRecognizer
        for x in [-100, 100] {
            pan.speed = CGPoint(x: x, y: -45)
            precondition(!scroll.gestureRecognizerShouldBegin(pan))
            pan.speed = .zero
            pan.delta = CGPoint(x: x, y: 3)
            precondition(!scroll.gestureRecognizerShouldBegin(pan))
        }
        for y in [-100, 100] {
            pan.speed = CGPoint(x: 4, y: y)
            precondition(scroll.gestureRecognizerShouldBegin(pan))
        }
        scroll.allowed = false
        precondition(!scroll.gestureRecognizerShouldBegin(pan))
        precondition(!scroll.gestureRecognizerShouldBegin(UIGestureRecognizer()))

        for web in [false, true] {
            let next = Item(), old = Restore()
            old.nagramiXWebPiPTransitionStarted = web
            old.nagramiXPiPVisualState.restore()
            precondition(old.nagramiXPiPVisualState.presented(generation: old.nagramiXPiPHandoffGeneration))
            old.nagramiXPiPVisualState.stopped()
            old.videoNode?.ownsContentNode = false
            old.gallery.pager.central = next
            withExtendedLifetime(next) {
                old.nagramiXTryFinishNativePiPRestore()
                old.nagramiXTryFinishNativePiPRestore()
                precondition(old.gallery.alpha == 1 && !old.dismissed)
                precondition(old.cleanups == [web ? "web" : "native"])
            }
        }

        let youtube = YoutubeEmbedImplementation(videoId: "sample", timestamp: 0)
        var states: [MediaPlayerStatus] = []
        let page = WKWebView()
        youtube.setup(page, userContentController: WKUserContentController(), evaluateJavaScript: { _, _ in },
                      updateStatus: { states.append($0) }, onPlaybackStarted: {})
        precondition(page.origin?.absoluteString == "https://com.mr-efes.nagramix")
        precondition(page.html.replacingOccurrences(of: "\\/", with: "/").contains(page.origin!.absoluteString))
        youtube.play()
        youtube.callback(url: URL(string: "embed://onState?failed=true&playback=-1&duration=0")!)
        precondition(states.last?.status == .paused && states.last?.soundEnabled == false)
        youtube.callback(url: URL(string: "embed://onState?failed=false&playback=1&duration=32&position=9")!)
        precondition(states.last?.status == .playing && states.last?.soundEnabled == true && states.last?.timestamp == 9)
        youtube.pause()
        var commands: [String] = []
        youtube.evalImpl = { command, _ in commands.append(command) }
        youtube.callback(url: URL(string: "embed://onReady")!)
        precondition(!commands.contains("play();"))
        print("PASS: horizontal/vertical gestures, late WebKit/AVKit restore after paging, provider error and recovery")
    }
}
