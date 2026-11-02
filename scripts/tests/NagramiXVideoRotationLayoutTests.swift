import Foundation

private var checks = 0
private func check(_ value: Bool, _ message: String) {
    checks += 1
    if !value { print("FAIL: " + message); exit(1) }
}
private func near(_ a: CGFloat, _ b: CGFloat) -> Bool { abs(a - b) < 0.00001 }

@main struct Tests {
    static func main() {
        let screens: [CGSize] = [.init(width: 320, height: 568), .init(width: 375, height: 667),
                                .init(width: 390, height: 844), .init(width: 430, height: 932)]
        let videos: [CGSize] = [.init(width: 1920, height: 1080), .init(width: 1080, height: 1920),
                               .init(width: 640, height: 640), .init(width: 3840, height: 1646),
                               .init(width: 320, height: 240), .init(width: 7680, height: 4320)]
        for screen in screens { for video in videos {
            let host = NativeZoomLayout()
            host.scrollNode.view.zoomChanged = { [weak host] in
                guard let host else { return }
                host.scrollViewDidZoom(host.scrollNode.view)
            }
            let content = ASDisplayNode()
            host.zoomableContent = (video, content)
            var rotations = 0
            for cycle in 0..<20 {
                for viewport in [screen, CGSize(width: screen.height, height: screen.width)] {
                    let transition: ContainedViewLayoutTransition = cycle % 2 == 0 ? .immediate : .animated(duration: 0.35, curve: .system)
                    host.containerLayoutUpdated(ContainerViewLayout(size: viewport), navigationBarHeight: 88, transition: transition)
                    check(host.scrollNode.view.bounds.size == viewport, "stale portrait/landscape viewport")
                    check(host.zoomableContent?.1 === content, "video node was replaced")
                    let scale = min(viewport.width / video.width, viewport.height / video.height)
                    check(near(host.scrollNode.view.minimumZoomScale, scale), "wrong aspect-fit minimum")
                    check(near(host.scrollNode.view.zoomScale, scale), "rotation left stale zoom")
                    let frame = content.frame
                    check(near(frame.width, video.width * scale) && near(frame.height, video.height * scale), "video shrank or stretched")
                    check(near(frame.midX, viewport.width / 2) && near(frame.midY, viewport.height / 2), "video not centered")
                    check(near(frame.width, viewport.width) || near(frame.height, viewport.height), "video doesn't use full available dimension")
                    check(frame.width <= viewport.width + 0.001 && frame.height <= viewport.height + 0.001, "unexpected crop")
                    if transition.isAnimated { rotations += 1 }
                    // A user zoom before rotation must be reset by native layout.
                    host.scrollNode.view.zoomScale = host.scrollNode.view.maximumZoomScale
                }
            }
            check(content.layer.scaleAnimations == rotations, "native rotation animation was bypassed")
        } }
        print("PASS: \(checks) actual native zoom-layout checks; repeated portrait/landscape, aspect fit, centering, pinch reset, animation forwarding")
    }
}
