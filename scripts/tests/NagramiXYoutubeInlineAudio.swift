@main private enum InlineAudioTests {
    static func main() {
        for pip in [false, true] {
            for enabled in [false, true] {
                NagramiXTabSettings.backgroundVideoPlaybackEnabled = enabled
                let web = WebPolicy()
                let player = web.playerNode
                let bridge = player.nagramiXSystemPiP
                bridge.setYouTubePolicy(true, pipEnabled: pip, backgroundEnabled: enabled)
                let owner = UUID()
                web.setNagramiXBackgroundPlayback(id: owner, active: enabled)
                precondition(!web.nagramiXHasManagedAudio)
                web.play()
                web.audioSessionManager.acquire()
                precondition(player.impl.plays == 1)
                if pip { precondition(bridge.begin()) }
                bridge.setApplicationActive(false)
                let token = player.view.calls.last!.0["token"]!
                func media(_ reason: String, _ playing: Bool) {
                    let data: [String: Any] = ["token": token, "kind": "media", "frameKey": "frame",
                        "reason": reason, "area": 16000.0, "ended": false, "playing": playing, "allowed": true]
                    bridge.userContentController(player.controller, didReceive: WKScriptMessage(body: data, frameInfo: WKFrameInfo(1)))
                }
                media("watch", false)
                precondition(bridge.actualMediaPlaying == nil)
                media("playing", true)
                player.nagramiXPublishPlaybackStatus(sample(.playing))
                media("loadedmetadata", false)
                precondition(bridge.actualMediaPlaying == true)
                if pip {
                    // Exercise a confirmed WebKit window as well as ordinary inline playback.
                    let probe = player.view.calls.last { $0.0["command"] as? String == "probe" }!.0
                    var candidate = probe
                    candidate["kind"] = "candidate"
                    candidate["video"] = "1"
                    candidate["frameKey"] = "frame"
                    candidate["playing"] = true
                    candidate["area"] = 16000.0
                    let frame = WKFrameInfo(1)
                    bridge.userContentController(player.controller, didReceive: WKScriptMessage(body: candidate, frameInfo: frame))
                    DispatchQueue.main.run()
                    candidate["kind"] = "state"
                    candidate["active"] = true
                    bridge.userContentController(player.controller, didReceive: WKScriptMessage(body: candidate, frameInfo: frame))
                    precondition(bridge.isActive)
                }
                NotificationCenter.default.post(name: UIApplication.didEnterBackgroundNotification, object: nil)
                precondition(web.nagramiXHasManagedAudio == enabled && player.impl.plays == 1)
                if enabled {
                    precondition(player.impl.pauses == 0)
                    media("pause", false)
                    precondition(!web.nagramiXHasManagedAudio && !web.nagramiXPlaybackRequested)
                } else {
                    precondition(player.impl.pauses > 0)
                }
                bridge.stop()
            }
        }
        NagramiXTabSettings.backgroundVideoPlaybackEnabled = true
        let interrupted = WebPolicy()
        interrupted.setNagramiXBackgroundPlayback(id: UUID(), active: true)
        interrupted.play()
        interrupted.audioSessionManager.acquire()
        interrupted.audioSessionManager.interrupt(0)
        precondition(!interrupted.nagramiXHasManagedAudio && interrupted.playerNode.impl.plays == 1)
        let blocked = WebPolicy()
        blocked.setNagramiXBackgroundPlayback(id: UUID(), active: true)
        blocked.play()
        blocked.audioSessionManager.acquire()
        let refused = MediaPlayerStatus(generationTimestamp: 0, duration: 0, dimensions: .zero, timestamp: 0,
            baseRate: 1, seekId: 0, status: .paused, soundEnabled: false)
        blocked.status(refused)
        precondition(!blocked.nagramiXHasManagedAudio && !blocked.nagramiXPendingPlay)
        print("PASS: owned inline and PiP playback across lock, passive metadata, background OFF, real pause and interruption")
    }
}
