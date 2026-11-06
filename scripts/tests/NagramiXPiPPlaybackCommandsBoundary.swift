// AVKit, content lookup and the decoder are explicit boundaries. The complete
// production playback delegate and UniversalVideoNode command methods run.
struct PlaybackCommandIdentity { let id = 42 }
final class PlaybackCommandContent {
    let status: Signal<MediaPlayerStatus?, NoError>
    var playing = true
    var commands: [String] = []
    var publishImmediately = true
    var timestamp = 30.0
    init(status: Signal<MediaPlayerStatus?, NoError>) { self.status = status }
    func publish() {
        status.emit(MediaPlayerStatus(status: playing ? .playing : .paused, duration: 100, timestamp: timestamp))
    }
    func play() {
        commands.append("play")
        playing = true
        if publishImmediately { publish() }
    }
    func pause() {
        commands.append("pause")
        playing = false
        if publishImmediately { publish() }
    }
    func togglePlayPause() {
        commands.append("toggle")
        playing.toggle()
        if publishImmediately { publish() }
    }
}
final class PlaybackCommandManager {
    let node: PlaybackCommandContent
    var requestedIds: [Int] = []
    init(status: Signal<MediaPlayerStatus?, NoError>) { node = PlaybackCommandContent(status: status) }
    func withUniversalVideoContent(id: Int, _ body: (PlaybackCommandContent?) -> Void) {
        requestedIds.append(id)
        body(node)
    }
}
