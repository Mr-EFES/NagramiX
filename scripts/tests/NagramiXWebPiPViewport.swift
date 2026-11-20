private final class ScaledGallery: UIView {
    override func convert(_ rect: CGRect, to view: UIView?) -> CGRect {
        CGRect(x: 0, y: 270, width: rect.width / 4, height: rect.height / 4)
    }
}

@main private struct ViewportTests {
    static func main() {
        let window = UIWindow(), gallery = ScaledGallery()
        let view = WKWebView()
        let viewport = CGRect(x: 10, y: 8, width: 1280, height: 720)
        let controller = WKUserContentController()
        let bridge = NagramiXWebSystemPictureInPicture(controller: controller, isYouTube: true, pipEnabled: true)
        window.addSubview(gallery)
        gallery.addSubview(view)
        view.frame = viewport
        bridge.webView = view
        for _ in 0..<2 {
            precondition(bridge.begin())
            let probe = view.calls.last { $0.0["command"] as? String == "probe" }!.0
            let frame = WKFrameInfo(1)
            var reply = probe
            reply["frameKey"] = "1"
            reply["kind"] = "candidate"
            reply["video"] = "1"
            reply["area"] = 100.0
            reply["playing"] = true
            bridge.userContentController(controller, didReceive: WKScriptMessage(body: reply, frameInfo: frame))
            DispatchQueue.main.run()
            reply["kind"] = "state"
            reply["active"] = true
            bridge.userContentController(controller, didReceive: WKScriptMessage(body: reply, frameInfo: frame))
            let host = view.superview!
            precondition(host !== gallery && host.bounds == viewport && host.transform.a == 0.25 && host.transform.d == 0.25)
            bridge.stop()
            precondition(view.superview === gallery && view.frame == viewport && host.superview == nil)
        }
        print("PASS: two entries and restores keep the same web view, viewport and source scale")
    }
}
