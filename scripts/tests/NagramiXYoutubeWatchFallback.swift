@main private enum WatchFallbackTests {
    static func main() {
        let player = YoutubeEmbedImplementation(videoId: "b_uhOUMfp3k")
        let web = WKWebView()
        var pages = 0
        var commands: [(String, Double?, Int)] = []
        var status: MediaPlayerStatus?
        player.openWatchPage = { id, _ in
            precondition(id == "b_uhOUMfp3k")
            pages += 1
        }
        player.sendWatchCommand = { commands.append(($0, $1, $2)) }
        player.setup(web, userContentController: WKUserContentController(), evaluateJavaScript: { _, _ in },
                     updateStatus: { status = $0 }, onPlaybackStarted: {})
        let doc = web.html.components(separatedBy: "window.nagramiXYoutubeDocument = \"")[1].components(separatedBy: "\"")[0]
        func embed(_ query: String) {
            player.callback(url: URL(string: "embed://onState?document=\(doc)&\(query)")!)
        }
        func watch(_ event: String, _ time: Double = 0, revision: Int? = nil) {
            player.watchEvent(event, position: time, duration: 90, revision: revision ?? commands.last?.2 ?? 0)
        }
        // A healthy iframe advances. Pausing and rotating do not select the fallback.
        player.play()
        player.callback(url: URL(string: "embed://onReady?document=\(doc)")!)
        embed("transport=1&playback=1&duration=90&position=0")
        precondition(!player.availability.canPlayInPiP)
        embed("transport=1&playback=1&duration=90&position=1")
        DispatchQueue.main.expire()
        precondition(pages == 0 && player.availability == .playable)
        embed("transport=1&playback=0&duration=90&position=90")
        player.play()
        player.pause()
        DispatchQueue.main.expire()
        precondition(pages == 0)
        // The iframe reports PLAYING but the new playback stays at zero.
        player.play()
        embed("transport=4&playback=1&duration=90&position=0")
        embed("transport=4&playback=1&duration=90&position=0")
        DispatchQueue.main.expire()
        precondition(pages == 1 && player.availability == .watchLoading)
        embed("transport=4&failed=true&errorCode=101")
        precondition(pages == 1 && player.availability == .watchLoading)
        watch("ready")
        precondition(commands.last?.0 == "play" && player.availability == .watchInteractive)
        watch("paused") // transient pause before the first frame
        precondition(player.wantsPlayingPictureInPicture)
        watch("gesture")
        DispatchQueue.main.expire()
        precondition(player.availability == .watchInteractive && status?.soundEnabled == false)
        watch("attempt")
        precondition(player.wantsPlayingPictureInPicture)
        watch("playing")
        watch("playing", 0.4)
        precondition(player.availability.canPlayInPiP && status?.status == .playing)
        player.pause()
        watch("playing", 1, revision: commands.last!.2 - 1)
        precondition(status?.status == .paused)
        player.seek(timestamp: 8)
        precondition(commands.last?.0 == "seek" && commands.last?.1 == 8)
        player.play()
        watch("playing", 8.25)
        watch("ended", 90)
        precondition(!player.wantsPlayingPictureInPicture)
        player.play()
        DispatchQueue.main.expire()
        precondition(player.availability == .unavailable && pages == 1 && status?.soundEnabled == false)
        watch("paused")
        precondition(status?.soundEnabled == false)
        player.play()
        precondition(!player.wantsPlayingPictureInPicture && pages == 1)
        for query in ["failed=true&errorCode=101", "blocked=true"] {
            let failed = YoutubeEmbedImplementation(videoId: "cgvHSmqSvdw")
            let view = WKWebView()
            failed.setup(view, userContentController: WKUserContentController(), evaluateJavaScript: { _, _ in }, updateStatus: { _ in }, onPlaybackStarted: {})
            let id = view.html.components(separatedBy: "window.nagramiXYoutubeDocument = \"")[1].components(separatedBy: "\"")[0]
            failed.callback(url: URL(string: "embed://onState?document=\(id)&transport=0&\(query)")!)
            precondition(!failed.usesWatchPage)
            failed.play()
            precondition(failed.usesWatchPage && failed.availability == .watchLoading)
            if query == "blocked=true" {
                failed.watchEvent("pageError", position: 0, duration: 0, revision: 0)
                precondition(failed.availability == .unavailable)
            }
            DispatchQueue.main.expire()
            precondition(failed.availability == .unavailable)
        }
        for size in [CGSize(width: 320, height: 568), CGSize(width: 393, height: 852), CGSize(width: 568, height: 320)] {
            let zone = CGRect(x: 16, y: 60, width: size.width - 32, height: size.height - 60 - 132)
            let screen = CGRect(origin: .zero, size: size)
            let small = CGSize(width: zone.width, height: 90)
            let expected = zone.contains(CGRect(x: screen.midX - small.width / 2, y: screen.midY - 45, width: small.width, height: 90)) ? screen : zone
            precondition(Feedback.nagramiXWatchViewport(screen: screen, safe: zone, mediaSize: small) == expected)
            precondition(Feedback.nagramiXWatchViewport(screen: screen, safe: zone, mediaSize: size) == zone)
            for measured in [CGSize(width: 170, height: 42), CGSize(width: 750, height: 112)] {
                let frame = Feedback.nagramiXFeedbackFrame(bounds: zone, videoBottom: size.height * 0.7, measured: measured)!
                precondition(zone.contains(frame) && frame.width >= 44 && frame.height >= 44)
            }
        }
        print("YouTube embed, automatic watch page, gesture, replay, errors and gallery button geometry passed")
    }
}
