@main private enum ReadinessTests {
    static func main() {
        let player = YoutubeEmbedImplementation(videoId: "b_uhOUMfp3k")
        let web = WKWebView()
        var commands: [String] = []
        var status: MediaPlayerStatus?
        var starts = 0
        var reveals = 0
        player.pageVisible = { reveals += 1 }
        player.setup(web, userContentController: WKUserContentController(),
                     evaluateJavaScript: { script, _ in commands.append(script) },
                     updateStatus: { status = $0 }, onPlaybackStarted: { starts += 1 })
        func document() -> String {
            web.html.components(separatedBy: "window.nagramiXYoutubeDocument = \"")[1].components(separatedBy: "\"")[0]
        }
        func state(_ doc: String, _ revision: Int, _ playback: Int, _ extra: String = "") {
            player.callback(url: URL(string: "embed://onState?document=\(doc)&transport=\(revision)&ready=true&duration=90&position=6&playback=\(playback)\(extra)")!)
        }
        let first = document()
        player.play()
        player.pause()
        player.callback(url: URL(string: "embed://onReady?document=\(first)")!)
        precondition(reveals == 1 && starts == 0 && player.availability == .loading && commands.isEmpty)
        player.play()
        state(first, 1, 2)
        precondition(player.wantsPlayingPictureInPicture && player.availability == .loading)
        state(first, 1, 1)
        precondition(starts == 1 && player.availability == .playable && status?.status == .playing)
        player.pause()
        state(first, 1, 1)
        state(first, 2, 1)
        precondition(!player.wantsPlayingPictureInPicture && status?.status == .paused)
        state(first, 2, 2)
        precondition(player.availability == .playable)
        state(first, 2, 2, "&failed=true&errorCode=150")
        precondition(player.availability == .unavailable && starts == 1 && status?.soundEnabled == false)
        player.retryDocument()
        let second = document()
        precondition(first != second && player.availability == .loading)
        state(first, 2, 1)
        precondition(starts == 1 && player.availability == .loading)
        player.play()
        player.callback(url: URL(string: "embed://onReady?document=\(second)")!)
        precondition(commands.last!.contains(second) && commands.last!.contains("play(1)"))
        state(second, 1, -1, "&blocked=true")
        precondition(player.availability == .unavailable && !player.wantsPlayingPictureInPicture)
        player.retryDocument()
        let third = document()
        player.play()
        DispatchQueue.main.expire()
        precondition(player.availability == .unavailable && status?.soundEnabled == false)
        state(third, 0, 1)
        precondition(starts == 2 && player.availability == .playable)
        player.webProcessEnded()
        state(third, 0, 1)
        precondition(player.availability == .unavailable && !player.wantsPlayingPictureInPicture)
        player.retryDocument()
        player.play()
        player.pause()
        DispatchQueue.main.expire()
        precondition(player.availability == .loading && !player.wantsPlayingPictureInPicture)
        print("PASS: iframe readiness, playback, late commands, manual pause, provider refusal, timeout, retry and process termination")
    }
}
