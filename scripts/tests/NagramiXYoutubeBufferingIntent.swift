func checkYouTubeBufferingIntent() {
    NagramiXTabSettings.backgroundVideoPlaybackEnabled = true
    let web = WebPolicy()
    web.setNagramiXBackgroundPlayback(id: UUID(), active: true)
    web.play()
    web.audioSessionManager.acquire()
    web.status(sample(.playing))
    let plays = web.playerNode.impl.plays
    web.status(sample(.buffering(initial: false, whilePlaying: false, progress: 0, display: false)))
    precondition(web.nagramiXPlaybackRequested && web.nagramiXHasManagedAudio)
    NotificationCenter.default.post(name: UIApplication.didEnterBackgroundNotification, object: nil)
    precondition(web.nagramiXHasManagedAudio && web.playerNode.impl.plays == plays)
    web.pause()
    precondition(!web.nagramiXPlaybackRequested && !web.nagramiXHasManagedAudio)
}
