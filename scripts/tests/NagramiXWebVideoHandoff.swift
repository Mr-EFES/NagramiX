private class GalleryItemNode {}
private final class UniversalVideoGalleryItemNode: GalleryItemNode {
    let waitsForEmbeddedPictureInPicture: Bool
    init(embedded: Bool) { self.waitsForEmbeddedPictureInPicture = embedded }
}
private final class GalleryPager {
    var item: GalleryItemNode?
    func centralItemNode() -> GalleryItemNode? { self.item }
}
private final class GalleryScroll {
    var contentOffset = CGPoint(x: 0, y: 720)
    let contentSize = CGSize(width: 320, height: 1800)
    func setContentOffset(_ point: CGPoint, animated: Bool) { self.contentOffset = point }
}
private final class Gallery {
    let pager = GalleryPager(), scrollView = GalleryScroll()
    weak var nagramiXNativePictureInPictureItem: GalleryItemNode?
    var nagramiXNativePictureInPictureDistance: CGFloat?
    var visibleDistance: CGFloat = 120
    func updateDismissAppearance(distanceFromEquilibrium: CGFloat) { self.visibleDistance = distanceFromEquilibrium }
    // SWIPE LOCK
}

private final class WebFixture {
    let player = Player(youtube: true, pip: true, bg: true)
    let frame = WKFrameInfo(7)
    var bridge: NagramiXWebSystemPictureInPicture { self.player.nagramiXSystemPiP }
    var probe: [String: Any] { self.player.view.calls.last { $0.0["command"] as? String == "probe" }!.0 }

    func send(_ request: [String: Any], _ kind: String, _ values: [String: Any]) {
        var body = request.merging(values) { _, value in value }
        body["kind"] = kind
        body["frameKey"] = "7"
        self.bridge.userContentController(self.player.controller, didReceive: WKScriptMessage(body: body, frameInfo: self.frame))
    }
    func media(_ reason: String, playing: Bool) {
        self.send(self.probe, "media", ["reason": reason, "playing": playing, "ended": false, "area": 220.0, "allowed": self.bridge.playbackAllowed])
    }
}

@main private enum HandoffTests {
    static func main() {
        for embedded in [true, false] {
            let gallery = Gallery()
            gallery.pager.item = UniversalVideoGalleryItemNode(embedded: embedded)
            gallery.nagramiXLockNativePictureInPictureSwipe()
            precondition(gallery.scrollView.contentOffset.y == (embedded ? 600 : 720))
            precondition(gallery.visibleDistance == (embedded ? 0 : 120))
        }
        let f = WebFixture()
        precondition(f.bridge.begin())
        let first = f.probe
        f.bridge.documentDidChange(continuingPlayback: true)
        let second = f.probe
        precondition(first["request"] as? String != second["request"] as? String)
        f.send(second, "candidate", ["video": "1", "area": 22.0, "playing": true])
        DispatchQueue.main.run()
        f.send(second, "unavailable", [:])
        let third = f.probe
        precondition(second["request"] as? String != third["request"] as? String)
        f.send(third, "candidate", ["video": "2", "area": 22.0, "playing": true])
        DispatchQueue.main.run()
        f.send(second, "state", ["active": true])
        precondition(!f.bridge.isActive)
        f.send(third, "state", ["active": true])
        precondition(f.bridge.isActive)
        f.send(second, "state", ["active": false])
        precondition(f.bridge.isActive)
        f.bridge.stop()
        precondition(f.bridge.begin())
        f.bridge.documentDidChange(continuingPlayback: false)
        precondition(!f.bridge.keepsPlaybackActive)
        precondition(f.bridge.begin())
        DispatchTime.clock += 6
        f.bridge.documentDidChange(continuingPlayback: true)
        precondition(!f.bridge.keepsPlaybackActive, "a reloaded page cannot extend discovery indefinitely")

        for pip in [false, true] {
            let audio = WebFixture()
            precondition(audio.bridge.begin())
            let probe = audio.probe
            if pip {
                audio.send(probe, "candidate", ["video": "3", "area": 22.0, "playing": true])
                DispatchQueue.main.run()
                audio.send(probe, "state", ["active": true])
            } else {
                audio.bridge.setYouTubePolicy(true, pipEnabled: false, backgroundEnabled: true)
            }
            audio.bridge.setBackground(true)
            audio.bridge.setApplicationActive(false)
            audio.media("playing", playing: true)
            audio.player.nagramiXPublishPlaybackStatus(sample(.playing))
            audio.media("detached", playing: false)
            audio.media("loadedmetadata", playing: false)
            precondition(audio.bridge.actualMediaPlaying == true && audio.bridge.playbackAllowed)
            audio.media("playing", playing: true)
            DispatchQueue.main.run()
            precondition(audio.player.statusValue.value.status == .playing && audio.bridge.isActive == pip)
            audio.media("detached", playing: false)
            DispatchQueue.main.run()
            precondition(audio.bridge.actualMediaPlaying == false && audio.player.statusValue.value.status == .paused)
            audio.media("playing", playing: true)
            audio.media("detached", playing: false)
            audio.bridge.setPlaybackAllowed(false)
            precondition(audio.bridge.actualMediaPlaying == false && !audio.bridge.playbackAllowed)
            precondition(audio.player.impl.plays == 0, "a handoff never sends an unsolicited play")
        }
        print("PASS: swipe remains opaque, navigation and DOM replacement, stale callbacks, bounded audio handoff with and without PiP")
    }
}
