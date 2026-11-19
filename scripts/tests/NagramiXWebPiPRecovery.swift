func exerciseWebRecovery() {
    for link in ["https://youtu.be/ab_-CD12345?t=19", "https://m.youtube.com/shorts/ab_-CD12345?t=19",
                 "https://www.youtube.com/live/ab_-CD12345?t=19", "https://www.youtube-nocookie.com/embed/ab_-CD12345?t=19",
                 "https://music.youtube.com/watch?v=ab_-CD12345&t=19", "https://youtube.com/v/ab_-CD12345?t=19"] {
        let video = extractYoutubeVideoIdAndTimestamp(url: link)
        precondition(video?.0 == "ab_-CD12345" && video?.1 == 19)
    }
    for link in ["https://youtube.com.example.org/watch?v=unrelated", "https://youtube.com/@channel/live",
                 "https://youtube.com/embed/videoseries?list=playlist", "https://youtube.com/shorts/"] {
        precondition(extractYoutubeVideoIdAndTimestamp(url: link) == nil)
    }

    let player = Player()
    let bridge = player.nagramiXSystemPiP
    let frame = WKFrameInfo(2)
    func last(_ command: String) -> [String: Any] {
        player.view.calls.last { $0.0["command"] as? String == command }!.0
    }
    func receive(_ message: [String: Any], kind: String, values: [String: Any]) {
        var body = message.merging(values) { _, right in right }
        body["kind"] = kind
        body["frameKey"] = "2"
        bridge.userContentController(player.controller, didReceive: WKScriptMessage(body: body, frameInfo: frame))
    }
    precondition(bridge.begin())
    let probe = last("probe")
    receive(probe, kind: "candidate", values: ["video": "1", "area": 12.0, "playing": true])
    DispatchQueue.main.run()
    player.view.reply?(.success(false))
    precondition(player.view.calls.last!.0["command"] as? String == "probe")
    receive(probe, kind: "candidate", values: ["video": "2", "area": 24.0, "playing": true])
    DispatchQueue.main.run()
    player.view.reply?(.success(true))
    receive(probe, kind: "state", values: ["active": true])
    DispatchQueue.main.run()
    precondition(player.view.calls.last!.0["command"] as? String == "status")
    let staleCheck = player.view.reply!
    staleCheck(.failure(WKError(code: .javaScriptInvalidFrameTarget)))
    precondition(!bridge.isActive && !bridge.keepsPlaybackActive && bridge.begin())
    staleCheck(.success(false))
    precondition(bridge.keepsPlaybackActive)
    bridge.stop()

    for enabled in [true, false] {
        bridge.setYouTubePolicy(true, pipEnabled: true, backgroundEnabled: enabled)
        bridge.setBackground(false)
        bridge.setPlaybackAllowed(true)
        receive(probe, kind: "media", values: ["playing": true, "ended": false, "allowed": true, "area": 24.0])
        player.nagramiXPublishPlaybackStatus(sample(.paused))
        precondition(player.statusValue.value.status == (enabled ? .playing : .paused))
        bridge.setApplicationActive(false)
        player.nagramiXPublishPlaybackStatus(sample(.paused))
        precondition(player.statusValue.value.status == .paused, "background without a playback owner")
        bridge.setApplicationActive(true)
        bridge.setPlaybackAllowed(false)
        player.nagramiXPublishPlaybackStatus(sample(.playing))
        precondition(player.statusValue.value.status == .paused)
    }
}
