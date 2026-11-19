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
    var probe: [String: Any] {
        guard let call = self.player.view.calls.last(where: { $0.0["command"] as? String == "probe" }) else {
            failHandoff("the web view never received a probe")
        }
        return call.0
    }

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

private func failHandoff(_ message: String) -> Never {
    FileHandle.standardError.write(Data("Web video handoff: \(message)\n".utf8))
    exit(1)
}

private func requireHandoff(_ condition: Bool, _ message: String) {
    if !condition { failHandoff(message) }
}

@main private enum HandoffTests {
    static func main() {
        for embedded in [true, false] {
            let gallery = Gallery()
            gallery.pager.item = UniversalVideoGalleryItemNode(embedded: embedded)
            gallery.nagramiXLockNativePictureInPictureSwipe()
            requireHandoff(gallery.scrollView.contentOffset.y == (embedded ? 600 : 720), "swipe offset for embedded=\(embedded)")
            requireHandoff(gallery.visibleDistance == (embedded ? 0 : 120), "swipe appearance for embedded=\(embedded)")
        }
        let f = WebFixture()
        // The app owns the player and view throughout the interaction. The bridge borrows the view.
        defer { withExtendedLifetime(f) {} }
        requireHandoff(f.bridge.begin(), "first entry")
        let first = f.probe
        f.bridge.documentDidChange(continuingPlayback: true)
        let second = f.probe
        requireHandoff(first["request"] as? String != second["request"] as? String, "navigation must renew the request")
        f.send(second, "candidate", ["video": "1", "area": 22.0, "playing": true])
        DispatchQueue.main.run()
        f.send(second, "unavailable", [:])
        let third = f.probe
        requireHandoff(second["request"] as? String != third["request"] as? String, "unavailable frame must renew the request")
        f.send(third, "candidate", ["video": "2", "area": 22.0, "playing": true])
        DispatchQueue.main.run()
        f.send(second, "state", ["active": true])
        requireHandoff(!f.bridge.isActive, "stale entry must be ignored")
        f.send(third, "state", ["active": true])
        requireHandoff(f.bridge.isActive, "replacement frame must enter PiP")
        f.send(second, "state", ["active": false])
        requireHandoff(f.bridge.isActive, "stale exit must be ignored")
        f.bridge.stop()
        requireHandoff(f.bridge.begin(), "entry after stop")
        f.bridge.documentDidChange(continuingPlayback: false)
        requireHandoff(!f.bridge.keepsPlaybackActive, "stopping navigation must clear entry")
        requireHandoff(f.bridge.begin(), "entry after stopping navigation")
        DispatchTime.clock += 6
        f.bridge.documentDidChange(continuingPlayback: true)
        requireHandoff(!f.bridge.keepsPlaybackActive, "a reloaded page cannot extend discovery indefinitely")

        for pip in [false, true] {
            let audio = WebFixture()
            defer { withExtendedLifetime(audio) {} }
            requireHandoff(audio.bridge.begin(), "audio fixture entry, PiP=\(pip)")
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
            requireHandoff(audio.bridge.actualMediaPlaying == true && audio.bridge.playbackAllowed, "audio during replacement, PiP=\(pip)")
            audio.media("playing", playing: true)
            DispatchQueue.main.run()
            requireHandoff(audio.player.statusValue.value.status == .playing && audio.bridge.isActive == pip, "resumed audio, PiP=\(pip)")
            audio.media("detached", playing: false)
            DispatchQueue.main.run()
            requireHandoff(audio.bridge.actualMediaPlaying == false && audio.player.statusValue.value.status == .paused, "audio timeout, PiP=\(pip)")
            audio.media("playing", playing: true)
            audio.media("detached", playing: false)
            audio.bridge.setPlaybackAllowed(false)
            requireHandoff(audio.bridge.actualMediaPlaying == false && !audio.bridge.playbackAllowed, "explicit pause, PiP=\(pip)")
            requireHandoff(audio.player.impl.plays == 0, "a handoff never sends an unsolicited play, PiP=\(pip)")
        }
        print("PASS: swipe remains opaque, navigation and DOM replacement, stale callbacks, bounded audio handoff with and without PiP")
    }
}
