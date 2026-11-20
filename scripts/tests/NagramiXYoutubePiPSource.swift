// Minimal view hierarchy for exercising the production bridge on a host without UIKit.
#if canImport(CoreGraphics)
import CoreGraphics
#else
struct CGAffineTransform {
    let a: CGFloat, d: CGFloat
    init(scaleX: CGFloat, y: CGFloat) { self.a = scaleX; self.d = y }
}
#endif
class UIView {
    var bounds = CGRect.zero
    var transform = CGAffineTransform(scaleX: 1.0, y: 1.0)
    var frame: CGRect
    weak var superview: UIView?
    var subviews: [UIView] = []
    var window: UIWindow? { (self as? UIWindow) ?? self.superview?.window }
    var isUserInteractionEnabled = true
    var accessibilityElementsHidden = false
    var clipsToBounds = false

    init(frame: CGRect = .zero) { self.frame = frame }
    func convert(_ rect: CGRect, to: UIView?) -> CGRect { rect }
    func insertSubview(_ view: UIView, at index: Int) {
        view.removeFromSuperview()
        self.subviews.insert(view, at: index)
        view.superview = self
    }
    func addSubview(_ view: UIView) {
        view.removeFromSuperview()
        self.subviews.append(view)
        view.superview = self
    }
    func removeFromSuperview() {
        self.superview?.subviews.removeAll { $0 === self }
        self.superview = nil
    }
}
final class UIWindow: UIView {}

struct DispatchTime: Comparable {
    var seconds: Double
    static var clock = 0.0
    static func now() -> DispatchTime { DispatchTime(seconds: clock) }
    static func + (time: DispatchTime, seconds: Double) -> DispatchTime { DispatchTime(seconds: time.seconds + seconds) }
    static func < (left: DispatchTime, right: DispatchTime) -> Bool { left.seconds < right.seconds }
}

// ACTUAL_BRIDGE

@main private struct YouTubePiPTests {
    static func main() {
        let controller = WKUserContentController()
        let bridge = NagramiXWebSystemPictureInPicture(controller: controller, isYouTube: true, pipEnabled: true)
        let window = UIWindow(), chat = UIView(), gallery = UIView(), web = WKWebView()
        let mainFrame = WKFrameInfo(1), videoFrame = WKFrameInfo(2)
        window.addSubview(chat)
        window.addSubview(gallery)
        gallery.addSubview(web)
        bridge.webView = web

        func lastProbe() -> [String: Any] {
            web.calls.last { $0.0["command"] as? String == "probe" }!.0
        }
        func receive(_ kind: String, _ probe: [String: Any], _ frame: WKFrameInfo, active: Bool = false, restore: Bool = false) {
            var body = probe
            body["kind"] = kind
            body["frameKey"] = String(frame.id)
            body["video"] = "0"
            body["playing"] = true
            body["area"] = 100.0
            body["active"] = active
            body["restore"] = restore
            bridge.userContentController(controller, didReceive: WKScriptMessage(body: body, frameInfo: frame))
        }
        func start() -> [String: Any] {
            precondition(bridge.begin())
            precondition(!bridge.begin())
            let probe = lastProbe()
            DispatchQueue.main.run()
            precondition(bridge.keepsPlaybackActive && !bridge.isActive, "slow iframe lost the first request")
            receive("candidate", probe, videoFrame)
            DispatchQueue.main.run()
            precondition(web.calls.last!.0["command"] as? String == "enter" && web.calls.last!.1 === videoFrame)
            return probe
        }

        let first = start()
        guard let failedFrame = web.reply else { fatalError("missing WebKit completion") }
        failedFrame(.failure(NSError(domain: "frame removed", code: 1)))
        precondition(web.calls.last!.0["command"] as? String == "probe")
        receive("candidate", first, videoFrame)
        DispatchQueue.main.run()
        receive("unavailable", first, videoFrame)
        precondition(web.calls.last!.0["command"] as? String == "probe", "replaced video must be rediscovered")
        receive("candidate", first, videoFrame)
        DispatchQueue.main.run()
        receive("state", first, mainFrame, active: true)
        precondition(!bridge.isActive && web.superview === gallery)
        receive("state", first, videoFrame, active: true)
        guard let host = web.superview else { fatalError("lost source") }
        precondition(host !== gallery && window.subviews.first === host)
        precondition(!host.isUserInteractionEnabled && host.accessibilityElementsHidden)
        receive("state", first, videoFrame, active: true)
        precondition(web.superview === host && window.subviews.count == 3)
        gallery.removeFromSuperview()
        precondition(bridge.active.value && web.window === window, "dismissing gallery detached playing WebKit source")

        var restoreCompletion: ((Bool) -> Void)?
        bridge.restore = { restoreCompletion = $0 }
        receive("state", first, videoFrame, restore: true)
        precondition(web.superview === host && web.window === window && restoreCompletion != nil)
        precondition(!bridge.begin(), "restore must keep ownership until gallery reattaches")
        window.addSubview(gallery)
        restoreCompletion?(true)
        precondition(web.superview === gallery && host.superview == nil && !bridge.keepsPlaybackActive)
        let second = start()
        failedFrame(.failure(NSError(domain: "late completion", code: 1)))
        precondition(web.calls.last!.0["command"] as? String == "enter")
        receive("state", first, videoFrame, active: true)
        precondition(web.superview === gallery)
        receive("state", second, videoFrame, active: true)
        restoreCompletion?(true)
        precondition(bridge.active.value && web.window === window, "late restoration closed the next session")
        bridge.stop()
        precondition(web.superview === gallery && !bridge.keepsPlaybackActive && window.subviews.count == 2)

        let close = start()
        receive("state", close, videoFrame, active: true)
        gallery.removeFromSuperview()
        receive("state", close, videoFrame, restore: false)
        precondition(!bridge.active.value && web.superview === gallery && window.subviews.count == 1)
        window.addSubview(gallery)
        let transferred = start()
        receive("state", transferred, videoFrame, active: true)
        chat.addSubview(web)
        bridge.stop()
        precondition(web.superview === chat && window.subviews.count == 2, "stop stole a transferred player")

        precondition(bridge.begin())
        let cancelled = lastProbe()
        DispatchQueue.main.run()
        bridge.stop()
        let callCount = web.calls.count
        receive("candidate", cancelled, videoFrame)
        DispatchQueue.main.run()
        precondition(!bridge.keepsPlaybackActive && web.calls.count == callCount)
        precondition(bridge.begin())
        DispatchTime.clock += 6.0
        DispatchQueue.main.run()
        precondition(!bridge.keepsPlaybackActive && web.superview === chat, "empty iframe outlived entry timeout")
        let generic = NagramiXWebSystemPictureInPicture(controller: controller)
        generic.webView = web
        precondition(generic.begin())
        DispatchQueue.main.run()
        precondition(!generic.keepsPlaybackActive, "unrelated embeds retained an empty request")
        print("YouTube PiP delayed frame, replacement, attachment, close, restoration and cancellation passed")
    }
}
