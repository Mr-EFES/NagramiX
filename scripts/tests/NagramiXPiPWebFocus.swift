func checkDeferredWebAudio() {
    for youtube in [false, true] {
        let web = WebPolicy(youtube: youtube)
        let provider = web.playerNode.impl as? YoutubeEmbedImplementation
        provider?.availability = .loading
        var transfers = 0
        web.nagramiXPrepareGalleryPlayback { transfers += 1; return true }
        web.setNagramiXBackgroundPlayback(id: UUID(), active: true)
        web.status(sample(.buffering(initial: true, whilePlaying: true, progress: 0, display: true)))
        precondition(transfers == 0 && !web.nagramiXHasManagedAudio)
        if let provider {
            web.status(sample(.playing))
            precondition(transfers == 0 && !web.nagramiXHasManagedAudio)
            provider.availability = .playable
        }
        web.status(sample(.playing))
        web.status(sample(.playing))
        precondition(transfers == 1 && web.nagramiXHasManagedAudio)
        web.pause()
        let cancelled = WebPolicy(youtube: youtube)
        cancelled.nagramiXPrepareGalleryPlayback { false }
        cancelled.status(sample(.playing))
        precondition(!cancelled.nagramiXHasManagedAudio && !cancelled.nagramiXPlaybackRequested)
        cancelled.nagramiXPrepareGalleryPlayback { preconditionFailure("cancelled request") }
        cancelled.pause()
        precondition(cancelled.nagramiXPreparedGalleryPlay == nil)
    }
}
