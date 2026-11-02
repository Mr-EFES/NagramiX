    private func setupNativePictureInPicture() {
        guard self.nagramiXCanUseSystemPiP, let item = self.item, let node = self.videoNode else { return }
        if let previous = self.nativePictureInPictureContent as? NagramiXSystemPiPController {
            if previous.nagramiXMatchesSource(node, requireLayer: false) { return }
            guard !previous.nagramiXHasPiPRequest else { return }
            self.nativePictureInPictureContent = nil
        }
        var hiddenMedia: (MessageId, Media)?
        if case let .message(message, _) = item.contentInfo {
            for media in message.effectiveMedia {
                if let file = media as? TelegramMediaFile, file.isVideo { hiddenMedia = (message.id, file); break }
            }
        }
        var restoring = false
        let content = NagramiXSystemPiPController(context: self.context, videoNode: node, hiddenMedia: hiddenMedia,
            transfer: { [weak self, weak node] content in
                guard let self, let node, self.videoNode === node, self.nativePictureInPictureContent === content,
                      let controller = self.galleryController(), let navigation = self.baseNavigationController() else { return false }
                let owner = self.context.sharedContext.mediaManager.currentPictureInPictureNode
                guard owner == nil || owner === self else { return false }
                self.activePictureInPictureController = controller
                self.activePictureInPictureNavigationController = navigation
                self.context.sharedContext.mediaManager.currentPictureInPictureNode = self
                node.canAttachContent = true
                self.beginCustomDismiss(.pip)
                controller.view.alpha = 0.0
                controller.view.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.2, completion: { [weak self, weak content] _ in
                    guard let self, let content, self.nativePictureInPictureContent === content, !restoring else { return }
                    self.completeCustomDismiss(true)
                })
                return true
            }, restore: { [weak self, weak node] completion in
                guard let self, let node, self.videoNode === node,
                      let controller = self.activePictureInPictureController,
                      let navigation = self.activePictureInPictureNavigationController,
                      let window = navigation.currentWindow else { completion(false); return }
                restoring = true
                (controller.displayNode as? GalleryControllerNode)?.nagramiXPreparePiPRestoration()
                node.canAttachContent = true
                controller.view.layer.removeAnimation(forKey: "opacity")
                controller.view.alpha = 1.0
                self.updateControlsVisibility(false)
                // Expand may arrive before the inline fade/dismiss completed.
                // If the gallery is still present, presenting it again duplicates
                // the controller. Reuse it and let AVKit animate back to its layer.
                if controller.view.window != nil {
                    completion(true)
                } else {
                    let arguments = controller.presentationArguments
                    controller.presentationArguments = nil
                    window.present(controller, on: .root, blockInteraction: false, completion: { completion(true) })
                    controller.presentationArguments = arguments
                }
            }, ended: { [weak self, weak node] content, restored in
                guard let self, self.nativePictureInPictureContent === content else { return }
                if self.context.sharedContext.mediaManager.currentPictureInPictureNode === self {
                    self.context.sharedContext.mediaManager.currentPictureInPictureNode = nil
                }
                if !restored || self.isCentral == false {
                    // A newer gallery can own the same shared decoder already.
                    // Stopping this retired PiP must not pause that new owner.
                    if node?.ownsContentNode == true { node?.pause() }
                    if self._isVisible == false || self.view.window == nil { node?.canAttachContent = false }
                }
                if !restored {
                    self.context.engine.accountData.addAppLogEvent(type: "pip_close_btn")
                }
                self.activePictureInPictureController = nil
                self.activePictureInPictureNavigationController = nil
                self.updateDisplayPlaceholder()
            })
        self.nativePictureInPictureContent = content
    }

    @objc func pictureInPictureButtonPressed() {
        if self.nagramiXPiPSwipeTransitionPending || self.nagramiXDirectionalPiPSourceRequest != nil { return }
        if let content = self.nativePictureInPictureContent as? NagramiXSystemPiPController, content.nagramiXHasPiPRequest { return }
        guard let source = self.videoNode else { self.nagramiXPresentPiPFailure(); return }
        let accepted = self.nagramiXStartSystemPiP(requiresSwipeSetting: false, completion: { [weak self, weak source] started in
            guard let self, let source, self.videoNode === source, !started, !self.nagramiXPiPSourceWasCancelled else { return }
            self.nagramiXPresentPiPFailure()
        })
        if !accepted { self.nagramiXPresentPiPFailure() }
    }

    private func nagramiXPresentPiPFailure() {
        guard self.isCentral == true, UIApplication.shared.applicationState == .active,
              let controller = self.galleryController(), controller.view.window != nil,
              (controller.displayNode as? GalleryControllerNode)?.nagramiXAllowsSystemPiPTransition == true else { return }
        controller.present(textAlertController(context: self.context, title: self.presentationData.strings.nagramiXPiPTitle, text: self.presentationData.strings.nagramiXPiPUnavailable, actions: [TextAlertAction(type: .defaultAction, title: self.presentationData.strings.Common_OK, action: {})]), in: .window(.root))
    }
