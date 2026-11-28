@main private enum WatchAudioIntentTests {
    static func main() {
        NagramiXTabSettings.backgroundVideoPlaybackEnabled = true
        let first = WebPolicy(), second = WebPolicy()
        first.play(); first.audioSessionManager.acquire()
        first.status(sample(.playing))
        var transfers = 0
        second.nagramiXPrepareGalleryPlayback { transfers += 1; first.pause(); return true }
        second.playerNode.nagramiXActualPlaybackRequested?()
        precondition(transfers == 0 && !second.nagramiXHasManagedAudio)
        second.status(sample(.playing))
        precondition(transfers == 1 && !first.nagramiXPlaybackRequested)
        if !(second.nagramiXHasManagedAudio && second.nagramiXPendingPlay) {
            FileHandle.standardError.write(Data("accepted preroll must wait for the final audio handoff\n".utf8))
            exit(91)
        }
        for _ in 0..<8 { second.status(sample(.playing)) }
        precondition(second.nagramiXPendingPlay && !second.nagramiXAudioReady, "queued playing cannot cancel the pending audio handoff")
        second.status(sample(.paused)) // WebKit pauses while the audio category changes.
        second.audioSessionManager.acquire()
        precondition(second.playerNode.impl.plays == 2 && second.nagramiXPlaybackRequested)
        second.status(sample(.playing))
        for _ in 0..<8 { second.status(sample(.playing)) }
        precondition(second.audioSessionManager.pushes == 1 && second.playerNode.impl.plays == 2)
        second.audioSessionManager.interrupt()
        precondition(second.nagramiXAudioSuspended)
        second.playerNode.nagramiXActualPlaybackRequested?()
        precondition(second.nagramiXPendingPlay && !second.nagramiXAudioSuspended)
        second.audioSessionManager.acquire(1)
        precondition(second.playerNode.impl.plays == 3)
        second.pause()
        second.audioSessionManager.acquire(1)
        precondition(second.playerNode.impl.plays == 3 && !second.nagramiXPlaybackRequested)
        let cancelled = WebPolicy()
        cancelled.nagramiXPrepareGalleryPlayback { false }
        cancelled.status(sample(.playing))
        precondition(!cancelled.nagramiXHasManagedAudio && !cancelled.nagramiXPlaybackRequested)
        NagramiXTabSettings.backgroundVideoPlaybackEnabled = false
        let stopped = WebPolicy()
        stopped.nagramiXInForeground = false
        stopped.playerNode.nagramiXActualPlaybackRequested?()
        precondition(!stopped.nagramiXHasManagedAudio && !stopped.nagramiXPlaybackRequested)
        print("Real managed-audio handoff: preroll, queued status, activation pause, native Play, interruption, cancellation and background OFF passed")
    }
}
