override func visibilityUpdated(isVisible: Bool) {
        super.visibilityUpdated(isVisible: isVisible)
        
        if self._isVisible != isVisible {
            let hadPreviousValue = self._isVisible != nil
            self._isVisible = isVisible
            
            if let item = self.item, let videoNode = self.videoNode {
                if hadPreviousValue {
                    videoNode.canAttachContent = isVisible
                    if isVisible {
                        if let currentPictureInPictureNode = self.context.sharedContext.mediaManager.currentPictureInPictureNode as? UniversalVideoGalleryItemNode, let currentItem = currentPictureInPictureNode.item, case let .message(currentMessage, _) = currentItem.contentInfo, case let .message(message, _) = item.contentInfo, currentMessage.id == message.id {
                            self.skipInitialPause = true
                        }
                        
                        if self.skipInitialPause {
                            self.skipInitialPause = false
                        } else {
                            self.resetLivePhotoPlayback()
                            self.ignorePauseStatus = true
                            videoNode.pause()
                            videoNode.seek(0.0)
                        }
                    } else {
                        self.resetLivePhotoPlayback()
                        if let status = self.playerStatusValue {
                            self.maybeStorePlaybackStatus(status: status)
                        }
                        if !self.isLivePhoto {
                            videoNode.continuePlayingWithoutSound()
                        }
                    }
                    self.updateDisplayPlaceholder()
                } else if !item.fromPlayingVideo {
                    videoNode.canAttachContent = isVisible
                    self.updateDisplayPlaceholder()
                }
                if self.shouldAutoplayOnCentrality() {
                    self.hideStatusNodeUntilCentrality = true
                    self.statusButtonNode.isHidden = true
                }
            }
        }
    }
