    override func centralityUpdated(isCentral: Bool) {
        super.centralityUpdated(isCentral: isCentral)
        
        if self.isCentral != isCentral {
            self.isCentral = isCentral
            
            if let videoNode = self.videoNode {
                if isCentral {
                    var isAnimated = false
                    if let item = self.item, let content = item.content as? NativeVideoContent {
                        isAnimated = content.fileReference.media.isAnimated
                    } else if let item = self.item, let content = item.content as? HLSVideoContent {
                        isAnimated = content.fileReference.media.isAnimated
                    }
                    
                    self.hideStatusNodeUntilCentrality = false
                    self.statusButtonNode.isHidden = self.hideStatusNodeUntilCentrality || self.statusNodeShouldBeHidden

                    if videoNode.ownsContentNode {
                        if isAnimated {
                            videoNode.seek(0.0)
                            videoNode.play()
                        } else if self.shouldAutoplayOnCentrality()  {
                            self.initiallyActivated = true
                            if self.playLivePhotoAutoplayIfNeeded(videoNode: videoNode) {
                            } else {
                                videoNode.playOnceWithSound(playAndRecord: false, actionAtEnd: self.actionAtEnd)
                            }

                            videoNode.setBaseRate(self.playbackRate ?? 1.0)
                        }
                    } else {
                        if isAnimated {
                            self.playOnContentOwnership = true
                        } else if self.shouldAutoplayOnCentrality()  {
                            self.playOnContentOwnership = true
                        }
                    }
                } else {
                    self.resetLivePhotoPlayback()
                    self.isPlayingPromise.set(false)
                    self.isPlaying = false
                    
                    self.dismissOnOrientationChange = false
                    if videoNode.ownsContentNode {
                        videoNode.pause()
                    }
                }
            }
            
            if #available(iOS 15.0, *) {
                if let nativePictureInPictureContent = self.nativePictureInPictureContent as? NativePictureInPictureContentImpl {
                    nativePictureInPictureContent.updateIsCentral(isCentral: isCentral)
                }
            }
        }
    }
    
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
    
