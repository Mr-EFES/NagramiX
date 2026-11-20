final class Logger {
    static let shared = Logger()
    var messages: [String] = []
    func log(_ tag: String, _ message: @autoclosure () -> String) {
        precondition(tag == "YouTubeEmbed")
        messages.append(message())
    }
}

@main struct StartupTests {
    static func main() {
        let controller = YoutubeEmbedImplementation(videoId: "sample")
        let page = WKWebView()
        var states: [MediaPlayerStatus] = []
        controller.setup(page, userContentController: WKUserContentController(),
            evaluateJavaScript: { _, _ in }, updateStatus: { states.append($0) }, onPlaybackStarted: {})
        precondition(page.origin?.absoluteString == "https://com.mr-efes.nagramix")
        func state(_ params: String) {
            controller.callback(url: URL(string: "embed://onState?duration=37.625&" + params)!)
        }
        state("failed=true")
        precondition(states.last?.status == .paused && Logger.shared.messages.isEmpty)
        state("failed=true&errorCode=153")
        state("failed=true&errorCode=153")
        state("failed=true&errorCode=101")
        state("failed=false&playback=1")
        precondition(states.last?.status == .playing && states.last?.duration == 37.625)
        state("failed=true&errorCode=101")
        precondition(states.last?.status == .paused && states.last?.soundEnabled == false)
        precondition(Logger.shared.messages == [153, 101, 101].map { "IFrame player error \($0)" })
        print("PASS: app identity, paused error, diagnostic deduplication and playback recovery")
    }
}
