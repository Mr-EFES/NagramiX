    private func expandIntoCustomPiP() {
        if let item = self.item, let videoNode = self.videoNode, let customUnembedWhenPortrait = customUnembedWhenPortrait {
            self.customUnembedWhenPortrait = nil
            videoNode.setContinuePlayingWithoutSoundOnLostAudioSession(false)
            
            let context = self.context
            let baseNavigationController = self.baseNavigationController()
            let mediaManager = self.context.sharedContext.mediaManager
            var expandImpl: (() -> Void)?
            let overlayNode = OverlayUniversalVideoNode(context: self.context, audioSession: context.sharedContext.mediaManager.audioSession, manager: context.sharedContext.mediaManager.universalVideoManager, content: item.content, expand: {
                expandImpl?()
            }, close: { [weak mediaManager] in
                mediaManager?.setOverlayVideoNode(nil)
            })

            let playbackRate = self.playbackRate

            expandImpl = { [weak overlayNode] in
                guard let contentInfo = item.contentInfo, let overlayNode = overlayNode else {
                    return
                }
                
                switch contentInfo {
                    case let .message(message, _):
                        let gallery = GalleryController(context: context, source: .peerMessagesAtId(messageId: message.id, chatLocation: .peer(id: message.id.peerId), customTag: nil, chatLocationContextHolder: Atomic<ChatLocationContextHolder?>(value: nil)), playbackRate: playbackRate, replaceRootController: { controller, ready in
                            if let baseNavigationController = baseNavigationController {
                                baseNavigationController.replaceTopController(controller, animated: false, ready: ready)
                            }
                        }, baseNavigationController: baseNavigationController)
                        gallery.temporaryDoNotWaitForReady = true
                        
                        baseNavigationController?.view.endEditing(true)
                        
                        (baseNavigationController?.topViewController as? ViewController)?.present(gallery, in: .window(.root), with: GalleryControllerPresentationArguments(transitionArguments: { [weak overlayNode, context] id, media in
                            if let overlayNode = overlayNode, let overlaySupernode = overlayNode.supernode {
                                return GalleryTransitionArguments(transitionNode: (overlayNode, overlayNode.bounds, { [weak overlayNode] in
                                    return (overlayNode?.view.snapshotContentTree(), nil)
                                }), addToTransitionSurface: { [weak context, weak overlaySupernode, weak overlayNode] view in
                                    guard let context = context, let overlayNode = overlayNode else {
                                        return
                                    }
                                    if context.sharedContext.mediaManager.hasOverlayVideoNode(overlayNode) {
                                        overlaySupernode?.view.addSubview(view)
                                    }
                                    overlayNode.canAttachContent = false
                                })
                            } else if let info = context.sharedContext.mediaManager.galleryHiddenMediaManager.findTarget(messageId: id, media: EngineMedia(media)) {
                                return GalleryTransitionArguments(transitionNode: (info.1, info.1.bounds, {
                                    return info.2()
                                }), addToTransitionSurface: info.0)
                            }
                            return nil
                        }))
                    case let .webPage(_, _, expandFromPip):
                        if let expandFromPip = expandFromPip, let baseNavigationController = baseNavigationController {
                            expandFromPip({ [weak overlayNode, context] in
                                if let overlayNode = overlayNode, let overlaySupernode = overlayNode.supernode {
                                    return GalleryTransitionArguments(transitionNode: (overlayNode, overlayNode.bounds, { [weak overlayNode] in
                                        return (overlayNode?.view.snapshotContentTree(), nil)
                                    }), addToTransitionSurface: { [weak context, weak overlaySupernode, weak overlayNode] view in
                                        guard let context = context, let overlayNode = overlayNode else {
                                            return
                                        }
                                        if context.sharedContext.mediaManager.hasOverlayVideoNode(overlayNode) {
                                            overlaySupernode?.view.addSubview(view)
                                        }
                                        overlayNode.canAttachContent = false
                                    })
                                }
                                return nil
                            }, baseNavigationController, { [weak baseNavigationController] c, a in
                                (baseNavigationController?.topViewController as? ViewController)?.present(c, in: .window(.root), with: a)
                            })
                        }
                }
            }
            if customUnembedWhenPortrait(overlayNode) {
                self.beginCustomDismiss(.default)
                self.statusNode.isHidden = true
                self.animateOut(toOverlay: overlayNode, completion: { [weak self] in
                    self?.completeCustomDismiss(false)
                })
            }
        }
    }
    
