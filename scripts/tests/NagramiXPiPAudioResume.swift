
enum MediaPlayerSeek { case none, start, timecode(Double) }
final class Renderer {
    var stops = 0
    func stop() { stops += 1 }
}
final class RendererContext { let renderer = Renderer() }
extension Core {
    func resumeAfterInterruption(_ loadedState: MediaPlayerLoadedState) {
        // PRODUCTION_RESUME
    }
}
@main struct AudioResumeTests {
    static func main() {
        let core = Core()
        let loaded = MediaPlayerLoadedState(16.75)
        let renderer = core.audioRenderer!.renderer
        core.state = .paused(loaded)
        core.enableSound = true
        core.audioRendererInterrupted(generation: 1)
        precondition(!loaded.lostAudioSession)
        core.audioRendererInterrupted(generation: 2)
        guard case .paused = core.state else { preconditionFailure("interruption changed user pause") }
        precondition(loaded.lostAudioSession && core.seeks.isEmpty)
        core.resumeAfterInterruption(loaded)
        precondition(core.seeks == [16.75] && renderer.stops == 1 && core.audioRenderer == nil)
        core.audioRendererInterrupted(generation: 2)
        precondition(core.seeks == [16.75] && core.enableSound)
        print("Paused native video reacquires audio at the saved position and ignores stale interruptions")
    }
}
