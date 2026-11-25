struct VideoFile { let isVideo: Bool }
struct TelegramMediaWebpageLoadedContent {
    let url: String
    var embedUrl: String?
    var file: VideoFile?
    var image: Bool?
}
func extractVimeoVideoIdAndTimestamp(url: String) -> (String, Int)? { nil }
func isTwitchVideoUrl(_ url: String) -> Bool { false }

@main private enum InlinePlaybackTests {
    static func main() {
        let references = [
            ("https://youtu.be/b_uhOUMfp3k?si=X5yNqyfOVXcRAOrR", "b_uhOUMfp3k"),
            ("https://youtu.be/cgvHSmqSvdw?is=Nk3RrEHiJgk84PG5", "cgvHSmqSvdw"),
            ("https://youtube.com/watch?v=ukfI4WLziCM", "ukfI4WLziCM")
        ]
        for (url, id) in references {
            var metadata = TelegramMediaWebpageLoadedContent(url: url)
            guard case let .youtube(routedId, start) = webEmbedType(content: metadata) else {
                preconditionFailure("The gallery did not recognize the reference")
            }
            precondition(routedId == id && start == 0)
            precondition(select(metadata) == "embed")
            metadata.file = VideoFile(isVideo: true)
            precondition(select(metadata) == "native")
            metadata.embedUrl = "https://example.org/video.mp4"
            metadata.image = true
            precondition(select(metadata) == "native")
            metadata.file = nil
            precondition(select(metadata) == "system")
            let parsed = extractYoutubeVideoIdAndTimestamp(url: url)
            precondition(parsed?.0 == id && parsed?.1 == 0)
            let controller = YoutubeEmbedImplementation(videoId: id)
            let page = WKWebView()
            var commands: [String] = []
            var state: MediaPlayerStatus?
            var revealed = false
            controller.setup(page, userContentController: WKUserContentController(),
                evaluateJavaScript: { command, _ in commands.append(command) },
                updateStatus: { state = $0 }, onPlaybackStarted: { revealed = true })
            precondition(page.html.contains(id))
            func snapshot(_ query: String) {
                controller.callback(url: URL(string: "embed://onState?duration=0&" + query)!)
            }
            controller.seek(timestamp: 7)
            controller.setBaseRate(1.25)
            precondition(commands.isEmpty)
            controller.play()
            controller.pause()
            snapshot("ready=false&playback=-1")
            precondition(state?.status == .paused)
            controller.play()
            snapshot("ready=true&playback=-1")
            controller.callback(url: URL(string: "embed://onReady")!)
            precondition(commands.filter { $0 == "seek(7.0);" }.count == 1)
            precondition(commands.filter { $0 == "setRate(1.25);" }.count == 1)
            precondition(revealed && commands.filter { $0 == "play();" }.count == 1)
            snapshot("ready=true&blocked=true&playback=-1")
            precondition(state?.status == .paused && state?.soundEnabled == false)
            controller.play()
            snapshot("ready=true&playback=1&position=42")
            precondition(state?.status == .playing)
            snapshot("ready=true&failed=true&errorCode=150&playback=1")
            precondition(state?.status == .paused && state?.soundEnabled == false)
            controller.callback(url: URL(string: "embed://onReady")!)
            precondition(commands.filter { $0 == "play();" }.count == 2)
        }
        let late = YoutubeEmbedImplementation(videoId: "ukfI4WLziCM")
        var plays = 0
        late.setup(WKWebView(), userContentController: WKUserContentController(),
            evaluateJavaScript: { command, _ in if command == "play();" { plays += 1 } },
            updateStatus: { _ in }, onPlaybackStarted: {})
        late.play()
        late.callback(url: URL(string: "embed://onState?ready=true&blocked=true&playback=-1&duration=0")!)
        precondition(plays == 0)
        late.play()
        precondition(plays == 1)
        print("PASS: all three URLs, queued Play, pause, repeated readiness, blocked autoplay and provider error")
    }
}
