@main private enum WatchPlaybackTests {
    static func main() {
        let player = YoutubeEmbedImplementation(videoId: "b_uhOUMfp3k")
        let web = WKWebView()
        var commands: [(String, Double?, Int)] = []
        var pages = 0
        var status: MediaPlayerStatus?
        player.openWatchPage = { _, _ in pages += 1 }
        player.sendWatchCommand = { commands.append(($0, $1, $2)) }
        player.setup(web, userContentController: WKUserContentController(), evaluateJavaScript: { _, _ in },
                     updateStatus: { status = $0 }, onPlaybackStarted: {})
        player.play()
        player.startupFailed()
        func watch(_ event: String, _ time: Double = 0, pip: Bool = true, revision: Int? = nil) {
            player.watchEvent(event, position: time, duration: 90, revision: revision ?? commands.last?.2 ?? 0, canUsePiP: pip)
        }
        watch("ready")
        watch("playing")
        watch("paused")
        DispatchQueue.main.expire()
        precondition(pages == 1 && player.availability == .watchInteractive && !player.wantsPlayingPictureInPicture)
        precondition(status?.status == .paused && status?.soundEnabled == false)
        player.play()
        watch("playing", 0, pip: false)
        watch("playing", 2, pip: false)
        precondition(player.availability.hasPlayableVideo && !player.availability.canPlayInPiP)
        watch("capability", 2)
        precondition(player.availability.canPlayInPiP)
        watch("paused", 2)
        let seekId = status!.seekId
        player.seek(timestamp: 40)
        precondition(commands.last?.0 == "seek" && commands.last?.1 == 40)
        precondition(status?.timestamp == 40 && status?.seekId == seekId + 1 && status?.status == .paused)
        watch("seeked", 39, revision: commands.last!.2 - 1)
        precondition(status?.timestamp == 40)
        watch("seeked", 39.9)
        precondition(status?.timestamp == 39.9 && status?.status == .paused)
        watch("detached")
        precondition(!player.availability.canPlayInPiP)
        player.seek(timestamp: 18)
        watch("failed")
        watch("ready")
        precondition(commands.suffix(2).map { $0.0 } == ["seek", "pause"] && commands.dropLast().last?.1 == 18)
        watch("playing", 18, revision: commands.last!.2 - 1)
        precondition(!player.wantsPlayingPictureInPicture)
        player.play()
        watch("playing", 18)
        watch("playing", 18.2)
        precondition(player.availability.canPlayInPiP && status?.status == .playing)
        watch("detached")
        DispatchQueue.main.expire()
        precondition(player.availability == .unavailable)
        watch("ready")
        precondition(player.availability == .unavailable)
        print("Watch playback, capability changes, pause, seeking, media replacement and genuine startup timeout passed")
    }
}
