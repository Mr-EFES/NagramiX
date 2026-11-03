@main enum Tests {
    static var count = 0
    static func check(_ condition: @autoclosure () -> Bool, _ text: String) {
        count += 1
        if !condition() { fatalError("system PiP regression: " + text) }
    }
    static func main() {
        let manager = MediaManager(), context = AccountContext(), node = UniversalVideoNode()
        var began = 0, ended = 0, restored = 0
        var content: NativePictureInPictureContentImpl? = NativePictureInPictureContentImpl(context: context, mediaManager: manager, accountId: 1, hiddenMedia: nil, videoNode: node, canSkip: true, willBegin: { _ in began += 1 }, didBegin: { _ in }, didEnd: { _ in ended += 1 }, expand: { completion in restored += 1; completion() })
        let av = AVPictureInPictureController.instances.last!
        check(av.contentSource?.sampleBufferDisplayLayer === node.layer, "PiP uses the existing video layer")
        content!.updateIsCentral(isCentral: true)
        for _ in 0..<12 {
            av.canStartPictureInPictureAutomaticallyFromInline = false
            av.isPictureInPicturePossible = true
            check(av.canStartPictureInPictureAutomaticallyFromInline, "AVKit readiness restores automatic PiP for current item")
            content!.updateIsCentral(isCentral: false)
            av.canStartPictureInPictureAutomaticallyFromInline = true
            av.isPictureInPicturePossible = true
            check(!av.canStartPictureInPictureAutomaticallyFromInline, "late readiness cannot enable a noncentral video")
            content!.updateIsCentral(isCentral: true)
        }
        av.isPictureInPicturePossible = false
        content!.beginPictureInPicture()
        check(av.starts == 0, "unready controller does not start")
        av.isPictureInPicturePossible = true
        content!.beginPictureInPicture()
        check(av.starts == 1 && began == 1 && node.withoutHierarchy, "native start keeps existing playback alive")
        content!.invalidatePlaybackState()
        check(av.invalidations > 0, "active playback state invalidation")
        var restoredOK = false
        content!.pictureInPictureController(av, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: { restoredOK = $0 })
        check(restored == 1 && restoredOK, "system restore forwards completion")
        content!.requestExpand()
        check(ended == 1 && !node.withoutHierarchy, "expand stops PiP through native stop callback")
        content = nil
        check(av.observers.isEmpty && av.delegate == nil && av.contentSource == nil && !av.canStartPictureInPictureAutomaticallyFromInline, "teardown detaches observer, delegate and video source")
        check(node.status.handlers.isEmpty, "playback delegate subscription released")

        let owner = GalleryHarness()
        owner.videoNode!.ownsContentNode = false
        owner.setupNativePictureInPicture()
        check(owner.nativePictureInPictureContent == nil, "nonowner cannot attach PiP content source")
        owner.videoNode!.ownsContentNode = true; owner.videoNode!.hasLayer = false
        owner.setupNativePictureInPicture()
        check(owner.nativePictureInPictureContent == nil, "missing layer cannot attach PiP")
        owner.videoNode!.hasLayer = true
        owner.updateCentral(true)
        check(owner.nativePictureInPictureContent != nil, "centrality proactively prepares PiP")
        let identity = owner.nativePictureInPictureContent
        let player = AVPictureInPictureController.instances.last!
        owner.setupNativePictureInPicture()
        check(owner.nativePictureInPictureContent === identity, "setup does not replace an existing controller")
        check(player.canStartPictureInPictureAutomaticallyFromInline, "setup synchronizes centrality immediately")
        player.isPictureInPicturePossible = true
        NagramiXTabSettings.videoPiPSwipeEnabled = false
        check(!owner.maybePerformActionForSwipeDismiss() && player.starts == 0, "saved swipe OFF keeps native dismiss")
        NagramiXTabSettings.videoPiPSwipeEnabled = true
        owner.context.currentAppConfiguration.value.data = ["ios_killswitch_disable_swipe_pip": true]
        check(!owner.maybePerformActionForSwipeDismiss(), "server swipe killswitch retained")
        owner.context.currentAppConfiguration.value.data = ["video_swipe_up_to_close": true]
        check(!owner.maybePerformActionForSwipeDismiss(), "server swipe-close policy retained")
        owner.context.currentAppConfiguration.value.data = nil
        check(owner.maybePerformActionForSwipeDismiss() && player.starts == 1 && owner.dismissals == 1, "first prepared swipe enters PiP and dismisses gallery")
        check(owner.context.sharedContext.mediaManager.currentPictureInPictureNode === owner, "gallery owns active PiP")
        check(!owner.maybePerformActionForSwipeDownDismiss(), "downward swipe remains normal close")
        var completed = false
        (owner.nativePictureInPictureContent as! NativePictureInPictureContentImpl).pictureInPictureController(player, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: { completed = $0 })
        check(completed && owner.navigation.currentWindow!.presentations == 1 && owner.gallery.view.alpha == 1, "restore reuses original gallery")
        owner.expandPIP()
        check(owner.context.sharedContext.mediaManager.currentPictureInPictureNode == nil, "stop releases media manager ownership")
        let button = GalleryHarness(); button.isCentral = true
        button.pictureInPictureButtonPressed()
        let buttonAV = AVPictureInPictureController.instances.last!
        buttonAV.isPictureInPicturePossible = true
        button.pictureInPictureButtonPressed()
        check(buttonAV.starts == 1, "PiP button uses same prepared controller")
        for kind in 0..<3 {
            let excluded = GalleryHarness()
            if kind == 0 { excluded.context.currentAppConfiguration.value.data = ["ios_killswitch_disable_native_pip_v2": true] }
            if kind == 1 { excluded.item!.contentInfo = .message(Message(adAttribute: 1),0) }
            if kind == 2 { (excluded.item!.content as! NativeVideoContent).fileReference.media.isAnimated = true }
            excluded.updateCentral(true)
            check(excluded.nativePictureInPictureContent == nil, "native exclusions remain unchanged")
        }
        print("PASS: \(count) actual controller/setup/centrality/button/swipe/restore and teardown checks; AVKit/KVO/UIKit boundaries")
    }
}
