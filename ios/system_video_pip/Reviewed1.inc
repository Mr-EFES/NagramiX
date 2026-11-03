private func setupNativePictureInPicture() {
        guard self.nativePictureInPictureContent == nil, let item = self.item, let videoNode = self.videoNode, videoNode.ownsContentNode else {
            return
        }
        
        if videoNode.getVideoLayer() == nil {
            return
        }
        
        var useNative = true
        if let data = self.context.currentAppConfiguration.with({ $0 }).data, let _ = data["ios_killswitch_disable_native_pip_v2"] {
            useNative = false
        }
        var isAd = false
        if let contentInfo = item.contentInfo {
            switch contentInfo {
            case let .message(message, mediaSubject):
                isAd = message.adAttribute != nil
                self.footerContentNode.setMessage(message, mediaSubject: mediaSubject, displayInfo: !item.displayInfoOnTop, peerIsCopyProtected: item.peerIsCopyProtected, displayPictureInPictureButton: self.hasPictureInPicture, settingsButtonState: self.settingsButtonState, displayStickersButton: self.displayStickersButton)
            case let .webPage(webPage, media, _):
                self.footerContentNode.setWebPage(webPage, media: media)
            }
        }
        if isAd {
            useNative = false
        }
        if let content = item.content as? NativeVideoContent {
            if content.fileReference.media.isAnimated {
                useNative = false
            }
        }
        if !useNative {
            return
        }
        
        var hiddenMedia: (MessageId, Media)? = nil
        switch item.contentInfo {
        case let .message(message, _):
            for media in message.effectiveMedia {
                if let media = media as? TelegramMediaImage {
                    hiddenMedia = (message.id, media)
                } else if let media = media as? TelegramMediaFile, media.isVideo {
                    hiddenMedia = (message.id, media)
                }
            }
        default:
            break
        }
        
        if #available(iOS 15.0, *) {
            var didExpand = false
            let content = NativePictureInPictureContentImpl(context: self.context, mediaManager: self.context.sharedContext.mediaManager, accountId: self.context.account.id, hiddenMedia: hiddenMedia, videoNode: videoNode, canSkip: true, willBegin: { [weak self] content in
                guard let self, let controller = self.galleryController(), let navigationController = self.baseNavigationController() else {
                    return
                }
                
                self.activePictureInPictureNavigationController = navigationController
                self.activePictureInPictureController = controller
                self.context.sharedContext.mediaManager.currentPictureInPictureNode = self
                
                self.beginCustomDismiss(.pip)
                controller.view.alpha = 0.0
                controller.view.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.2, completion: { [weak self] _ in
                    self?.completeCustomDismiss(true)
                })
                if let videoNode = self.videoNode {
                    videoNode.setNativePictureInPictureIsActive(false)
                }
                didExpand = false
            }, didBegin: { [weak self] _ in
                guard let self else {
                    return
                }
                let _ = self
            }, didEnd: { [weak self] _ in
                guard let self else {
                    return
                }
                
                if self.context.sharedContext.mediaManager.currentPictureInPictureNode === self {
                    self.context.sharedContext.mediaManager.currentPictureInPictureNode = nil
                }
                
                if let videoNode = self.videoNode {
                    videoNode.setNativePictureInPictureIsActive(false)
                }
                
                if !didExpand {
                    self.activePictureInPictureController = nil
                    self.activePictureInPictureNavigationController = nil
                    
                    self.context.engine.accountData.addAppLogEvent(type: "pip_close_btn")
                }
            }, expand: { [weak self] completion in
                didExpand = true
                
                guard let self, let activePictureInPictureController = self.activePictureInPictureController, let activePictureInPictureNavigationController = self.activePictureInPictureNavigationController else {
                    completion()
                    return
                }
                
                self.activePictureInPictureController = nil
                self.activePictureInPictureNavigationController = nil
                
                let previousPresentationArguments = activePictureInPictureController.presentationArguments
                activePictureInPictureController.presentationArguments = nil
                activePictureInPictureNavigationController.currentWindow?.present(activePictureInPictureController, on: .root, blockInteraction: false, completion: {
                })
                activePictureInPictureController.presentationArguments = previousPresentationArguments
                self.updateControlsVisibility(false)
                
                activePictureInPictureController.view.alpha = 1.0
                activePictureInPictureController.view.layer.animateAlpha(from: 0.0, to: 1.0, duration: 0.35, completion: { _ in
                })
                
                completion()
            })
            
            content.updateIsCentral(isCentral: self.isCentral == true)
            self.nativePictureInPictureContent = content
        }
    }
