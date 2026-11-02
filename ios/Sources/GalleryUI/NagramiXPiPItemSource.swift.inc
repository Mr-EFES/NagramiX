    override var nagramiXPiPSwipeView: UIView { return self.nagramiXPiPSurface.view }

    override func nagramiXPiPSourceFrame(in view: UIView) -> CGRect {
        guard let node = self.videoNode else { return .zero }
        return node.view.convert(node.view.bounds, to: view)
    }

    override var nagramiXPiPNativeTransitionInFlight: Bool {
        return (self.nativePictureInPictureContent as? NagramiXSystemPiPController)?.nagramiXNativeStartInFlight == true
    }

    private var nagramiXPiPRequestRequiresSwipeSetting = false
    private var nagramiXPiPSourceWasCancelled = false

    override var nagramiXBlocksPiPSourcePan: Bool {
        guard NagramiXTabSettings.videoPiPSwipeEnabled else { return false }
        return self.pictureInPictureNode != nil || self.nagramiXPiPSwipeTransitionPending
            || self.nagramiXDirectionalPiPSourceRequest != nil
            || (self.nativePictureInPictureContent as? NagramiXSystemPiPController)?.nagramiXHasPiPRequest == true
    }

    override var nagramiXCanBeginDirectionalPiPSwipe: Bool {
        return self.nagramiXCanUseDirectionalPiP && self.pictureInPictureNode == nil
            && self.nagramiXDirectionalPiPSourceRequest == nil
            && (self.nativePictureInPictureContent as? NagramiXSystemPiPController)?.nagramiXHasPiPRequest != true
    }

    override func nagramiXStartDirectionalPiP(completion: @escaping (Bool) -> Void) -> Bool {
        return self.nagramiXStartSystemPiP(requiresSwipeSetting: true, completion: completion)
    }

    private var nagramiXCanUseSystemPiP: Bool {
        guard self.isCentral == true, self.hasPictureInPicture, !self.isLivePhoto,
              let item = self.item, !item.isSecret, self.videoNode != nil,
              self.baseNavigationController() != nil,
              AVPictureInPictureController.isPictureInPictureSupported() else { return false }
        if let data = self.context.currentAppConfiguration.with({ $0 }).data,
           data["ios_killswitch_disable_native_pip_v2"] != nil { return false }
        if case let .message(message, _) = item.contentInfo, message.adAttribute != nil { return false }
        if let content = item.content as? NativeVideoContent, content.fileReference.media.isAnimated { return false }
        if let content = item.content as? HLSVideoContent, content.fileReference.media.isAnimated { return false }
        return true
    }

    private func nagramiXStartSystemPiP(requiresSwipeSetting: Bool, completion: @escaping (Bool) -> Void) -> Bool {
        guard self.nagramiXCanUseSystemPiP,
              !requiresSwipeSetting || self.nagramiXCanBeginDirectionalPiPSwipe,
              self.nagramiXDirectionalPiPSourceRequest == nil,
              UIApplication.shared.applicationState == .active,
              (self.galleryController()?.displayNode as? GalleryControllerNode)?.nagramiXAllowsSystemPiPTransition == true,
              self.galleryController()?.view.window != nil,
              let node = self.videoNode else { return false }
        self.setupNativePictureInPicture()
        guard let content = self.nativePictureInPictureContent as? NagramiXSystemPiPController,
              content.nagramiXMatchesSource(node, requireLayer: false), !content.nagramiXHasPiPRequest else { return false }
        let request = UUID()
        self.nagramiXPiPSourceWasCancelled = false
        self.nagramiXDirectionalPiPSourceRequest = request
        self.nagramiXPiPRequestRequiresSwipeSetting = requiresSwipeSetting
        let previous = self.context.sharedContext.mediaManager.currentPictureInPictureNode
        var stoppedPrevious = false
        let accepted = content.start(acquirePrevious: { [weak self] in
            guard let self else { return false }
            guard let owner = self.context.sharedContext.mediaManager.currentPictureInPictureNode else { return true }
            guard owner === previous, owner !== self, let item = owner as? UniversalVideoGalleryItemNode,
                  let old = item.nativePictureInPictureContent as? NagramiXSystemPiPController else { return false }
            if !old.nagramiXHasPiPRequest {
                self.context.sharedContext.mediaManager.currentPictureInPictureNode = nil
                item.activePictureInPictureController = nil
                item.activePictureInPictureNavigationController = nil
                return true
            }
            if !stoppedPrevious { stoppedPrevious = true; old.stop() }
            return false
        }, validate: { [weak self, weak content, weak node] in
            guard let self, let content, let node, self.videoNode === node,
                  self.nativePictureInPictureContent === content,
                  self.nagramiXDirectionalPiPSourceRequest == request,
                  (self.galleryController()?.displayNode as? GalleryControllerNode)?.nagramiXAllowsSystemPiPTransition == true,
                  self.nagramiXCanUseSystemPiP,
                  !requiresSwipeSetting || NagramiXTabSettings.videoPiPSwipeEnabled else { return false }
            let owner = self.context.sharedContext.mediaManager.currentPictureInPictureNode
            guard owner == nil || owner === self || owner === previous else { return false }
            return content.nagramiXNativeStartInFlight || (UIApplication.shared.applicationState == .active
                && self.galleryController()?.view.window != nil)
        }, completion: { [weak self] started in
            guard let self, self.nagramiXDirectionalPiPSourceRequest == request else { return }
            self.nagramiXDirectionalPiPSourceRequest = nil
            NSLog("NagramiX PiP v3: result=%@", started ? "active" : "inline")
            completion(started)
        })
        if !accepted { self.nagramiXDirectionalPiPSourceRequest = nil }
        return accepted
    }

    override func prepareForPictureInPictureSwipe() -> Bool {
        guard self.nagramiXCanBeginDirectionalPiPSwipe else { return false }
        self.setupNativePictureInPicture()
        return self.nativePictureInPictureContent != nil
    }

    override func cancelPictureInPictureSwipePreparation() {
        guard let content = self.nativePictureInPictureContent as? NagramiXSystemPiPController else { return }
        if self.nagramiXDirectionalPiPSourceRequest != nil, !content.nagramiXNativeStartInFlight {
            self.nagramiXPiPSourceWasCancelled = true
        }
        content.nagramiXCancelDirectionalPiP()
    }
