@main enum Tests {
    final class ReleaseProbe {
        weak var content: NativePictureInPictureContentImpl?
        init(_ content: NativePictureInPictureContentImpl?) { self.content = content }
    }
    static var count = 0
    static func check(_ value: @autoclosure () -> Bool, _ message: String) {
        count += 1
        if !value() { fatalError("first PiP regression: " + message) }
    }
    static func prepared() -> (GalleryHarness, NativePictureInPictureContentImpl, AVPictureInPictureController) {
        let gallery = GalleryHarness()
        gallery.updateCentral(true)
        TestScheduler.advance()
        return (gallery, gallery.nativePictureInPictureContent as! NativePictureInPictureContentImpl, AVPictureInPictureController.instances.last!)
    }
    static func main() {
        let (gallery, content, av) = prepared()
        gallery.pictureInPictureButtonPressed()
        gallery.pictureInPictureButtonPressed()
        TestScheduler.advance()
        check(av.starts == 0 && content.hasPendingPictureInPictureStart, "first button request waits for readiness")
        av.isPictureInPicturePossible = true
        TestScheduler.advance()
        check(av.starts == 1 && av.isPictureInPictureActive, "first request starts on ready without a second tap")
        check(gallery.gallery.dismissals == 0, "duplicate pending taps never force-dismiss the source")
        check(gallery.dismissals == 1, "successful native transition dismisses once")
        for _ in 0..<10 { av.isPictureInPicturePossible = true }
        TestScheduler.advance()
        check(av.starts == 1, "repeated readiness never repeats native start")
        var restored = false
        content.pictureInPictureController(av, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: { restored = $0 })
        check(restored && gallery.navigation.currentWindow!.presentations == 1, "return restores original gallery")
        content.requestExpand()
        check(!av.isPictureInPictureActive && !gallery.videoNode!.withoutHierarchy, "native stop releases background ownership")
        check(gallery.maybePerformActionForSwipeDismiss(), "swipe works after restoration")
        TestScheduler.advance()
        check(av.starts == 2, "restored controller starts again")
        content.stop()

        let cold = GalleryHarness()
        cold.isCentral = true
        cold.videoNode!.hasLayer = false
        cold.videoNode!.ownsContentNode = false
        let previousCount = AVPictureInPictureController.instances.count
        check(cold.maybePerformActionForSwipeDismiss(), "first cold swipe creates preparation and retains request")
        TestScheduler.advance()
        check(AVPictureInPictureController.instances.count == previousCount, "nonowner/missing layer never attaches an AVKit source")
        cold.videoNode!.ownsContentNode = true
        cold.videoNode!.hasLayer = true
        TestScheduler.advance(0.05)
        check(AVPictureInPictureController.instances.count == previousCount + 1, "first frame preparation retries within the original request")
        let coldAV = AVPictureInPictureController.instances.last!
        check(coldAV.contentSource?.sampleBufferDisplayLayer === cold.videoNode!.layer, "only original live sample layer is used")
        coldAV.isPictureInPicturePossible = true
        TestScheduler.advance()
        check(coldAV.starts == 1 && cold.dismissals == 1, "first cold swipe succeeds without prior button warmup")
        (cold.nativePictureInPictureContent as! NativePictureInPictureContentImpl).stop()

        let statusOwner = GalleryHarness()
        statusOwner.isCentral = true
        statusOwner.videoNode!.hasLayer = false
        statusOwner.setupNativePictureInPicture()
        let beforeStatus = AVPictureInPictureController.instances.count
        statusOwner.videoNode!.hasLayer = true
        statusOwner.videoNode!.status.emit(MediaPlayerStatus())
        TestScheduler.advance()
        check(AVPictureInPictureController.instances.count == beforeStatus + 1, "status prepares a late layer even before explicit start")

        let (cancelled, cancelledContent, cancelledAV) = prepared()
        check(cancelled.maybePerformActionForSwipeDismiss(), "pending swipe accepted")
        cancelled.updateCentral(false)
        cancelledAV.isPictureInPicturePossible = true
        TestScheduler.advance(6)
        check(cancelledAV.starts == 0 && !cancelledContent.hasPendingPictureInPictureStart, "navigation cancels pending start and stale KVO/timeout")
        check(!cancelledAV.canStartPictureInPictureAutomaticallyFromInline, "noncentral readiness cannot enable automatic PiP")
        check(!cancelledContent.beginPictureInPicture(), "noncentral manual request rejected")

        let (timed, timedContent, timedAV) = prepared()
        timed.pictureInPictureButtonPressed()
        TestScheduler.advance(5.1)
        check(!timedContent.hasPendingPictureInPictureStart && timedAV.starts == 0, "unavailable AVKit request expires without silent later launch")
        timedAV.isPictureInPicturePossible = true
        TestScheduler.advance()
        check(timedAV.starts == 0 && timed.gallery.view.alpha == 1 && timed.dismissals == 0, "late readiness after timeout preserves visible gallery")
        timed.pictureInPictureButtonPressed()
        TestScheduler.advance()
        check(timedAV.starts == 1, "fresh user request after timeout can start")
        timedContent.stop()

        let missing = GalleryHarness()
        missing.isCentral = true
        missing.videoNode!.hasLayer = false
        missing.pictureInPictureButtonPressed()
        TestScheduler.advance(5.1)
        let beforeLateLayer = AVPictureInPictureController.instances.count
        missing.videoNode!.hasLayer = true
        TestScheduler.advance(1)
        check(AVPictureInPictureController.instances.count == beforeLateLayer, "preparation retry is bounded and stops after expiry")
        check(!(missing.nativePictureInPictureContent as! NativePictureInPictureContentImpl).hasPendingPictureInPictureStart, "missing-source request fully cancelled")

        let (transition, transitionContent, transitionAV) = prepared()
        let layer = transition.videoNode!.layer
        layer.cornerRadius = 3
        layer.cornerCurve = .circular
        layer.maskedCorners = .layerMinXMinYCorner
        layer.masksToBounds = false
        layer.isOpaque = true
        let originalBackground = layer.backgroundColor
        let presentation = CALayer(); presentation.cornerRadius = 5; layer.presented = presentation
        transitionAV.completesStart = false
        transitionAV.isPictureInPicturePossible = true
        transition.pictureInPictureButtonPressed()
        TestScheduler.advance()
        check(transitionAV.starts == 1 && transitionContent.hasPendingPictureInPictureStart, "native start remains in flight until delegate completion")
        check(transition.gallery.view.alpha == 1 && transition.dismissals == 0 && transition.videoNode!.nativePictureInPictureActive, "source geometry and opacity remain stable during AVKit transition")
        check(layer.maskedCorners.rawValue == 15 && layer.masksToBounds && layer.cornerCurve == .continuous, "all four source corners use one continuous clip")
        check(!layer.isOpaque && layer.backgroundColor == nil, "source corners cannot carry opaque black backing")
        let animation = layer.animations["nagramiXPiPSourceCorners"]
        check(animation?.keyPath == "cornerRadius" && animation?.duration == 0.3, "corner curve starts in same native transition")
        check((animation?.fromValue as? CGFloat) == 5 && abs((animation?.toValue as? CGFloat ?? 0) - 64.8) < 0.000001, "interrupted corner animation continues from presentation radius")
        transition.pictureInPictureButtonPressed()
        TestScheduler.advance()
        check(transitionAV.starts == 1 && transition.gallery.dismissals == 0, "second tap during animation cannot detach source")
        transitionAV.finishStart()
        check(transition.dismissals == 1 && transition.gallery.view.alpha == 0, "gallery fades only after native transition completes")
        check(layer.cornerRadius == 3 && layer.cornerCurve == .circular && layer.maskedCorners.rawValue == 1, "original radius/curve/corners restored after handoff")
        check(!layer.masksToBounds && layer.isOpaque && layer.backgroundColor === originalBackground && layer.animations.isEmpty, "original appearance restored without residual mask/animation")
        check(CATransaction.depth == 0, "appearance transactions balanced")
        transitionContent.stop()

        let (failed, failedContent, failedAV) = prepared()
        failedAV.isPictureInPicturePossible = true
        failedAV.completesStart = false
        failed.pictureInPictureButtonPressed()
        TestScheduler.advance()
        failedContent.pictureInPictureController(failedAV, failedToStartPictureInPictureWithError: NSError(domain: "test", code: 1))
        check(!failedContent.hasPendingPictureInPictureStart && failed.gallery.view.alpha == 1 && failed.dismissals == 0, "AVKit failure leaves original gallery visible and permits retry")
        check(failed.videoNode!.layer.animations.isEmpty && !failed.videoNode!.withoutHierarchy && !failed.videoNode!.nativePictureInPictureActive, "failure restores appearance and playback ownership")
        check(failed.context.sharedContext.mediaManager.currentPictureInPictureNode == nil, "failure clears global PiP ownership")
        failedAV.completesStart = true
        failed.pictureInPictureButtonPressed()
        TestScheduler.advance()
        check(failedAV.starts == 2 && failed.dismissals == 1, "next request recovers after native failure")
        failedContent.stop()

        let (lost, lostContent, lostAV) = prepared()
        lostAV.completesStart = false; lostAV.isPictureInPicturePossible = true
        lost.pictureInPictureButtonPressed(); TestScheduler.advance()
        lost.updateCentral(false)
        check(lostAV.stops == 1 && !lostContent.hasPendingPictureInPictureStart, "leaving during native start cancels controller")
        check(lost.gallery.view.alpha == 1 && lost.videoNode!.layer.animations.isEmpty, "interrupted handoff restores original appearance")

        for key in ["ios_killswitch_disable_native_pip_v2", "ios_killswitch_disable_swipe_pip", "video_swipe_up_to_close"] {
            let blocked = GalleryHarness(); blocked.isCentral = true
            blocked.context.currentAppConfiguration.value.data = [key: true]
            check(!blocked.maybePerformActionForSwipeDismiss(), "server restriction preserved: " + key)
        }
        let off = GalleryHarness(); off.isCentral = true
        NagramiXTabSettings.videoPiPSwipeEnabled = false
        check(!off.maybePerformActionForSwipeDismiss() && off.nativePictureInPictureContent == nil, "saved swipe OFF does not create/start a controller")
        NagramiXTabSettings.videoPiPSwipeEnabled = true
        let ad = GalleryHarness(); ad.isCentral = true; ad.item!.contentInfo = .message(Message(adAttribute: 1),0)
        check(!ad.maybePerformActionForSwipeDismiss(), "advertisement gate preserved")
        let animated = GalleryHarness(); animated.isCentral = true
        (animated.item!.content as! NativeVideoContent).fileReference.media.isAnimated = true
        check(!animated.maybePerformActionForSwipeDismiss(), "animated content gate preserved")
        let unsupported = GalleryHarness(); unsupported.isCentral = true
        AVPictureInPictureController.supported = false
        check(!unsupported.maybePerformActionForSwipeDismiss(), "unsupported system keeps native dismissal")
        AVPictureInPictureController.supported = true
        check(!off.maybePerformActionForSwipeDownDismiss(), "downward swipe unchanged")

        let (hidden, hiddenContent, hiddenAV) = prepared()
        hidden.pictureInPictureButtonPressed()
        hidden.setVisible(false)
        TestScheduler.advance()
        hiddenAV.isPictureInPicturePossible = true
        TestScheduler.advance(6)
        check(hiddenAV.starts == 0 && !hiddenContent.hasPendingPictureInPictureStart, "queued button is rejected after the gallery becomes hidden")
        hidden.setVisible(true)
        hiddenAV.isPictureInPicturePossible = false
        hidden.pictureInPictureButtonPressed(); TestScheduler.advance()
        hidden.setVisible(false)
        hiddenAV.isPictureInPicturePossible = true; TestScheduler.advance()
        check(hiddenAV.starts == 0 && !hiddenContent.hasPendingPictureInPictureStart, "hiding cancels an already queued readiness request")

        let (resized, resizedContent, resizedAV) = prepared()
        resized.videoNode!.layer.bounds = .zero
        resizedAV.isPictureInPicturePossible = true
        resized.pictureInPictureButtonPressed(); TestScheduler.advance()
        check(resizedAV.starts == 0, "ready flag alone never starts with a zero source rectangle")
        resized.videoNode!.layer.bounds = CGRect(x: 0, y: 0, width: 1280, height: 720)
        TestScheduler.advance(0.05)
        check(resizedAV.starts == 1, "first request starts when source geometry arrives")
        resizedContent.stop()

        let (replaced, replacedContent, oldAV) = prepared()
        replaced.pictureInPictureButtonPressed(); TestScheduler.advance()
        replaced.videoNode!.layer = VideoLayer()
        oldAV.isPictureInPicturePossible = true
        replaced.videoNode!.status.emit(MediaPlayerStatus())
        let newAV = AVPictureInPictureController.instances.last!
        TestScheduler.advance()
        check(newAV !== oldAV && oldAV.contentSource == nil && oldAV.observers.isEmpty, "source replacement detaches the old native source and KVO")
        check(oldAV.starts == 0 && newAV.starts == 0, "stale ready callback cannot start an old source")
        newAV.isPictureInPicturePossible = true; TestScheduler.advance()
        check(newAV.starts == 1 && newAV.contentSource?.sampleBufferDisplayLayer === replaced.videoNode!.layer, "pending request transfers to the currently owned layer")
        replacedContent.stop()

        let (reduced, reducedContent, reducedAV) = prepared()
        UIAccessibility.isReduceMotionEnabled = true
        reducedAV.completesStart = false; reducedAV.isPictureInPicturePossible = true
        reduced.pictureInPictureButtonPressed(); TestScheduler.advance()
        check(reduced.videoNode!.layer.animations["nagramiXPiPSourceCorners"]?.duration == 0, "Reduce Motion avoids custom corner motion")
        reducedAV.finishStart(); reducedContent.stop()
        UIAccessibility.isReduceMotionEnabled = false

        let (stalled, stalledContent, stalledAV) = prepared()
        stalledAV.completesStart = false; stalledAV.isPictureInPicturePossible = true
        stalled.pictureInPictureButtonPressed(); TestScheduler.advance(5.1)
        check(stalledAV.stops == 1 && !stalledContent.hasPendingPictureInPictureStart, "native startup watchdog cancels an incomplete transition")
        check(stalled.gallery.view.alpha == 1 && stalled.context.sharedContext.mediaManager.currentPictureInPictureNode == nil, "watchdog restores visible gallery and releases global ownership")
        stalledAV.finishStart()
        check(stalled.dismissals == 0 && !stalledAV.isPictureInPictureActive, "late native completion after cancellation cannot dismiss the source")

        let lifecycleNode = UniversalVideoNode(), lifecycleContext = AccountContext(), lifecycleManager = MediaManager()
        defer { withExtendedLifetime(lifecycleContext) {}; withExtendedLifetime(lifecycleManager) {} }
        var temporary: NativePictureInPictureContentImpl? = NativePictureInPictureContentImpl(context: lifecycleContext, mediaManager: lifecycleManager, accountId: 1, hiddenMedia: nil, videoNode: lifecycleNode, canSkip: true, willBegin: { _ in }, didBegin: { _ in }, didEnd: { _ in }, expand: { $0() })
        let lifecycleAV = AVPictureInPictureController.instances.last!
        temporary!.updateIsCentral(isCentral: true)
        temporary!.beginPictureInPicture()
        let probe = ReleaseProbe(temporary)
        temporary = nil
        TestScheduler.advance(10)
        check(probe.content == nil, "queued readiness/retries never retain the controller")
        check(lifecycleAV.observers.isEmpty && lifecycleAV.delegate == nil && lifecycleAV.contentSource == nil, "teardown releases KVO/delegate/source")
        check(lifecycleNode.status.handlers.isEmpty && !lifecycleNode.withoutHierarchy, "teardown releases both subscriptions and playback lease")
        print("PASS: \(count) first-request/readiness/handoff/corner/lifecycle checks; AVKit/UIKit/CA scheduling are explicit boundaries")
    }
}
