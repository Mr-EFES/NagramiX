@main private enum WatchContinuityTests {
    static func main() {
        let player = YoutubeEmbedImplementation(videoId: "b_uhOUMfp3k")
        let web = WKWebView()
        var commands: [(action: String, value: Double?, revision: Int)] = []
        var status: MediaPlayerStatus?
        player.openWatchPage = { _, _ in }
        player.sendWatchCommand = { commands.append(($0, $1, $2)) }
        player.setup(web, userContentController: WKUserContentController(), evaluateJavaScript: { _, _ in },
                     updateStatus: { status = $0 }, onPlaybackStarted: {})
        func event(_ name: String, _ time: Double, duration: Double = 90, revision: Int? = nil) {
            player.watchEvent(name, position: time, duration: duration, revision: revision ?? commands.last!.revision, canUsePiP: true)
        }
        func advancePlayback(_ time: Double) {
            event("playing", time)
            event("playing", time + 1)
            precondition(status?.status == .playing)
        }
        player.play()
        player.startupFailed()
        event("ready", 0, revision: 0)
        advancePlayback(24)
        var start = commands.count
        event("ready", 0)
        precondition(commands[start...].map { $0.action } == ["seek", "play"] && commands[start].value == 25)
        advancePlayback(25)
        player.pause()
        start = commands.count
        event("detached", 0)
        event("ready", 0, duration: 0)
        event("metadata", 0)
        precondition(commands[start...].map { $0.action } == ["pause", "seek"] && commands.last!.value == 26)
        event("seeked", 26)
        precondition(status?.timestamp == 26 && status?.status == .paused)
        player.play()
        advancePlayback(26)
        start = commands.count
        event("ready", 0, duration: 12) // A different timeline (e.g. ad).
        precondition(commands[start...].map { $0.action } == ["play"])
        advancePlayback(2)
        event("detached", 0)
        player.seek(timestamp: 4)
        start = commands.count
        event("ready", 0)
        precondition(commands[start].action == "seek" && commands[start].value == 4)
        advancePlayback(4)

        start = commands.count
        event("waiting", 5)
        event("waiting", 5)
        DispatchQueue.main.expire()
        precondition(commands[start...].map { $0.action } == ["recover"])
        event("online", 5)
        event("playing", 5) // A repeated timestamp is not a recovered stream.
        DispatchQueue.main.expire()
        precondition(commands[start...].map { $0.action } == ["recover", "pause"])
        precondition(status?.status == .paused && player.availability == .watchInteractive)
        player.play()
        advancePlayback(5)
        start = commands.count
        event("waiting", 6)
        event("online", 6)
        advancePlayback(7.5)
        DispatchQueue.main.expire()
        precondition(commands[start...].map { $0.action } == ["recover"])
        event("waiting", 8.5)
        player.pause()
        DispatchQueue.main.expire()
        precondition(commands.last!.action == "pause")
        player.play()
        let oldPlay = commands.last!.revision
        player.pause()
        event("gesture", 8.5, revision: oldPlay)
        precondition(status?.status == .paused && player.availability == .watchPlayable)
        player.play()
        let newPlay = commands.last!.revision
        player.setBaseRate(1.5)
        player.seek(timestamp: 9)
        event("gesture", 9, revision: newPlay)
        DispatchQueue.main.expire()
        precondition(player.availability == .watchInteractive && !player.wantsPlayingPictureInPicture && status?.soundEnabled == false)
        print("Watch timeline, paused replacement, bounded stall recovery, cancellation and independent Play intent passed")
    }
}
