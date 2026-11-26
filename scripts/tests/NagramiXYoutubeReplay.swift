@main private enum ReplayTests {
    static func main() {
        let player = YoutubeEmbedImplementation(videoId: "b_uhOUMfp3k")
        let web = WKWebView()
        var commands: [String] = []
        var status: MediaPlayerStatus?
        var starts = 0
        player.setup(web, userContentController: WKUserContentController(),
                     evaluateJavaScript: { script, _ in commands.append(script) },
                     updateStatus: { status = $0 }, onPlaybackStarted: { starts += 1 })
        func document() -> String {
            web.html.components(separatedBy: "window.nagramiXYoutubeDocument = \"")[1].components(separatedBy: "\"")[0]
        }
        let original = document()
        func state(_ revision: Int, _ playback: Int, position: Int = 90) {
            let query = "document=\(original)&transport=\(revision)&ready=true&duration=90&position=\(position)&playback=\(playback)"
            player.callback(url: URL(string: "embed://onState?\(query)")!)
        }
        func checkWaiting() {
            guard case .buffering(_, true, _, _)? = status?.status else {
                preconditionFailure("Replay lost its pending Play")
            }
            precondition(player.availability == .loading && player.wantsPlayingPictureInPicture)
        }
        player.play()
        player.callback(url: URL(string: "embed://onReady?document=\(original)")!)
        state(1, 1, position: 0)
        state(1, 0)
        precondition(status?.status == .paused && status?.timestamp == 0 && starts == 1)

        player.play()
        state(1, 0)
        state(2, 0)
        state(2, 3)
        state(2, 0)
        checkWaiting()
        state(2, 1, position: 0)
        DispatchQueue.main.expire()
        precondition(starts == 2 && status?.status == .playing && player.availability == .playable)
        precondition(commands.count == 2)

        // Even with an extra Play on an already playing clip, its genuine end still wins.
        player.play()
        state(3, 0)
        precondition(status?.timestamp == 0 && status?.status == .paused && !player.wantsPlayingPictureInPicture)
        player.play()
        state(4, 0)
        player.pause()
        state(4, 1)
        state(5, 0)
        precondition(status?.status == .paused)
        DispatchQueue.main.expire()
        precondition(!player.wantsPlayingPictureInPicture && player.availability == .loading && starts == 2)

        player.play()
        state(6, 0)
        checkWaiting()
        DispatchQueue.main.expire()
        for value in [0, 2, 3, -1, 0] {
            state(6, value)
            precondition(player.availability == .unavailable && status?.soundEnabled == false)
            precondition(status?.timestamp == 0 && !player.wantsPlayingPictureInPicture)
        }
        // A confirmed Pause during the timeout must still allow a subsequent
        // manual start from the iframe on this same document.
        player.pause()
        state(7, 2)
        precondition(player.availability == .unavailable && status?.timestamp == 0)
        state(7, 1, position: 0)
        precondition(starts == 3 && player.availability == .playable)

        state(7, 0)
        player.play()
        state(8, 0)
        DispatchQueue.main.expire()
        state(8, 0)
        player.retryDocument()
        let retry = document()
        precondition(retry != original)
        state(8, 1)
        precondition(starts == 3 && player.availability == .loading)
        let count = commands.count
        player.play()
        player.callback(url: URL(string: "embed://onReady?document=\(retry)")!)
        precondition(commands.count == count + 1 && commands.last!.contains("play(1)"))
        print("PASS: replay, repeated ENDED, real completion, explicit pause, timeout, late recovery and manual retry")
    }
}
