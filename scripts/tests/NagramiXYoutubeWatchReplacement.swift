final class WatchSource: NagramiXYoutubePlaybackSource {
    let nagramiXYoutubeAvailability = Signal<Availability>(.watchPlayable)
    var replies: [(Bool) -> Void] = []
    func checkWatchPictureInPicture(_ completion: @escaping (Bool) -> Void) {
        replies.append(completion)
    }
}

func checkWatchReplacement() {
    let first = GalleryLifecycleBoundary()
    first.pictureInPictureButtonPressed()
    finish(first)
    let next = first.anotherVideo(embedded: true)
    let source = WatchSource()
    next.nagramiXYoutubeId = "b_uhOUMfp3k"
    next.nagramiXYoutubeAvailability = .watchPlayable
    next.nagramiXYoutubeSource = source
    next.deliver(.playing)
    next.pictureInPictureButtonPressed()
    advance(0.1)
    check(first.stopCount == 0 && source.replies.count == 1, "wait for live watch video before retiring first PiP")
    source.replies.removeFirst()(false)
    check(first.stopCount == 0 && next.nagramiXPiPVisualState.phase == .idle, "unavailable replacement leaves first window")
    next.pictureInPictureButtonPressed()
    let late = source.replies.removeFirst()
    next.nagramiXAbortPiPEntry()
    late(true)
    check(first.stopCount == 0, "superseded check cannot close the window")
    let last = first.anotherVideo(embedded: true)
    last.nagramiXYoutubeId = "cgvHSmqSvdw"
    last.nagramiXYoutubeAvailability = .watchPlayable
    last.nagramiXYoutubeSource = source
    last.deliver(.playing)
    last.pictureInPictureButtonPressed()
    source.replies.removeFirst()(true)
    check(first.stopCount == 1 && !last.nagramiXWebPiPTransitionStarted, "approved replacement waits for system close")
    first.acknowledgeClose()
    advance(0.1)
    check(last.nagramiXWebPiPTransitionStarted, "enter second PiP once previous window closes")
    last.nagramiXAbortPiPEntry()
}
