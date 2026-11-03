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
                if isCentral && self.nativePictureInPictureContent == nil {
                    self.setupNativePictureInPicture()
                }
                if let nativePictureInPictureContent = self.nativePictureInPictureContent as? NativePictureInPictureContentImpl {
                    nativePictureInPictureContent.updateIsCentral(isCentral: isCentral)
                }
            }
        }
    }
