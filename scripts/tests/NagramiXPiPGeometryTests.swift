@main enum Tests {
    static var count = 0
    static func check(_ value: @autoclosure () -> Bool, _ message: String) {
        count += 1
        if !value() { fatalError("PiP geometry regression: " + message) }
    }
    static func prepared() -> (GalleryHarness, NativePictureInPictureContentImpl, AVPictureInPictureController) {
        NagramiXTabSettings.videoPiPSwipeEnabled = true
        let item = GalleryHarness()
        item.centralityUpdated(isCentral: true)
        TestScheduler.advance()
        return (item, item.nativePictureInPictureContent as! NativePictureInPictureContentImpl, AVPictureInPictureController.instances.last!)
    }
    static func drag(_ item: GalleryHarness, distance: CGFloat, velocity: CGFloat, release: Bool = true) {
        let ui = item.gallery.galleryNode, scroll = ui.scrollView
        scroll.isDragging = true
        ui.scrollViewWillBeginDragging(scroll)
        for step in 1...6 {
            scroll.panGestureRecognizer.offset = CGPoint(x: 0, y: -distance * CGFloat(step) / 6)
            scroll.contentOffset.y = scroll.contentSize.height / 3 + distance * CGFloat(step) / 6
            ui.scrollViewDidScroll(scroll)
            if distance > 0 && item.usesNativePictureInPictureSwipe {
                check(scroll.contentOffset.y == scroll.contentSize.height / 3, "upward drag never displays a displaced video frame")
                check(ui.backgroundNode.backgroundColor?.opacity == 1 && ui.footerNode.alpha == 1, "upward PiP gesture does not apply close-gallery chrome")
            }
        }
        var target = CGPoint.zero
        withUnsafeMutablePointer(to: &target) { ui.scrollViewWillEndDragging(scroll, withVelocity: CGPoint(x: 0, y: velocity), targetContentOffset: $0) }
        if distance > 0 && item.usesNativePictureInPictureSwipe {
            check(target.y == scroll.contentSize.height / 3, "release never schedules displaced deceleration")
        }
        if release { scroll.isDragging = false }
    }
    static func button(_ item: GalleryHarness, _ av: AVPictureInPictureController) {
        av.isPictureInPicturePossible = true
        item.pictureInPictureButtonPressed()
        TestScheduler.advance()
    }
    static func requestRestore(_ content: NativePictureInPictureContentImpl, _ av: AVPictureInPictureController, result: @escaping (Bool) -> Void) {
        content.pictureInPictureController(av, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: result)
        TestScheduler.advance()
        Window.shared.finishPresentation()
    }
    static func main() {
        let (swipe, swipeContent, swipeAV) = prepared()
        let ui = swipe.gallery.galleryNode
        let bounds = swipe.videoNode!.layer.bounds
        swipe.context.currentAppConfiguration.value.data = ["video_swipe_up_to_close": true]
        swipeAV.isPictureInPicturePossible = true
        drag(swipe, distance: 240, velocity: 1.4, release: false)
        TestScheduler.advance(0.1)
        check(swipeAV.starts == 0 && swipeContent.hasPendingPictureInPictureStart, "recognizer must finish before source capture")
        swipe.videoNode!.frameContainer.isHidden = true
        ui.scrollView.isDragging = false
        TestScheduler.advance(0.1)
        check(swipeAV.starts == 0, "thumbnail readiness cannot replace the first visible video frame")
        swipe.videoNode!.frameContainer.isHidden = false
        TestScheduler.advance(0.06)
        check(swipeAV.starts == 1 && swipe.dismissals == 1, "one upward swipe starts the native controller, including server close preference")
        check(swipe.videoNode!.layer.bounds == bounds && swipe.videoNode!.layer.animations.isEmpty, "swipe preserves original sample-buffer geometry")
        check(swipe.videoNode!.backgroundColor?.opacity == 0, "ordinary rectangular video backing is clear during native motion")
        check(swipe.disablePictureInPicturePlaceholder && swipe.gallery.galleryNode.normalAnimations == 0, "native motion has no second gallery transition or large gallery placeholder")
        check(swipe.videoNode!.plays == 0 && swipe.videoNode!.pauses == 0 && swipe.videoNode!.seeks.isEmpty, "swipe keeps the same player and timebase")
        var results: [Bool] = []
        requestRestore(swipeContent, swipeAV) { results.append($0) }
        for _ in 0..<3 { swipe.gallery.tryCompleteNativePictureInPictureRestore() }
        check(results.isEmpty, "repeated layout callbacks in one transaction cannot confirm the restore rect")
        let target = swipe.videoNode!.view
        target.convertedRect = CGRect(x: 0, y: 260, width: 384, height: 216)
        TestScheduler.advance(0.05)
        check(results.isEmpty, "changed target rect invalidates the first restore candidate")
        target.convertedRect = CGRect(x: 0, y: 280, width: 384, height: 216)
        TestScheduler.advance(0.05)
        check(results.isEmpty, "rotation/safe-area layout cannot acknowledge a moving target")
        check(ui.nativePictureInPictureRestoring && ui.navigationBar?.alpha == 0 && ui.footerNode.alpha == 0, "gallery controls stay hidden during target preparation")
        TestScheduler.advance(0.06)
        check(results == [true], "two consecutive real layout passes acknowledge one stable target")
        check(ui.backgroundNode.alpha == 1 && ui.navigationBar?.alpha == 0 && ui.footerNode.alpha == 0, "backdrop fades behind native return while gallery controls wait for DidStop")
        check(swipe.videoNode!.backgroundColor?.opacity == 0 && swipe.videoNode!.withoutHierarchy, "native return retains clear source host and playback ownership")
        swipeContent.requestExpand()
        check(!swipeAV.isPictureInPictureActive && !ui.nativePictureInPictureTransitionInProgress && ui.scrollView.isScrollEnabled, "DidStop releases the transaction and restores input")
        check(ui.navigationBar?.alpha == 1 && ui.footerNode.visibilityAlpha == 1 && swipe.videoNode!.backgroundColor?.opacity == 1, "DidStop restores ordinary controls and backing")
        check(swipe.videoNode!.plays == 0 && swipe.videoNode!.pauses == 0 && swipe.videoNode!.seeks.isEmpty, "reverse transition never restarts playback")
        check(swipe.activations == 0 && ui.normalAnimations == 0, "return never reuses the stock media-open animation")
        for cycle in 2...5 {
            drag(swipe, distance: 45, velocity: 1.5)
            TestScheduler.advance(0.06)
            check(swipeAV.starts == cycle && swipe.dismissals == cycle, "each first swipe works after a previous restore")
            var restored: Bool?
            requestRestore(swipeContent, swipeAV) { restored = $0 }
            TestScheduler.advance(0.11)
            check(restored == true && swipe.videoNode!.layer.bounds == bounds, "repeat restore preserves video dimensions")
            swipeContent.requestExpand()
        }

        let (tap, tapContent, tapAV) = prepared()
        tapAV.completesStart = false
        button(tap, tapAV)
        check(tapAV.starts == 1 && tap.dismissals == 0, "first button press starts once and retains gallery until DidStart")
        for _ in 0..<5 { tap.pictureInPictureButtonPressed(); tapAV.isPictureInPicturePossible = true }
        TestScheduler.advance()
        check(tapAV.starts == 1, "duplicate input and KVO events cannot start another native transition")
        check(tap.videoNode!.layer.bounds == bounds && tap.videoNode!.layer.animations.isEmpty, "button and swipe use the same unmodified layer")
        tapAV.finishStart()
        var repeated: [Bool] = []
        tapContent.pictureInPictureController(tapAV, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: { repeated.append($0) })
        tapContent.pictureInPictureController(tapAV, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: { repeated.append($0) })
        TestScheduler.advance(); Window.shared.finishPresentation(); TestScheduler.advance(0.06)
        check(repeated == [true, true], "duplicate restore handlers share presentation and complete once each")
        tapContent.requestExpand()

        let (cancelled, cancelledContent, cancelledAV) = prepared()
        drag(cancelled, distance: 50, velocity: 0.2)
        TestScheduler.advance(0.1)
        check(cancelledAV.starts == 0 && !cancelledContent.hasPendingPictureInPictureStart && cancelled.gallery.galleryNode.normalAnimations == 0, "short cancelled gesture leaves full gallery intact")
        check(cancelled.gallery.galleryNode.scrollView.isScrollEnabled && cancelled.chat.pushed == 1, "cancelled gesture keeps input and chat transition intact")

        let (slow, slowContent, slowAV) = prepared()
        slowAV.isPictureInPicturePossible = true
        drag(slow, distance: 100, velocity: 0.3)
        TestScheduler.advance(0.06)
        check(slowAV.starts == 1 && slow.dismissals == 1, "a deliberate short slow swipe does not require a quarter-screen drag")
        slowContent.stop()

        let (timeout, timeoutContent, timeoutAV) = prepared()
        drag(timeout, distance: 300, velocity: 2)
        TestScheduler.advance(5.1)
        check(timeoutAV.starts == 0 && !timeoutContent.hasPendingPictureInPictureStart, "readiness timeout cancels the original request")
        check(timeout.gallery.galleryNode.scrollView.isScrollEnabled && timeout.gallery.galleryNode.pager.isScrollEnabled && timeout.gallery.galleryNode.backgroundNode.alpha == 1, "timeout rolls back every gesture and chrome lock")
        timeoutAV.isPictureInPicturePossible = true; TestScheduler.advance()
        check(timeoutAV.starts == 0 && timeout.chat.toasts == 0, "late KVO cannot resurrect a timed-out swipe")
        button(timeout, timeoutAV)
        timeoutContent.stop()

        let (failed, failedContent, failedAV) = prepared()
        failedAV.completesStart = false
        button(failed, failedAV)
        failedContent.pictureInPictureController(failedAV, failedToStartPictureInPictureWithError: NSError(domain: "boundary", code: 1))
        check(failed.videoNode!.backgroundColor?.opacity == 1 && failed.playbackControls.view?.alpha == 1 && failed.statusButtonNode.alpha == 1, "failure restores original host and controls")
        check(failedAV.delegate == nil && failedAV.contentSource == nil && failedAV.observers.isEmpty, "failed controller cannot deliver stale callbacks")

        for reason in 0..<6 {
            let (bad, content, av) = prepared()
            button(bad, av)
            var restored: [Bool] = []
            requestRestore(content, av) { restored.append($0) }
            switch reason {
            case 0: bad.videoNode!.view.convertedRect = CGRect(x: 500, y: 900, width: 384, height: 216)
            case 1: bad.videoNode!.view.convertedRect = CGRect(x: 0, y: 0, width: 0, height: 200)
            case 2: bad.videoNode!.view.convertedRect = CGRect(x: CGFloat.infinity, y: 0, width: 100, height: 200)
            case 3: bad.videoNode!.ownsContentNode = false
            case 4: bad.videoNode!.view.window = Window()
            default: bad.videoNode!.layer.superlayer = nil
            }
            TestScheduler.advance(0.2)
            check(restored.isEmpty && av.isPictureInPictureActive, "invalid/offscreen/unowned destination cannot receive a successful restore")
            TestScheduler.advance(5.1)
            check(restored == [false] && av.isPictureInPictureActive && bad.videoNode!.withoutHierarchy, "failed restore keeps native video alive and completes exactly once")
            content.stop()
        }

        let (interrupt, interruptedContent, interruptedAV) = prepared()
        button(interrupt, interruptedAV)
        var interrupted: [Bool] = []
        interruptedContent.pictureInPictureController(interruptedAV, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: { interrupted.append($0) })
        interruptedContent.stop()
        TestScheduler.advance(5.1)
        Window.shared.finishPresentation()
        check(interrupted == [false] && interrupt.gallery.view.window == nil, "stop/timeout/late appearance never acknowledge an abandoned gallery")

        for shape in [CGSize(width: 1920, height: 1080), CGSize(width: 384, height: 832), CGSize(width: 720, height: 720)] {
            let (shaped, content, av) = prepared()
            shaped.videoNode!.layer.bounds = CGRect(origin: .zero, size: shape)
            button(shaped, av)
            check(shaped.videoNode!.layer.bounds.size == shape && av.starts == 1, "landscape/portrait/square keep complete unscaled sample-buffer bounds")
            content.stop()
        }

        for reason in 0..<6 {
            let (ordinary, _, _) = prepared()
            switch reason {
            case 0: NagramiXTabSettings.videoPiPSwipeEnabled = false
            case 1: ordinary.context.currentAppConfiguration.value.data = ["ios_killswitch_disable_swipe_pip": true]
            case 2: ordinary.context.currentAppConfiguration.value.data = ["ios_killswitch_disable_native_pip_v2": true]
            case 3: (ordinary.item!.content as! NativeVideoContent).fileReference.media.isAnimated = true
            case 4: ordinary.item!.contentInfo = .message(Message(adAttribute: 1), 0)
            default: ordinary.item!.content = NSObject(); ordinary.videoNode!.hasLayer = false
            }
            check(!ordinary.usesNativePictureInPictureSwipe && !ordinary.maybePerformActionForSwipeDismiss(), "OFF/unsupported/GIF/ads/kill switches retain ordinary gesture policy")
        }
        let (down, _, downAV) = prepared()
        drag(down, distance: -300, velocity: -2)
        check(down.gallery.galleryNode.normalAnimations > 0 && downAV.starts == 0, "downward swipe keeps stock gallery dismissal")

        let (reduced, reducedContent, reducedAV) = prepared()
        UIAccessibility.isReduceMotionEnabled = true
        UIView.durations.removeAll()
        button(reduced, reducedAV)
        var reducedRestore: Bool?
        requestRestore(reducedContent, reducedAV) { reducedRestore = $0 }
        TestScheduler.advance(0.06)
        reducedContent.requestExpand()
        check(reducedRestore == true && UIView.durations.allSatisfy { $0 == 0 }, "Reduce Motion retains native state transitions without custom chrome animation")
        UIAccessibility.isReduceMotionEnabled = false
        print("\(count) PiP geometry checks passed")
    }
}
