final class PlaybackDelegate { var retiringForReplacement = false }
typealias WindowHost = Window
extension ViewController {
    var nagramiXPiPGalleryNode: ResetNode? { (self as? GalleryController)?.galleryNode }
}
extension ResetNode {
    var dismiss: (() -> Void)? { nil }
    func nagramiXPrepareNativePiPBackdrop() -> Bool { true }
    func nagramiXShowNativePiPBackdrop() {}
    func nagramiXFinishNativePiPBackdrop(owner: GalleryItemNode?, animated: Bool) {}
    func nagramiXPrepareNativePiPRestore() {}
    func updateDismissAppearance(distanceFromEquilibrium: CGFloat) {}
}
extension GalleryLifecycleBoundary {
    var waitsForEmbeddedPictureInPicture: Bool { self.item?.embedded == true }
    var native: NativePictureInPictureContentImpl? { self.nativePictureInPictureContent as? NativePictureInPictureContentImpl }
    var stopCount: Int { self.item!.embedded ? self.videoNode!.stops : (self.native?.stops ?? 0) }
    func acknowledgeClose() {
        if self.item!.embedded { self.videoNode!.isNativePictureInPictureActive.set(false) }
        else { self.native!.confirmStop() }
    }
    func anotherVideo(embedded: Bool) -> GalleryLifecycleBoundary {
        let other = GalleryLifecycleBoundary()
        other.context = self.context
        other.item!.embedded = embedded
        return other
    }
}

@main struct ReplacementTests {
    static func main() {
        for firstWeb in [false, true] {
            for secondWeb in [false, true] {
                let first = GalleryLifecycleBoundary()
                first.item!.embedded = firstWeb
                first.pictureInPictureButtonPressed()
                finish(first)
                advance(0.3)
                let next = first.anotherVideo(embedded: secondWeb)
                let originalPlayer = next.videoNode!
                check(next.nagramiXRequestPictureInPicture(), "second request accepted")
                next.pictureInPictureButtonPressed()
                advance(0.5)
                check(first.stopCount == 1 && next.nagramiXPiPVisualState.phase == .waiting, "request stops first once and waits for confirmation")
                let oldController = first.native
                first.expandPIP()
                check(first.navigation!.currentWindow!.presents == 0, "retiring window cannot reopen its gallery")
                first.acknowledgeClose()
                advance(0.1)
                finish(next)
                oldController?.confirmStop()
                if let oldController {
                    var restored: Bool?
                    oldController.expand { restored = $0 }
                    check(restored == false, "late restore from old native session rejected")
                } else {
                    first.videoNode!.isNativePictureInPictureActive.set(true)
                    first.videoNode!.isNativePictureInPictureActive.set(false)
                }
                advance(0.3)
                check(next.nagramiXPiPVisualState.phase == .active && next.videoNode === originalPlayer, "same second player owns PiP")
                check(next.context.sharedContext.mediaManager.currentPictureInPictureNode === next && originalPlayer.pauses == 0, "late callbacks leave new playback alone")
                next.acknowledgeClose()
            }
            let first = GalleryLifecycleBoundary()
            first.item!.embedded = firstWeb
            first.pictureInPictureButtonPressed()
            finish(first)
            let middle = first.anotherVideo(embedded: !firstWeb)
            let last = first.anotherVideo(embedded: firstWeb)
            middle.pictureInPictureButtonPressed()
            last.pictureInPictureButtonPressed()
            advance(0.1)
            check(middle.nagramiXPiPVisualState.phase == .idle && middle.nagramiXPiPEntryTimer == nil, "superseded request unlocked")
            check(first.stopCount == 1, "rapid replacement issues one stop")
            first.acknowledgeClose()
            advance(0.1)
            finish(last)
            check(last.nagramiXPiPVisualState.phase == .active && middle.videoNode!.enters == 0, "last request wins")
            last.acknowledgeClose()

            let starting = GalleryLifecycleBoundary()
            starting.item!.embedded = firstWeb
            starting.pictureInPictureButtonPressed()
            let next = starting.anotherVideo(embedded: !firstWeb)
            next.pictureInPictureButtonPressed()
            finish(starting)
            check(starting.stopCount == 1 && starting.detached == 0, "superseded start stops on confirmation")
            advance(5.1)
            check(next.nagramiXPiPVisualState.phase == .idle, "missing stop of superseded start unlocks second gallery")
            next.pictureInPictureButtonPressed()
            check(starting.stopCount == 2, "confirmed start can retry stop after supersession")
            starting.acknowledgeClose()
            advance(0.1)
            finish(next)
            check(next.nagramiXPiPVisualState.phase == .active, "replacement after pending start")
            next.acknowledgeClose()
        }

        let first = GalleryLifecycleBoundary()
        first.pictureInPictureButtonPressed()
        finish(first)
        let second = first.anotherVideo(embedded: true)
        second.pictureInPictureButtonPressed()
        advance(5.1)
        check(second.nagramiXPiPVisualState.phase == .idle && second.controller!.view.alpha == 1, "missing stop leaves second inline")
        second.pictureInPictureButtonPressed()
        check(first.stopCount == 2, "user can retry after timeout")
        second.isCentral = false
        advance(0.1)
        first.acknowledgeClose()
        advance(0.1)
        check(second.videoNode!.enters == 0 && second.nagramiXPiPEntryTimer == nil, "paged-away request never opens")
        for web in [false, true] {
            let old = GalleryLifecycleBoundary()
            old.pictureInPictureButtonPressed()
            finish(old)
            let target = old.anotherVideo(embedded: web)
            target.pictureInPictureButtonPressed()
            old.acknowledgeClose()
            advance(0.1)
            if web { advance(8.1) } else { target.native!.fail() }
            check(target.controller!.view.alpha == 1 && target.controller!.view.window != nil, "failed start keeps inline video visible")
            check(target.nagramiXPiPVisualState.phase == .idle && target.context.sharedContext.mediaManager.currentPictureInPictureNode == nil, "failed start releases PiP and gesture")
            target.pictureInPictureButtonPressed()
            finish(target)
            advance(0.3)
            target.expandPIP()
            advance(0.2)
            check(target.navigation!.currentWindow!.presents == 1 && old.navigation!.currentWindow!.presents == 0, "normal return restores the new player only")
            target.acknowledgeClose()
            advance(0.1)
        }
        print("PiP replacement passed", checks, "checks")
    }
}
