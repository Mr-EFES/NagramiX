@main enum PiPPlaybackCommandsTests {
    static var checks = 0
    static func check(_ value: @autoclosure () -> Bool, _ label: String) {
        if !value() { fatalError("PiP playback command regression: " + label) }
        checks += 1
    }
    static func main() {
        let initialStatuses: [Playback?] = [.playing, .paused, .buffering(whilePlaying: true), .buffering(whilePlaying: false), nil]
        for initial in initialStatuses {
            for requested in [true, false] {
                let owner = GalleryHarness()
                let node = owner.videoNode!
                let engine = node.manager.node
                engine.playing = initial == .playing || initial == .buffering(whilePlaying: true)
                engine.timestamp = 47.5
                node.status.emit(initial.map { MediaPlayerStatus(status: $0, duration: 100, timestamp: 47.5) })
                owner.pictureInPictureButtonPressed()
                let pip = AVPictureInPictureController.instances.last!
                let delegate = pip.contentSource!.playbackDelegate!
                let controllers = AVPictureInPictureController.instances.count
                for _ in 0 ..< 3 { delegate.pictureInPictureController(pip, setPlaying: requested) }
                check(engine.playing == requested, "repeated AVKit command sets the requested state from every initial status")
                check(engine.commands == Array(repeating: requested ? "play" : "pause", count: 3), "commands use explicit native play/pause without toggle or cached-status suppression")
                check(node.manager.requestedIds == [42, 42, 42], "commands reach the existing video content identity")
                check(node.seeks.isEmpty && engine.timestamp == 47.5, "playback command preserves position without seeking or replaying from the beginning")
                check(AVPictureInPictureController.instances.count == controllers && pip.contentSource?.sampleBufferDisplayLayer === node.layer, "commands reuse the existing PiP controller and sample-buffer layer")
                let native = owner.nativePictureInPictureContent as! NativePictureInPictureContentImpl
                check(native.contentDelegate!.pictureInPictureControllerIsPlaybackPaused(pip) == !requested, "native paused query follows the reported final state")
                native.stop()
            }
        }

        // Real decoder status arrives asynchronously. Opposing commands must
        // reach the player even while the delegate still sees an old value.
        for initial in initialStatuses {
            let owner = GalleryHarness()
            let node = owner.videoNode!
            let engine = node.manager.node
            engine.playing = true
            engine.publishImmediately = false
            node.status.emit(initial.map { MediaPlayerStatus(status: $0) })
            owner.pictureInPictureButtonPressed()
            let pip = AVPictureInPictureController.instances.last!
            let delegate = pip.contentSource!.playbackDelegate!
            let sequence = [true, true, false, false, true, false, true]
            for value in sequence {
                delegate.pictureInPictureController(pip, setPlaying: value)
                check(engine.playing == value, "latest command wins before status publication")
            }
            check(engine.commands == sequence.map { $0 ? "play" : "pause" }, "no command is lost when status is stale or unavailable")
            engine.publish()
            let native = owner.nativePictureInPictureContent as! NativePictureInPictureContentImpl
            check(!native.contentDelegate!.pictureInPictureControllerIsPlaybackPaused(pip), "delayed status publication remains compatible with the native paused query")
            let before = engine.commands.count
            node.status.emit(MediaPlayerStatus(status: .paused))
            delegate.pictureInPictureController(pip, setPlaying: true)
            check(engine.playing && engine.commands.count == before + 1, "external status changes do not suppress a later explicit command")
            native.stop()
        }

        // Commands still work after native restore and another PiP entry.
        let owner = GalleryHarness()
        owner.pictureInPictureButtonPressed()
        let pip = AVPictureInPictureController.instances.last!
        let delegate = pip.contentSource!.playbackDelegate!
        delegate.pictureInPictureController(pip, setPlaying: false)
        owner.expandPIP()
        owner.pictureInPictureButtonPressed()
        let again = AVPictureInPictureController.instances.last!
        check(again === pip && again.starts == 2, "native controller is reused after restore")
        again.contentSource!.playbackDelegate!.pictureInPictureController(again, setPlaying: true)
        check(owner.videoNode!.manager.node.playing, "play command works after the next native entry")
        check(owner.videoNode!.manager.node.commands == ["pause", "play"], "restore does not add a hidden toggle")
        (owner.nativePictureInPictureContent as! NativePictureInPictureContentImpl).stop()
        print("PiP playback command checks: \(checks)")
    }
}
