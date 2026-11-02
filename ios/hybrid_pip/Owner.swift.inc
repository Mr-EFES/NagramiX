    private weak var nagramiXHybridMini: NagramiXHybridMiniNode?
    private var nagramiXHybridRetiring: NagramiXHybridMiniNode?
    private var nagramiXHybridClosing = false
    private var nagramiXHybridExpandPending = false
    private var nagramiXHybridReturning = false
    private let nagramiXHybridLease = UUID()
    private var nagramiXHybridGeneration = UUID()

    private func nagramiXStartHybridPiP(completion: @escaping (Bool) -> Void) -> Bool {
        guard self.nagramiXCanBeginDirectionalPiPSwipe, let video = self.videoNode,
              let item = self.item, let gallery = self.galleryController(),
              let navigation = self.baseNavigationController(), video.ownsContentNode else { return false }
        let manager = self.context.sharedContext.mediaManager
        if let previous = manager.currentPictureInPictureNode as? UniversalVideoGalleryItemNode,
           previous !== self, previous.nagramiXHybridMini != nil {
            previous.nagramiXCloseHybrid(remove: true)
        }
        guard manager.currentPictureInPictureNode == nil || manager.currentPictureInPictureNode === self else { return false }
        guard self.nagramiXHybridRetiring == nil else { return false }
        self.nagramiXHybridClosing = false
        self.nagramiXHybridExpandPending = false
        self.nagramiXHybridReturning = false
        let generation = UUID()
        self.nagramiXHybridGeneration = generation
        self.activePictureInPictureController = gallery
        self.activePictureInPictureNavigationController = navigation
        video.setNagramiXBackgroundPlayback(id: self.nagramiXHybridLease, active: true)
        let mini = NagramiXHybridMiniNode(owner: self, video: video, dimensions: item.content.dimensions,
            half: self.nagramiXRequestedPiPHalf,
            expand: { [weak self] in guard self?.nagramiXHybridGeneration == generation else { return }; self?.nagramiXExpandHybrid() },
            close: { [weak self] in guard self?.nagramiXHybridGeneration == generation else { return }; self?.nagramiXCloseHybrid(remove: true) },
            removed: { [weak self] in guard self?.nagramiXHybridGeneration == generation else { return }; self?.nagramiXCloseHybrid(remove: false) },
            background: { [weak self] in guard self?.nagramiXHybridGeneration == generation else { return }; self?.nagramiXHybridBackground() },
            foreground: { [weak self] in guard self?.nagramiXHybridGeneration == generation else { return }; self?.nagramiXHybridForeground() })
        self.nagramiXHybridMini = mini
        manager.currentPictureInPictureNode = self
        video.canAttachContent = true
        self.nagramiXUpdateBackgroundVideoPlayback()
        manager.setOverlayVideoNode(mini)
        self.beginCustomDismiss(.pip)
        completion(true)
        self.completeCustomDismiss(true)
        return true
    }
    private func nagramiXHybridBackground() {
        guard self.nagramiXHybridMini != nil, !self.nagramiXHybridClosing else { return }
        if let native = self.nativePictureInPictureContent as? NagramiXSystemPiPController, native.nagramiXHasPiPRequest { return }
        self.nagramiXHybridReturning = false
        _ = self.nagramiXStartSystemPiP(requiresSwipeSetting: false, completion: { [weak self] started in
            guard let self else { return }
            if !started {
                self.nagramiXHybridMini?.alpha = 1
                if self.nagramiXHybridClosing { self.nagramiXFinishHybridClose() }
                else if self.nagramiXHybridExpandPending {
                    self.nagramiXHybridExpandPending = false
                    self.nagramiXExpandHybrid()
                } else if self.nagramiXHybridReturning {
                    self.nagramiXHybridReturning = false
                    self.nagramiXScheduleHybridBackgroundRetry()
                }
            }
        })
    }
    private func nagramiXScheduleHybridBackgroundRetry() {
        let generation = self.nagramiXHybridGeneration
        Queue.mainQueue().async { [weak self] in
            guard let self, self.nagramiXHybridGeneration == generation,
                  UIApplication.shared.applicationState != .active else { return }
            self.nagramiXHybridBackground()
        }
    }
    private func nagramiXHybridForeground() {
        guard self.nagramiXHybridMini != nil, !self.nagramiXHybridClosing else { return }
        self.nagramiXHybridReturning = true
        if let native = self.nativePictureInPictureContent as? NagramiXSystemPiPController, native.nagramiXHasPiPRequest {
            native.stop()
        } else {
            self.nagramiXHybridMini?.alpha = 1
            self.nagramiXHybridReturning = false
        }
    }
    private func nagramiXCloseHybrid(remove: Bool) {
        guard let mini = self.nagramiXHybridMini, !self.nagramiXHybridClosing else { return }
        self.nagramiXHybridClosing = true
        self.nagramiXHybridRetiring = mini
        if remove {
            mini.removing = true
            if self.context.sharedContext.mediaManager.hasOverlayVideoNode(mini) {
                self.context.sharedContext.mediaManager.setOverlayVideoNode(nil)
            }
        }
        if let native = self.nativePictureInPictureContent as? NagramiXSystemPiPController, native.nagramiXHasPiPRequest {
            native.stop()
        } else { self.nagramiXFinishHybridClose() }
    }
    private func nagramiXFinishHybridClose() {
        self.nagramiXHybridGeneration = UUID()
        self.nagramiXHybridMini = nil
        self.videoNode?.setNagramiXBackgroundPlayback(id: self.nagramiXHybridLease, active: false)
        if self.videoNode?.ownsContentNode == true { self.videoNode?.pause() }
        self.videoNode?.canAttachContent = false
        let manager = self.context.sharedContext.mediaManager
        if manager.currentPictureInPictureNode === self { manager.currentPictureInPictureNode = nil }
        self.nativePictureInPictureContent = nil
        self.activePictureInPictureController = nil
        self.activePictureInPictureNavigationController = nil
        self.nagramiXUpdateBackgroundVideoPlayback()
        self.nagramiXHybridRetiring = nil
    }
    private func nagramiXExpandHybrid() {
        guard let mini = self.nagramiXHybridMini, !self.nagramiXHybridClosing,
              let controller = self.activePictureInPictureController,
              let navigation = self.activePictureInPictureNavigationController,
              let window = navigation.currentWindow else { return }
        if let native = self.nativePictureInPictureContent as? NagramiXSystemPiPController, native.nagramiXHasPiPRequest {
            self.nagramiXHybridExpandPending = true
            self.nagramiXHybridReturning = true
            native.stop()
            return
        }
        guard mini.restoreVideo() else { return }
        self.nagramiXHybridGeneration = UUID()
        mini.removing = true
        self.nagramiXHybridMini = nil
        if self.context.sharedContext.mediaManager.hasOverlayVideoNode(mini) {
            self.context.sharedContext.mediaManager.setOverlayVideoNode(nil)
        }
        self.videoNode?.setNagramiXBackgroundPlayback(id: self.nagramiXHybridLease, active: false)
        self.nagramiXPiPSurface.view.transform = .identity
        self.nagramiXPiPSwipeTransitionPending = false
        self.skipInitialPause = true
        self.nativePictureInPictureContent = nil
        (controller.displayNode as? GalleryControllerNode)?.nagramiXPreparePiPRestoration()
        controller.view.alpha = 1
        let arguments = controller.presentationArguments
        controller.presentationArguments = nil
        window.present(controller, on: .root, blockInteraction: false, completion: { [weak self] in
            guard let self else { return }
            if self.context.sharedContext.mediaManager.currentPictureInPictureNode === self {
                self.context.sharedContext.mediaManager.currentPictureInPictureNode = nil
            }
            self.activePictureInPictureController = nil
            self.activePictureInPictureNavigationController = nil
            self.nagramiXUpdateBackgroundVideoPlayback()
        })
        controller.presentationArguments = arguments
    }
