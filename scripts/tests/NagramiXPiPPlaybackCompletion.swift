func checkResumptionAndCompletion() {
    let first = GalleryLifecycleBoundary()
    first.pictureInPictureButtonPressed()
    finish(first)
    let other = first.anotherVideo(embedded: false)
    check(other.nagramiXStartAlongsidePiP(other.videoNode!, seek: .none), "second video prepares")
    other.deliver(.playing, sound: false)
    let node = first.videoNode!
    check(first.nagramiXAwaitingPause, "competing video pauses the first")
    first.deliver(.paused)
    first.isPaused = true
    first.installControls()
    let pauses = node.pauses
    first.footerContentNode.playbackControl?()
    first.deliver(.playing)
    check(node.pauses == pauses && !first.nagramiXAwaitingPause,
          "fullscreen Play after a competing video resumes the first")
    let otherPauses = other.videoNode!.pauses
    other.isPaused = true
    other.installControls()
    other.footerContentNode.playbackControl?()
    other.deliver(.playing, sound: false)
    check(other.videoNode!.pauses == otherPauses && first.nagramiXAwaitingPause,
          "foreground Play can take playback back")
    let control = first.native!.contentDelegate!
    control.pictureInPictureController(control.pictureInPictureController, setPlaying: true)
    first.deliver(.playing)
    check(!first.nagramiXAwaitingPause && node.audible, "PiP Play resumes after switching back again")
    first.acknowledgeClose()

    for embedded in [false, true] {
        let video = GalleryLifecycleBoundary()
        video.item!.embedded = embedded
        var dismisses = 0
        video.controller!.galleryNode.onDismiss = { dismisses += 1 }
        video.nagramiXFinishPlayback(video.videoNode!)
        video.nagramiXFinishPlayback(video.videoNode!)
        check(dismisses == 1 && video.videoNode!.pauses == 1, "natural completion closes the fullscreen once")
        check(video.nagramiXPlaybackFinished, "finished video rejects queued Play")
        let starts = video.videoNode!.plays + video.videoNode!.soundPlays
        video.nagramiXResumePlayback(video.videoNode!)
        check(video.videoNode!.plays + video.videoNode!.soundPlays == starts, "finished player cannot restart while closing")

        let pip = GalleryLifecycleBoundary()
        pip.item!.embedded = embedded
        pip.pictureInPictureButtonPressed()
        finish(pip)
        let next = pip.anotherVideo(embedded: false)
        var nextDismisses = 0
        next.controller!.galleryNode.onDismiss = { nextDismisses += 1 }
        pip.nagramiXFinishPlayback(pip.videoNode!)
        pip.nagramiXFinishPlayback(pip.videoNode!)
        check(pip.stopCount == 1 && nextDismisses == 0, "only the completed PiP closes")
        check(pip.context.sharedContext.mediaManager.currentPictureInPictureNode === pip,
              "keep the PiP owner until the system confirms stop")
        next.pictureInPictureButtonPressed()
        next.nagramiXAbortPiPEntry()
        check(pip.nagramiXRetiringPiP, "a cancelled replacement cannot restore a finished video")
        pip.acknowledgeClose()
        check(pip.context.sharedContext.mediaManager.currentPictureInPictureNode == nil, "system stop releases finished PiP")
    }
    let recycled = GalleryLifecycleBoundary()
    let old = recycled.videoNode!
    recycled.videoNode = UniversalVideoNode()
    recycled.nagramiXFinishPlayback(old)
    check(!recycled.nagramiXPlaybackFinished && recycled.videoNode!.pauses == 0, "old node completion leaves its replacement alone")
    let offscreen = GalleryLifecycleBoundary()
    offscreen.isCentral = false
    offscreen.nagramiXFinishPlayback(offscreen.videoNode!)
    check(!offscreen.nagramiXPlaybackFinished, "offscreen playback cannot close the current gallery")
}
