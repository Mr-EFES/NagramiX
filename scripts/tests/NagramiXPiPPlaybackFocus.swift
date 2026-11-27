// Controlled playback and status delivery around the production gallery transition.
enum MediaPlayerSeek: Equatable { case start, none, timecode(Double) }
enum FocusStatus { case paused, buffering, playing }
struct MediaPlayerStatus {
    let status: FocusStatus
    var soundEnabled = true
}
enum Availability { case loading, playable, unavailable }

class FocusVideoContent { let id = UUID() }
final class NativeVideoContent: FocusVideoContent {}
final class HLSVideoContent: FocusVideoContent {}
final class WebEmbedVideoContent: FocusVideoContent {}

final class PreparedSource: NagramiXGalleryPlaybackPreparation {
    var completion: (() -> Bool)?
    func nagramiXPrepareGalleryPlayback(_ ready: @escaping () -> Bool) { completion = ready }
}
final class FocusContentManager {
    var nodes: [UUID: PreparedSource] = [:]
    func withUniversalVideoContent(id: UUID, _ body: (AnyObject?) -> Void) { body(nodes[id]) }
}
final class SystemVideoContent: FocusVideoContent {}
final class PlatformVideoContent: FocusVideoContent {}

extension GalleryLifecycleBoundary {
    func deliver(_ status: FocusStatus, sound: Bool = true) {
        let update = MediaPlayerStatus(status: status, soundEnabled: sound)
        playerStatusValue = update
        nagramiXObservePlayback(update, node: videoNode!)
    }
}

func checkPlaybackFocus() {
    let first = GalleryLifecycleBoundary()
    first.pictureInPictureButtonPressed()
    finish(first)
    let floating = first.videoNode!
    let control = first.native!.contentDelegate!
    func pressPlay() { control.pictureInPictureController(control.pictureInPictureController, setPlaying: true) }
    control.pictureInPictureController(AVPictureInPictureController(), setPlaying: true)
    check(floating.soundPlays == 0, "unrelated controller is ignored")
    floating.position = 42
    pressPlay()
    check(floating.plays == 1 && floating.soundPlays == 0, "ordinary PiP Play preserves its existing sound setting")
    let next = first.anotherVideo(embedded: false)
    let foreground = next.videoNode!
    for round in 0..<3 {
        let baseline = floating.pauses
        let offset = 12.0 + Double(round)
        check(next.nagramiXStartAlongsidePiP(foreground, seek: .timecode(offset)), "prepare foreground")
        next.deliver(.buffering, sound: false)
        next.deliver(.playing) // Previous audible status was already on the main queue.
        check(floating.pauses == baseline, "buffering or stale status leaves PiP playing")
        next.deliver(.playing, sound: false)
        check(floating.pauses == baseline + 1 && foreground.audible && foreground.position == offset, "first frame transfers audio at current position")
        next.deliver(.playing)
        check(floating.pauses == baseline + 1, "duplicate status is inert")
        floating.ownsContentNode = false // The source gallery is no longer in the window.
        let foregroundPauses = foreground.pauses
        pressPlay()
        check(foreground.pauses == foregroundPauses + 1 && floating.audible && floating.position == 42, "system Play resumes original video and sound")
        next.deliver(.playing)
        check(floating.pauses == baseline + 1, "queued foreground frame cannot take back audio")
        next.deliver(.paused)
    }
    floating.ownsContentNode = true
    let source = PreparedSource()
    let web = first.anotherVideo(embedded: true)
    web.item!.content = WebEmbedVideoContent()
    web.context.sharedContext.mediaManager.universalVideoManager.nodes[web.item!.content.id] = source
    let baseline = floating.pauses
    check(web.nagramiXStartAlongsidePiP(web.videoNode!, seek: .none), "embed preparation registered")
    pressPlay()
    check(source.completion?() == false && floating.pauses == baseline, "superseded preparation cannot steal audio")
    check(web.nagramiXStartAlongsidePiP(web.videoNode!, seek: .none) && source.completion?() == true, "playable provider transfers audio")
    check(floating.pauses == baseline + 1, "confirmed readiness pauses prior player")
    web.nagramiXYoutubeId = "test"
    web.nagramiXYoutubeAvailability = .loading
    web.deliver(.buffering)
    web.pictureInPictureButtonPressed()
    advance(0.1)
    check(first.stopCount == 0, "no window closure during loading")
    web.nagramiXYoutubeAvailability = .playable
    web.deliver(.playing)
    pressPlay()
    web.deliver(.paused)
    advance(0.1)
    check(first.stopCount == 1 && web.videoNode!.enters == 0, "wait for old system stop")
    let oldPlayCount = floating.soundPlays
    pressPlay()
    check(floating.soundPlays == oldPlayCount, "retiring controller cannot acquire audio")
    first.acknowledgeClose()
    advance(0.1)
    finish(web)
    check(web.videoNode!.plays == 1 && web.context.sharedContext.mediaManager.currentPictureInPictureNode === web, "paused replacement starts after handoff")
    control.retiringForReplacement = false
    pressPlay()
    check(floating.soundPlays == oldPlayCount, "late command from closed controller is ignored")
    let third = web.anotherVideo(embedded: false)
    check(third.nagramiXStartAlongsidePiP(third.videoNode!, seek: .none), "native video can start alongside web PiP")
    third.deliver(.playing, sound: false)
    web.deliver(.paused)
    let pauses = third.videoNode!.pauses
    web.deliver(.playing)
    check(third.videoNode!.pauses == pauses + 1, "provider system Play takes sound back")
    web.acknowledgeClose()

    let active = GalleryLifecycleBoundary()
    active.pictureInPictureButtonPressed()
    finish(active)
    let fresh = active.anotherVideo(embedded: false)
    fresh.deliver(.paused)
    fresh.pictureInPictureButtonPressed()
    advance(0.1)
    check(fresh.videoNode!.plays == 1 && active.stopCount == 0, "first PiP tap prepares a fresh paused source once")
    fresh.deliver(.playing, sound: false)
    advance(0.1)
    check(active.stopCount == 1, "prepared source is eligible for replacement")
    active.acknowledgeClose()
    advance(0.1)
    finish(fresh)
    fresh.acknowledgeClose()
}
