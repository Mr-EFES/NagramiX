final class WeakGalleryProbe {
    weak var value: GalleryHarness?
    init(_ value: GalleryHarness?) { self.value = value }
}

@main enum Tests {
    static var count = 0
    static func check(_ value: @autoclosure () -> Bool, _ message: String) {
        count += 1
        if !value() { fatalError("PiP visual transition regression: " + message) }
    }
    static func prepared() -> (GalleryHarness, NativePictureInPictureContentImpl, AVPictureInPictureController) {
        let gallery = GalleryHarness(); gallery.centralityUpdated(isCentral: true)
        TestScheduler.advance()
        return (gallery, gallery.nativePictureInPictureContent as! NativePictureInPictureContentImpl, AVPictureInPictureController.instances.last!)
    }
    static func swipe(_ gallery: GalleryHarness) {
        let node = gallery.gallery.galleryNode
        node.scrollView.contentOffset.y = 1012
        node.scrollView.isDragging = true
        node.scrollViewDidScroll(node.scrollView)
        var target = CGPoint.zero
        withUnsafeMutablePointer(to: &target) { node.scrollViewWillEndDragging(node.scrollView, withVelocity: CGPoint(x: 0,y: 1.4), targetContentOffset: $0) }
    }
    static func start(_ gallery: GalleryHarness, _ av: AVPictureInPictureController) {
        av.isPictureInPicturePossible = true
        gallery.pictureInPictureButtonPressed()
        TestScheduler.advance()
    }
    static func main() {
        let (timed, timedContent, timedAV) = prepared()
        swipe(timed)
        let ui = timed.gallery.galleryNode
        check(timedAV.starts == 0 && ui.nativePictureInPictureTransitionInProgress, "accepted swipe freezes before AVKit readiness")
        check(ui.scrollView.contentOffset.y == 1012, "released swipe keeps its actual visible source rect")
        check(!ui.scrollView.isScrollEnabled && !ui.pager.isScrollEnabled && !ui.pager.isUserInteractionEnabled, "pending transition locks vertical and horizontal gestures")
        check(timed.chat.toasts == 0 && ui.normalAnimations == 0, "accepted pending swipe is not reported as a completed PiP or normal dismiss")
        for _ in 0..<4 { timed.pictureInPictureButtonPressed() }; TestScheduler.advance()
        check(timedAV.starts == 0 && timed.dismissals == 0, "duplicate requests do not dismiss an unready source")
        TestScheduler.advance(5.1)
        check(!timedContent.hasPendingPictureInPictureStart && !ui.nativePictureInPictureTransitionInProgress, "watchdog rolls back entire visual transaction")
        check(ui.scrollView.contentOffset.y == ui.scrollView.contentSize.height/3 && ui.scrollView.isScrollEnabled && ui.pager.isScrollEnabled && ui.pager.isUserInteractionEnabled, "timeout restores centred geometry and gestures")
        check(ui.backgroundNode.alpha == 1 && ui.backgroundNode.backgroundColor?.opacity == 1 && ui.navigationBar?.alpha == 1 && ui.footerNode.visibilityAlpha == 1, "timeout removes transparent backdrop and restores chrome")
        check(timed.chat.pushed == 1 && timed.chat.toasts == 0 && timed.gallery.view.window != nil, "failure leaves full gallery, no success toast")
        timedAV.isPictureInPicturePossible = true; TestScheduler.advance()
        check(timedAV.starts == 0, "late ready after expiry cannot start PiP")
        start(timed,timedAV)
        check(timedAV.starts == 1 && timed.dismissals == 1, "new request recovers after an unready timeout")
        timedContent.stop()
        check(timed.chat.pushed == 0, "closing PiP without restoring never pushes a hidden gallery over chat")

        let (gallery, content, av) = prepared()
        let video = gallery.videoNode!, layer = video.layer, manager = gallery.context.sharedContext.mediaManager.galleryHiddenMediaManager
        let originalRect = layer.bounds
        layer.cornerRadius = 7; layer.maskedCorners = .layerMinXMinYCorner; layer.masksToBounds = false; layer.isOpaque = true
        let originalBackground = layer.backgroundColor
        av.completesStart = false
        av.isPictureInPicturePossible = true
        gallery.pictureInPictureButtonPressed()
        TestScheduler.advance()
        check(av.starts == 1 && content.hasPendingPictureInPictureStart && gallery.dismissals == 0, "native handoff keeps source until DidStart")
        check(layer.bounds == originalRect && layer.cornerRadius == 7 && layer.maskedCorners.rawValue == 1 && !layer.masksToBounds && layer.isOpaque && layer.backgroundColor === originalBackground, "handoff never changes the live layer rect, corners, opacity or backing")
        check(layer.animations.isEmpty && gallery.gallery.view.alpha == 1, "AVKit alone animates the live source without a copy or root fade")
        check(manager.sources.count == 2, "native hidden-media ownership acquired before gallery releases its source")
        check(video.withoutHierarchy && video.nativePictureInPictureActive && video.plays == 0 && video.pauses == 0 && video.seeks.isEmpty, "same player continues without a pause, seek or restart")
        let state = av.contentSource!.playbackDelegate!
        av.finishStart()
        check(gallery.dismissals == 1 && gallery.gallery.view.alpha == 1 && gallery.gallery.view.layer.alphaAnimations == 0, "native completion removes gallery without a second fade")
        check(gallery.gallery.view.window == nil && manager.sources.count == 1 && !manager.sources.keys.contains(1), "PiP keeps hidden-media source after gallery removal")
        check(gallery.disablePictureInPicturePlaceholder, "large gallery placeholder stays suppressed during PiP")
        content.pictureInPictureControllerWillStartPictureInPicture(av)
        content.pictureInPictureControllerDidStartPictureInPicture(av)
        for _ in 0..<6 { av.isPictureInPicturePossible = true }; TestScheduler.advance()
        check(av.starts == 1 && gallery.dismissals == 1 && manager.sources.count == 1, "duplicate delegates and readiness do not create another handoff or hidden owner")
        gallery.visibilityUpdated(isVisible: false); gallery.centralityUpdated(isCentral: false)
        check(video.canAttachContent && video.pauses == 0 && video.seeks.isEmpty && video.mutedContinuations == 0 && content.keepsVideoAttached, "gallery disappearance never detaches, pauses, rewinds or mutes active PiP")
        let oldInvalidations = av.invalidations
        state.pictureInPictureController(av,didTransitionToRenderSize: CMVideoDimensions(width: 0,height: 200))
        check(av.invalidations == oldInvalidations, "invalid render size ignored")
        state.pictureInPictureController(av,didTransitionToRenderSize: CMVideoDimensions(width: 320,height: 180))
        let renderInvalidations = av.invalidations
        state.pictureInPictureController(av,didTransitionToRenderSize: CMVideoDimensions(width: 320,height: 180))
        check(renderInvalidations == oldInvalidations+1 && av.invalidations == renderInvalidations && layer.bounds == originalRect, "render resize refreshes controls once without resizing the live origin")
        for _ in 0..<3 { state.pictureInPictureController(av,setPlaying: false) }
        check(video.status.value?.status == .paused && video.toggles == 0, "repeated pause is idempotent")
        for _ in 0..<3 { state.pictureInPictureController(av,setPlaying: true) }
        check(video.status.value?.status == .playing && video.toggles == 0 && video.status.value?.timestamp == 30, "repeated play never toggles pause or resets timestamp")
        video.status.emit(MediaPlayerStatus(status: .buffering)); state.pictureInPictureController(av,setPlaying: true)
        check(video.status.value?.status == .playing, "play request while buffering never pauses the player")
        var seekComplete = 0
        state.pictureInPictureController(av,skipByInterval: CMTime(seconds: 10,preferredTimescale: 30),completion: { seekComplete += 1 })
        check(video.seeks.last == 40 && seekComplete == 1, "native seek forwards original playback position and completes once")
        let position = video.status.value?.timestamp
        let pauses = video.pauses, plays = video.plays, seeks = video.seeks
        var restores: [Bool] = []
        let presentations = Window.shared.presentations
        content.pictureInPictureController(av,restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: { restores.append($0) })
        content.pictureInPictureController(av,restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: { restores.append($0) })
        TestScheduler.advance()
        check(restores.isEmpty && Window.shared.presentations == presentations+1 && content.keepsVideoAttached, "restore waits for actual appearance; repeated callbacks share one presentation")
        check(gallery.gallery.view.alpha == 1 && gallery.gallery.view.layer.alphaAnimations == 0 && video.pauses == pauses && video.plays == plays && video.seeks == seeks, "return prepares existing source without a root fade or playback action")
        gallery.gallery.galleryNode.containerLayout = nil
        Window.shared.finishPresentation(layout: false)
        TestScheduler.advance(0.1)
        check(restores.isEmpty, "view appearance without layout cannot acknowledge restoration")
        gallery.gallery.galleryNode.containerLayout = (44,ContainerViewLayout())
        layer.bounds = .zero
        TestScheduler.advance(0.1)
        check(restores.isEmpty, "layout alone cannot acknowledge an empty video source")
        layer.bounds = originalRect
        TestScheduler.advance(0.05)
        check(restores == [true,true] && gallery.gallery.view.layoutPasses > 0, "all restore callbacks complete once after visible source geometry is ready")
        check(gallery.activations == 0 && gallery.gallery.galleryNode.normalAnimations == 0 && video.status.value?.timestamp == position, "restoration skips initial activation and stock gallery animations")
        check(gallery._isVisible == true && gallery.isCentral == true && video.pauses == pauses && video.plays == plays && video.seeks == seeks, "return restores central visibility without autoplay, pause or seek")
        check(gallery.gallery.presentationArguments as? Int == 7 && manager.sources.count == 2, "presentation arguments restored and gallery hidden source acquired before PiP stops")
        content.pictureInPictureController(av,restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: { restores.append($0) })
        check(restores == [true,true,true] && Window.shared.presentations == presentations+1, "late duplicate restore reuses already-ready interface")
        for _ in 0..<3 { gallery.pictureInPictureButtonPressed() }; TestScheduler.advance()
        check(gallery.gallery.dismissals == 0 && gallery.dismissals == 1, "button during final restore never dismisses the returned gallery")
        content.requestExpand()
        check(!av.isPictureInPictureActive && !video.withoutHierarchy && !video.nativePictureInPictureActive, "restored stop releases native playback ownership")
        check(manager.sources.count == 1 && gallery.context.sharedContext.mediaManager.currentPictureInPictureNode == nil, "gallery alone hides inline video after system ownership ends")
        check(video.canAttachContent && gallery.gallery.galleryNode.scrollView.isScrollEnabled && gallery.chat.pushed == 1, "restored gallery keeps source and unlocks gestures")
        av.completesStart = true
        av.isPictureInPicturePossible = false
        swipe(gallery)
        content.pictureInPictureControllerDidStopPictureInPicture(av)
        check(content.hasPendingPictureInPictureStart, "old duplicate stop never cancels a new waiting request")
        av.isPictureInPicturePossible = true; TestScheduler.advance()
        check(av.starts == 2 && gallery.dismissals == 2 && gallery.chat.toasts == 1, "first swipe works again after return and reports success only at DidStart")
        content.stop()
        check(gallery.chat.pushed == 0 && !video.canAttachContent, "closing second PiP releases detached gallery without changing visible chat")

        let (failed, failedContent, failedAV) = prepared()
        failedAV.completesStart = false; start(failed,failedAV)
        failedContent.pictureInPictureController(failedAV,failedToStartPictureInPictureWithError: NSError(domain: "test",code: 1))
        check(!failedContent.hasPendingPictureInPictureStart && failed.gallery.view.window != nil && failed.gallery.galleryNode.scrollView.isScrollEnabled && failed.context.sharedContext.mediaManager.galleryHiddenMediaManager.sources.count == 1, "failed start restores chrome/gestures and releases only native hidden source")
        check(failedAV.delegate == nil && failedAV.contentSource == nil && failedAV.observers.isEmpty, "interrupted controller detached before it can satisfy another request")
        failed.pictureInPictureButtonPressed(); TestScheduler.advance()
        let retryAV = AVPictureInPictureController.instances.last!
        check(retryAV !== failedAV && failedContent.hasPendingPictureInPictureStart, "retry gets fresh controller while retaining original player")
        failedContent.pictureInPictureControllerDidStartPictureInPicture(failedAV)
        failedContent.pictureInPictureController(failedAV,failedToStartPictureInPictureWithError: NSError(domain: "old",code: 2))
        check(retryAV.starts == 0 && failed.dismissals == 0 && failedContent.hasPendingPictureInPictureStart, "late old success/failure cannot complete or cancel a new transaction")
        retryAV.isPictureInPicturePossible = true; TestScheduler.advance()
        check(retryAV.starts == 1 && failed.dismissals == 1, "fresh request succeeds after failed controller without a second tap")
        failedContent.stop()

        let cold = GalleryHarness(); cold.isCentral = true; cold.videoNode!.ownsContentNode = false; cold.videoNode!.hasLayer = false
        check(cold.maybePerformActionForSwipeDismiss(), "first cold swipe retains intent without source ownership")
        let beforeLayer = AVPictureInPictureController.instances.count
        TestScheduler.advance(0.1)
        check(AVPictureInPictureController.instances.count == beforeLayer, "unowned missing layer never creates an AVKit source")
        cold.videoNode!.hasLayer = true; cold.videoNode!.ownsContentNode = true
        TestScheduler.advance(0.05)
        let coldAV = AVPictureInPictureController.instances.last!
        coldAV.isPictureInPicturePossible = true; TestScheduler.advance()
        check(coldAV.starts == 1 && coldAV.contentSource?.sampleBufferDisplayLayer === cold.videoNode!.layer && cold.dismissals == 1, "late layer enters from original cold swipe with same source")
        (cold.nativePictureInPictureContent as! NativePictureInPictureContentImpl).stop()

        for size in [CGSize(width: 1920,height: 1080),CGSize(width: 384,height: 832),CGSize(width: 720,height: 720)] {
            let (shaped, shapedContent, shapedAV) = prepared()
            shaped.videoNode!.layer.bounds = CGRect(origin: .zero,size: size)
            let sourceBounds = shaped.videoNode!.layer.bounds
            start(shaped,shapedAV)
            check(shaped.videoNode!.layer.bounds == sourceBounds && shapedAV.starts == 1, "landscape, portrait and square preserve complete source proportions")
            shapedContent.stop()
        }
        let (geometry, geometryContent, geometryAV) = prepared()
        geometry.videoNode!.layer.bounds = .zero
        start(geometry,geometryAV)
        check(geometryAV.starts == 0, "zero geometry never starts a rectangular placeholder")
        geometry.videoNode!.layer.bounds = CGRect(x: 0,y: 0,width: 1280,height: 720)
        geometry.videoNode!.layer.superlayer = nil; TestScheduler.advance(0.05)
        check(geometryAV.starts == 0, "detached layer never starts")
        geometry.videoNode!.layer.superlayer = geometry.videoNode!.frameContainer; geometry.videoNode!.view.window = nil; TestScheduler.advance(0.05)
        check(geometryAV.starts == 0, "detached view never starts")
        geometry.videoNode!.view.window = .shared; TestScheduler.advance(0.05)
        check(geometryAV.starts == 1, "original request starts when real source attaches")
        geometryContent.stop()

        let (firstFrame, firstFrameContent, firstFrameAV) = prepared()
        firstFrame.videoNode!.frameContainer.isHidden = true
        start(firstFrame,firstFrameAV)
        check(firstFrameAV.starts == 0 && firstFrameContent.hasPendingPictureInPictureStart, "AVKit ready plus thumbnail never starts PiP before a video frame")
        firstFrame.videoNode!.frameContainer.isHidden = false; TestScheduler.advance(0.05)
        check(firstFrameAV.starts == 1 && firstFrameAV.contentSource?.sampleBufferDisplayLayer === firstFrame.videoNode!.layer, "first decoded-frame visibility completes original request with existing video layer")
        firstFrameContent.stop()

        let (abandoned, abandonedContent, abandonedAV) = prepared()
        start(abandoned,abandonedAV)
        var failedRestore: [Bool] = []
        abandonedContent.pictureInPictureController(abandonedAV,restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: { failedRestore.append($0) })
        TestScheduler.advance(5.1)
        check(failedRestore == [false] && abandonedAV.isPictureInPictureActive && abandoned.videoNode!.withoutHierarchy, "restore timeout never discards still-playing system PiP")
        Window.shared.finishPresentation()
        check(abandoned.gallery.view.window == nil && abandoned.activations == 0 && failedRestore == [false], "late appearance after timeout is dismissed without replay or false completion")
        abandonedContent.requestExpand(); TestScheduler.advance()
        Window.shared.finishPresentation(); TestScheduler.advance(0.05)
        check(!abandonedAV.isPictureInPictureActive && abandoned.gallery.view.window != nil, "programmatic expand restores ready UI before stopping PiP")

        let (noWindow, noWindowContent, noWindowAV) = prepared()
        start(noWindow,noWindowAV); noWindow.navigation.currentWindow = nil
        var noWindowRestored: Bool?
        noWindowContent.pictureInPictureController(noWindowAV,restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: { noWindowRestored = $0 })
        check(noWindowRestored == false && noWindowAV.isPictureInPictureActive, "missing presentation window rejects restore and retains active PiP")
        noWindowContent.stop()

        let (stopping, stoppingContent, stoppingAV) = prepared()
        start(stopping,stoppingAV)
        stoppingContent.pictureInPictureControllerWillStopPictureInPicture(stoppingAV)
        stoppingAV.isPictureInPictureActive = false
        stopping.visibilityUpdated(isVisible: false)
        check(stoppingContent.keepsVideoAttached && stoppingContent.hasPendingPictureInPictureStart && stopping.videoNode!.canAttachContent, "WillStop retains ownership even if AVKit active flag has changed")
        var stopRestore: Bool?
        stoppingContent.pictureInPictureController(stoppingAV,restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: { stopRestore = $0 })
        TestScheduler.advance(); Window.shared.finishPresentation(); TestScheduler.advance(0.05)
        check(stopRestore == true && stopping.gallery.view.window != nil, "system return after WillStop is allowed until DidStop")
        stoppingContent.pictureInPictureControllerDidStopPictureInPicture(stoppingAV)
        check(!stoppingContent.keepsVideoAttached && !stopping.videoNode!.withoutHierarchy && stopping.videoNode!.canAttachContent, "DidStop releases ownership only after target is ready")

        let (interruptedRestore, interruptedContent, interruptedAV) = prepared()
        start(interruptedRestore,interruptedAV)
        var interruptedResults: [Bool] = []
        interruptedContent.pictureInPictureController(interruptedAV,restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: { interruptedResults.append($0) })
        TestScheduler.advance(); interruptedContent.stop()
        check(interruptedResults == [false] && !interruptedRestore.videoNode!.withoutHierarchy, "closing during pending return resolves restore once and releases native ownership")
        Window.shared.finishPresentation()
        check(interruptedRestore.gallery.view.window == nil && interruptedRestore.activations == 0 && interruptedResults == [false], "late cancelled return cannot reopen or restart gallery")

        let (layoutRace, layoutContent, layoutAV) = prepared()
        start(layoutRace,layoutAV)
        var layoutResults: [Bool] = []
        layoutContent.pictureInPictureController(layoutAV,restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: { layoutResults.append($0) })
        TestScheduler.advance()
        let raceBounds = layoutRace.videoNode!.layer.bounds
        layoutRace.gallery.view.layoutAction = { [weak layoutRace] in
            guard let layoutRace else { return }
            layoutRace.gallery.view.layoutAction = nil
            layoutRace.videoNode!.layer.bounds = .zero
            layoutRace.gallery.tryCompleteNativePictureInPictureRestore()
        }
        Window.shared.finishPresentation()
        check(layoutResults.isEmpty && layoutRace.gallery.view.layoutPasses == 1, "layout reentrancy cannot acknowledge a rect invalidated during layout")
        layoutRace.videoNode!.layer.bounds = raceBounds; TestScheduler.advance(0.05)
        check(layoutResults == [true], "restore rechecks actual source after layout and resolves once")
        layoutContent.stop()

        let (cancelled, cancelledContent, cancelledAV) = prepared()
        swipe(cancelled); cancelled.visibilityUpdated(isVisible: false)
        cancelledAV.isPictureInPicturePossible = true; TestScheduler.advance(5.1)
        check(cancelledAV.starts == 0 && !cancelledContent.hasPendingPictureInPictureStart && !cancelled.gallery.galleryNode.nativePictureInPictureTransitionInProgress, "external disappearance cancels pending gesture and old readiness")
        let (leaving, leavingContent, leavingAV) = prepared()
        leavingAV.completesStart = false; start(leaving,leavingAV)
        leaving.centralityUpdated(isCentral: false)
        check(leavingAV.stops == 1 && leavingAV.delegate == nil && !leavingContent.hasPendingPictureInPictureStart && !leaving.videoNode!.withoutHierarchy, "leaving during native animation cancels controller and ownership")

        let (automatic, automaticContent, automaticAV) = prepared()
        automaticAV.isPictureInPicturePossible = true; automaticAV.startPictureInPicture()
        check(automatic.dismissals == 1 && automatic.videoNode!.withoutHierarchy && automatic.gallery.galleryNode.nativePictureInPictureTransitionInProgress, "system automatic entry shares visual transaction")
        automaticContent.stop()
        UIAccessibility.isReduceMotionEnabled = true
        let (reduced, reducedContent, reducedAV) = prepared()
        start(reduced,reducedAV)
        check(UIView.durations.last == 0 && reduced.videoNode!.layer.animations.isEmpty, "Reduce Motion suppresses app chrome animation and never animates live layer")
        reducedContent.stop(); UIAccessibility.isReduceMotionEnabled = false

        for key in ["ios_killswitch_disable_native_pip_v2","ios_killswitch_disable_swipe_pip","video_swipe_up_to_close"] {
            let blocked = GalleryHarness(); blocked.isCentral = true
            blocked.context.currentAppConfiguration.value.data = [key: true]
            check(!blocked.maybePerformActionForSwipeDismiss() && !blocked.gallery.galleryNode.nativePictureInPictureTransitionInProgress, "server gate remains stock: " + key)
        }
        let off = GalleryHarness(); off.isCentral = true
        NagramiXTabSettings.videoPiPSwipeEnabled = false
        check(!off.maybePerformActionForSwipeDismiss() && off.nativePictureInPictureContent == nil, "saved swipe OFF remains off")
        NagramiXTabSettings.videoPiPSwipeEnabled = true
        check(!off.maybePerformActionForSwipeDownDismiss(), "swipe down remains normal close")
        let ad = GalleryHarness(); ad.isCentral = true; ad.item!.contentInfo = .message(Message(adAttribute: 1),0)
        check(!ad.maybePerformActionForSwipeDismiss(), "ad gate retained")
        let animated = GalleryHarness(); animated.isCentral = true; (animated.item!.content as! NativeVideoContent).fileReference.media.isAnimated = true
        check(!animated.maybePerformActionForSwipeDismiss(), "animated file gate retained")
        AVPictureInPictureController.supported = false
        let unsupported = GalleryHarness(); unsupported.isCentral = true
        check(!unsupported.maybePerformActionForSwipeDismiss(), "unsupported OS retains normal dismiss")
        AVPictureInPictureController.supported = true

        var released: GalleryHarness? = GalleryHarness()
        let weakGallery = WeakGalleryProbe(released)
        released!.centralityUpdated(isCentral: true); TestScheduler.advance()
        let releaseAV = AVPictureInPictureController.instances.last!, releaseNode = released!.videoNode!
        released!.pictureInPictureButtonPressed(); TestScheduler.advance()
        released = nil; TestScheduler.advance(6)
        check(weakGallery.value == nil && releaseAV.delegate == nil && releaseAV.contentSource == nil && releaseAV.observers.isEmpty && releaseNode.status.handlers.isEmpty, "waiting transition and subscriptions do not retain released gallery")
        print("PASS: \(count) PiP visual transition checks; UIKit/AVKit rendering are boundaries")
    }
}
