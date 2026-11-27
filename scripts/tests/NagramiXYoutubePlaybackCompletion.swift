@main private enum YoutubeCompletionTests {
    static func main() {
        let player = YoutubeEmbedImplementation(videoId: "b_uhOUMfp3k")
        let web = WKWebView()
        var ends = 0
        player.onPlaybackCompleted = { ends += 1 }
        player.setup(web, userContentController: WKUserContentController(), evaluateJavaScript: { _, _ in },
                     updateStatus: { _ in }, onPlaybackStarted: {})
        let document = web.html.components(separatedBy: "window.nagramiXYoutubeDocument = \"")[1].components(separatedBy: "\"")[0]
        func state(_ playback: Int, _ revision: Int = 1, position: Int = 90) {
            player.callback(url: URL(string: "embed://onState?document=\(document)&transport=\(revision)&ready=true&duration=90&position=\(position)&playback=\(playback)")!)
        }
        player.play()
        player.callback(url: URL(string: "embed://onReady?document=\(document)")!)
        state(0)
        precondition(ends == 0)
        state(1, position: 1)
        state(1, position: 2)
        state(2)
        precondition(ends == 0)
        state(0)
        state(0)
        precondition(ends == 1)

        let watch = YoutubeEmbedImplementation(videoId: "b_uhOUMfp3k")
        let watchWeb = WKWebView()
        var commands: [Int] = []
        var watchEnds = 0
        watch.openWatchPage = { _, _ in }
        watch.sendWatchCommand = { _, _, revision in commands.append(revision) }
        watch.onPlaybackCompleted = { watchEnds += 1 }
        watch.setup(watchWeb, userContentController: WKUserContentController(), evaluateJavaScript: { _, _ in },
                    updateStatus: { _ in }, onPlaybackStarted: {})
        watch.play()
        watch.startupFailed()
        watch.watchEvent("ready", position: 0, duration: 90, revision: 0, canUsePiP: true)
        func event(_ value: String, _ position: Double, revision: Int? = nil) {
            watch.watchEvent(value, position: position, duration: 90, revision: revision ?? commands.last!, canUsePiP: true)
        }
        event("playing", 1)
        event("playing", 2)
        event("paused", 20)
        precondition(watchEnds == 0)
        event("ended", 90, revision: commands.last! + 1)
        precondition(watchEnds == 0)
        event("ended", 90)
        event("ended", 90)
        precondition(watchEnds == 1)
        watch.play()
        event("playing", 1)
        event("playing", 2)
        event("ended", 90)
        precondition(watchEnds == 2)
        withExtendedLifetime((web, watchWeb)) {}
        print("YouTube iframe and watch completion, pause, stale events and repeated end passed")
    }
}
