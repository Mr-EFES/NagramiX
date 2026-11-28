@main private enum WatchPlayIntentTests {
    static func main() {
        let player = YoutubeEmbedImplementation(videoId: "b_uhOUMfp3k")
        let web = WKWebView()
        let bridge = WatchNativeIntentBridge(player)
        var commands: [(String, Int)] = []
        var intents = 0
        var status: MediaPlayerStatus?
        player.openWatchPage = { _, _ in }
        player.sendWatchCommand = { command, _, revision in commands.append((command, revision)) }
        bridge.nagramiXActualPlaybackRequested = { intents += 1 }
        player.setup(web, userContentController: WKUserContentController(), evaluateJavaScript: { _, _ in }, updateStatus: { status = $0 }, onPlaybackStarted: {})
        player.play(); player.startupFailed()
        player.watchEvent("ready", position: 0, duration: 90, revision: 0, canUsePiP: true)
        for i in 1...12 {
            player.pause()
            let revision = commands.last!.1
            player.watchEvent("attempt", position: Double(i), duration: 90, revision: revision - 1, canUsePiP: true)
            precondition(intents == i - 1)
            player.watchEvent("attempt", position: Double(i), duration: 90, revision: revision, canUsePiP: true)
            precondition(intents == i && player.wantsPlayingPictureInPicture)
            player.watchEvent("playing", position: Double(i), duration: 90, revision: revision, canUsePiP: true)
            player.watchEvent("playing", position: Double(i) + 0.2, duration: 90, revision: revision, canUsePiP: true)
            precondition(status?.status == .playing && player.availability.canPlayInPiP)
        }
        player.watchEvent("detached", position: 0, duration: 0, revision: commands.last!.1, canUsePiP: false)
        player.watchEvent("attempt", position: 0, duration: 90, revision: commands.last!.1, canUsePiP: true)
        precondition(intents == 12)
        withExtendedLifetime(bridge) {}
        print("Native watch Play reaches real controller, rejects stale revisions and detached media: 37 checks passed")
    }
}
