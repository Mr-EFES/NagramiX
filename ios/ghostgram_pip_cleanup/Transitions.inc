    override func animateIn(from node: (ASDisplayNode, CGRect, () -> (UIView?, UIView?)), addToTransitionSurface: (UIView) -> Void, completion: @escaping () -> Void) {
        guard let videoNode = self.videoNode, let validLayout = self.validLayout else {
            return
        }
        
        if let node = node.0 as? OverlayMediaItemNode {
            self.customUnembedWhenPortrait = node.customUnembedWhenPortrait
            node.customUnembedWhenPortrait = nil
        }
        
        if let node = node.0 as? OverlayMediaItemNode, self.context.sharedContext.mediaManager.hasOverlayVideoNode(node) {
            if let scrubberView = self.scrubberView {
                scrubberView.animateIn(from: nil, transition: .animated(duration: 0.25, curve: .spring))
            }
            
            var transformedFrame = node.view.convert(node.view.bounds, to: videoNode.view)
            let transformedSuperFrame = node.view.convert(node.view.bounds, to: videoNode.view.superview)
            
            videoNode.layer.animatePosition(from: CGPoint(x: transformedSuperFrame.midX, y: transformedSuperFrame.midY), to: videoNode.layer.position, duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring)
            
            transformedFrame.origin = CGPoint()
            
            let transform = CATransform3DScale(videoNode.layer.transform, transformedFrame.size.width / videoNode.layer.bounds.size.width, transformedFrame.size.height / videoNode.layer.bounds.size.height, 1.0)
            videoNode.layer.animate(from: NSValue(caTransform3D: transform), to: NSValue(caTransform3D: videoNode.layer.transform), keyPath: "transform", timingFunction: kCAMediaTimingFunctionSpring, duration: 0.25)
            
            videoNode.canAttachContent = true
            self.updateDisplayPlaceholder()
            
            self.context.sharedContext.mediaManager.setOverlayVideoNode(nil)
        } else {
            var scrubberTransition = (node.0 as? GalleryItemTransitionNode)?.scrubberTransition()
            
            if let data = self.context.currentAppConfiguration.with({ $0 }).data {
                if let value = data["ios_gallery_scrubber_transition"] as? Double {
                    if value == 0.0 {
                        scrubberTransition = nil
                    }
                }
            }
            
            if let scrubberView = self.scrubberView {
                scrubberView.animateIn(from: scrubberTransition, transition: .animated(duration: 0.25, curve: .spring))
            }
            
            var transformedFrame = node.0.view.convert(node.0.view.bounds, to: videoNode.view)
            var transformedSuperFrame = node.0.view.convert(node.0.view.bounds, to: videoNode.view.superview)
            var transformedSelfFrame = node.0.view.convert(node.0.view.bounds, to: self.view)
            let transformedCopyViewFinalFrame = videoNode.view.convert(videoNode.view.bounds, to: self.view)
            
            let (maybeSurfaceCopyView, _) = node.2()
            let (maybeCopyView, copyViewBackground) = node.2()
            copyViewBackground?.alpha = 0.0
            let surfaceCopyView = maybeSurfaceCopyView!
            let copyView = maybeCopyView!
            
            addToTransitionSurface(surfaceCopyView)
            
            var transformedSurfaceFrame: CGRect?
            var transformedSurfaceFinalFrame: CGRect?
            if let contentSurface = surfaceCopyView.superview {
                transformedSurfaceFrame = node.0.view.convert(node.0.view.bounds, to: contentSurface)
                transformedSurfaceFinalFrame = videoNode.view.convert(videoNode.view.bounds, to: contentSurface)
                
                if let frame = transformedSurfaceFrame, frame.minY < 0.0 {
                    transformedSurfaceFrame = CGRect(x: frame.minX, y: 0.0, width: frame.width, height: frame.height)
                }
            }
            
            if transformedSelfFrame.maxY < 0.0 {
                transformedSelfFrame = CGRect(x: transformedSelfFrame.minX, y: 0.0, width: transformedSelfFrame.width, height: transformedSelfFrame.height)
            }
            
            if transformedSuperFrame.maxY < 0.0 {
                transformedSuperFrame = CGRect(x: transformedSuperFrame.minX, y: 0.0, width: transformedSuperFrame.width, height: transformedSuperFrame.height)
            }
            
            if let transformedSurfaceFrame = transformedSurfaceFrame {
                surfaceCopyView.frame = transformedSurfaceFrame
            }
            
            self.view.insertSubview(copyView, belowSubview: self.scrollNode.view)
            copyView.frame = transformedSelfFrame
            
            copyView.layer.animateAlpha(from: 0.0, to: 1.0, duration: 0.2, removeOnCompletion: false)
            
            surfaceCopyView.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.25, removeOnCompletion: false)
            
            copyView.layer.animatePosition(from: CGPoint(x: transformedSelfFrame.midX, y: transformedSelfFrame.midY), to: CGPoint(x: transformedCopyViewFinalFrame.midX, y: transformedCopyViewFinalFrame.midY), duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring, removeOnCompletion: false, completion: { [weak copyView] _ in
                copyView?.removeFromSuperview()
            })
            let scale = CGSize(width: transformedCopyViewFinalFrame.size.width / transformedSelfFrame.size.width, height: transformedCopyViewFinalFrame.size.height / transformedSelfFrame.size.height)
            copyView.layer.animate(from: NSValue(caTransform3D: CATransform3DIdentity), to: NSValue(caTransform3D: CATransform3DMakeScale(scale.width, scale.height, 1.0)), keyPath: "transform", timingFunction: kCAMediaTimingFunctionSpring, duration: 0.25, removeOnCompletion: false)
            
            if let transformedSurfaceFrame = transformedSurfaceFrame, let transformedSurfaceFinalFrame = transformedSurfaceFinalFrame {
                surfaceCopyView.layer.animatePosition(from: CGPoint(x: transformedSurfaceFrame.midX, y: transformedSurfaceFrame.midY), to: CGPoint(x: transformedSurfaceFinalFrame.midX, y: transformedSurfaceFinalFrame.midY), duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring, removeOnCompletion: false, completion: { [weak surfaceCopyView] _ in
                    surfaceCopyView?.removeFromSuperview()
                })
                let scale = CGSize(width: transformedSurfaceFinalFrame.size.width / transformedSurfaceFrame.size.width, height: transformedSurfaceFinalFrame.size.height / transformedSurfaceFrame.size.height)
                surfaceCopyView.layer.animate(from: NSValue(caTransform3D: CATransform3DIdentity), to: NSValue(caTransform3D: CATransform3DMakeScale(scale.width, scale.height, 1.0)), keyPath: "transform", timingFunction: kCAMediaTimingFunctionSpring, duration: 0.25, removeOnCompletion: false)
            }
            
            if surfaceCopyView.superview != nil {
                videoNode.allowsGroupOpacity = true
                videoNode.layer.animateAlpha(from: 0.0, to: 1.0, duration: 0.1, completion: { [weak videoNode] _ in
                    videoNode?.allowsGroupOpacity = false
                })
            }
            videoNode.layer.animatePosition(from: CGPoint(x: transformedSuperFrame.midX, y: transformedSuperFrame.midY), to: videoNode.layer.position, duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring)
            
            transformedFrame.origin = CGPoint()
            
            let transform = CATransform3DScale(videoNode.layer.transform, transformedFrame.size.width / videoNode.layer.bounds.size.width, transformedFrame.size.height / videoNode.layer.bounds.size.height, 1.0)
            
            videoNode.layer.animate(from: NSValue(caTransform3D: transform), to: NSValue(caTransform3D: videoNode.layer.transform), keyPath: "transform", timingFunction: kCAMediaTimingFunctionSpring, duration: 0.25)
            
            if let scrubberTransition, let contentTransition = scrubberTransition.content {
                let transitionContentView = contentTransition.makeView()
                let transitionSelfContentView = contentTransition.makeView()
                
                addToTransitionSurface(transitionContentView)
                self.view.insertSubview(transitionSelfContentView, at: 0)
                transitionSelfContentView.layer.animateAlpha(from: 0.0, to: 1.0, duration: 0.2, removeOnCompletion: false)
                
                if let transitionContentSuperview = transitionContentView.superview {
                    let transitionContentSourceFrame = contentTransition.sourceView.convert(contentTransition.sourceRect, to: transitionContentSuperview)
                    let transitionContentDestinationFrame = self.view.convert(self.view.bounds, to: transitionContentSuperview)
                    
                    let transitionContentSelfSourceFrame = contentTransition.sourceView.convert(contentTransition.sourceRect, to: self.view)
                    let transitionContentSelfDestinationFrame = self.view.convert(self.view.bounds, to: self.view)
                    
                    let screenCornerRadius: CGFloat = validLayout.layout.deviceMetrics.screenCornerRadius
                    
                    transitionContentView.frame = transitionContentSourceFrame
                    contentTransition.updateView(transitionContentView, GalleryItemScrubberTransition.Content.TransitionState(sourceSize: transitionContentSourceFrame.size, destinationSize: transitionContentDestinationFrame.size, destinationCornerRadius: screenCornerRadius, progress: 0.0), .immediate)
                    
                    transitionSelfContentView.frame = transitionContentSelfSourceFrame
                    contentTransition.updateView(transitionSelfContentView, GalleryItemScrubberTransition.Content.TransitionState(sourceSize: transitionContentSelfSourceFrame.size, destinationSize: transitionContentSelfDestinationFrame.size, destinationCornerRadius: screenCornerRadius, progress: 0.0), .immediate)
                    
                    let transition: ContainedViewLayoutTransition = .animated(duration: 0.25, curve: .spring)
                    
                    transition.updateFrame(view: transitionContentView, frame: transitionContentDestinationFrame, completion: { [weak transitionContentView] _ in
                        transitionContentView?.removeFromSuperview()
                    })
                    contentTransition.updateView(transitionContentView, GalleryItemScrubberTransition.Content.TransitionState(sourceSize: transitionContentSourceFrame.size, destinationSize: transitionContentDestinationFrame.size, destinationCornerRadius: screenCornerRadius, progress: 1.0), transition)
                    
                    transition.updateFrame(view: transitionSelfContentView, frame: transitionContentSelfDestinationFrame, completion: { [weak transitionSelfContentView] _ in
                        transitionSelfContentView?.removeFromSuperview()
                    })
                    contentTransition.updateView(transitionSelfContentView, GalleryItemScrubberTransition.Content.TransitionState(sourceSize: transitionContentSelfSourceFrame.size, destinationSize: transitionContentSelfDestinationFrame.size, destinationCornerRadius: screenCornerRadius, progress: 1.0), transition)
                }
            }
            
            if self.item?.fromPlayingVideo ?? false {
                Queue.mainQueue().after(0.001) {
                    videoNode.canAttachContent = true
                    self.updateDisplayPlaceholder()
                }
            }
            
            if let pictureInPictureNode = self.pictureInPictureNode {
                let transformedPlaceholderFrame = node.0.view.convert(node.0.view.bounds, to: pictureInPictureNode.view)
                let transform = CATransform3DScale(pictureInPictureNode.layer.transform, transformedPlaceholderFrame.size.width / pictureInPictureNode.layer.bounds.size.width, transformedPlaceholderFrame.size.height / pictureInPictureNode.layer.bounds.size.height, 1.0)
                pictureInPictureNode.layer.animate(from: NSValue(caTransform3D: transform), to: NSValue(caTransform3D: pictureInPictureNode.layer.transform), keyPath: "transform", timingFunction: kCAMediaTimingFunctionSpring, duration: 0.25)
                
                pictureInPictureNode.layer.animateAlpha(from: 0.0, to: 1.0, duration: 0.1)
                pictureInPictureNode.layer.animatePosition(from: CGPoint(x: transformedSuperFrame.midX, y: transformedSuperFrame.midY), to: pictureInPictureNode.layer.position, duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring)
            }
            
            self.statusButtonNode.layer.animatePosition(from: CGPoint(x: transformedSuperFrame.midX, y: transformedSuperFrame.midY), to: self.statusButtonNode.position, duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring)
            self.statusButtonNode.layer.animateAlpha(from: 0.0, to: 1.0, duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring)
            self.statusButtonNode.layer.animateScale(from: 0.5, to: 1.0, duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring)
            
            if let playbackControlsView = self.playbackControls.view {
                playbackControlsView.layer.animatePosition(from: CGPoint(x: transformedSuperFrame.midX, y: transformedSuperFrame.midY), to: playbackControlsView.layer.position, duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring)
                playbackControlsView.layer.animateAlpha(from: 0.0, to: 1.0, duration: 0.2, timingFunction: kCAMediaTimingFunctionSpring)
                playbackControlsView.layer.animateScale(from: 0.2, to: 1.0, duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring)
            }
        }
    }
    
    override func animateOut(to node: (ASDisplayNode, CGRect, () -> (UIView?, UIView?)), addToTransitionSurface: (UIView) -> Void, completion: @escaping () -> Void) {
        if let status = self.playerStatusValue {
            self.maybeStorePlaybackStatus(status: status)
        }
        
        self.isAnimatingOut = true
        
        guard let videoNode = self.videoNode else {
            completion()
            return
        }
        
        var scrubberTransition = (node.0 as? GalleryItemTransitionNode)?.scrubberTransition()
        if let data = self.context.currentAppConfiguration.with({ $0 }).data {
            if let value = data["ios_gallery_scrubber_transition"] as? Double {
                if value == 0.0 {
                    scrubberTransition = nil
                }
            }
        }
        
        if let scrubberView = self.scrubberView {
            var scrubberEffectiveTransition = scrubberTransition
            if !self.controlsVisibility() {
                scrubberEffectiveTransition = nil
            }
            scrubberView.animateOut(to: scrubberEffectiveTransition, transition: .animated(duration: 0.25, curve: .spring))
        }
        
        let transformedFrame = node.0.view.convert(node.0.view.bounds, to: videoNode.view)
        var transformedSuperFrame = node.0.view.convert(node.0.view.bounds, to: videoNode.view.superview)
        let transformedSelfFrame = node.0.view.convert(node.0.view.bounds, to: self.view)
        let transformedCopyViewInitialFrame = videoNode.view.convert(videoNode.view.bounds, to: self.view)
        
        var positionCompleted = false
        var transformCompleted = false
        var boundsCompleted = true
        var copyCompleted = false
        
        let (maybeSurfaceCopyView, _) = node.2()
        let (maybeCopyView, copyViewBackground) = node.2()
        copyViewBackground?.alpha = 0.0
        let surfaceCopyView = maybeSurfaceCopyView!
        let copyView = maybeCopyView!
        
        addToTransitionSurface(surfaceCopyView)
        
        var transformedSurfaceFrame: CGRect?
        var transformedSurfaceCopyViewInitialFrame: CGRect?
        if let contentSurface = surfaceCopyView.superview {
            transformedSurfaceFrame = node.0.view.convert(node.0.view.bounds, to: contentSurface)
            transformedSurfaceCopyViewInitialFrame = videoNode.view.convert(videoNode.view.bounds, to: contentSurface)
        }
        
        self.view.insertSubview(copyView, belowSubview: self.scrollNode.view)
        copyView.frame = transformedSelfFrame
        
        let intermediateCompletion = { [weak copyView, weak surfaceCopyView] in
            if positionCompleted && transformCompleted && boundsCompleted && copyCompleted {
                copyView?.removeFromSuperview()
                surfaceCopyView?.removeFromSuperview()
                videoNode.canAttachContent = false
                videoNode.removeFromSupernode()
                completion()
            }
        }
        
        copyView.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.18, removeOnCompletion: false)
        surfaceCopyView.layer.animateAlpha(from: 0.0, to: 1.0, duration: 0.1, removeOnCompletion: false)
        
        copyView.layer.animatePosition(from: CGPoint(x: transformedCopyViewInitialFrame.midX, y: transformedCopyViewInitialFrame.midY), to: CGPoint(x: transformedSelfFrame.midX, y: transformedSelfFrame.midY), duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring, removeOnCompletion: false)
        let scale = CGSize(width: transformedCopyViewInitialFrame.size.width / transformedSelfFrame.size.width, height: transformedCopyViewInitialFrame.size.height / transformedSelfFrame.size.height)
        copyView.layer.animate(from: NSValue(caTransform3D: CATransform3DMakeScale(scale.width, scale.height, 1.0)), to: NSValue(caTransform3D: CATransform3DIdentity), keyPath: "transform", timingFunction: kCAMediaTimingFunctionSpring, duration: 0.25, removeOnCompletion: false, completion: { _ in
            copyCompleted = true
            intermediateCompletion()
        })
        
        if let transformedSurfaceFrame = transformedSurfaceFrame, let transformedCopyViewInitialFrame = transformedSurfaceCopyViewInitialFrame {
            surfaceCopyView.layer.animatePosition(from: CGPoint(x: transformedCopyViewInitialFrame.midX, y: transformedCopyViewInitialFrame.midY), to: CGPoint(x: transformedSurfaceFrame.midX, y: transformedSurfaceFrame.midY), duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring, removeOnCompletion: false)
            let scale = CGSize(width: transformedCopyViewInitialFrame.size.width / transformedSurfaceFrame.size.width, height: transformedCopyViewInitialFrame.size.height / transformedSurfaceFrame.size.height)
            surfaceCopyView.layer.animate(from: NSValue(caTransform3D: CATransform3DMakeScale(scale.width, scale.height, 1.0)), to: NSValue(caTransform3D: CATransform3DIdentity), keyPath: "transform", timingFunction: kCAMediaTimingFunctionSpring, duration: 0.25, removeOnCompletion: false)
        }
        
        self.statusButtonNode.layer.animatePosition(from: self.statusButtonNode.layer.position, to: CGPoint(x: transformedSelfFrame.midX, y: transformedSelfFrame.midY), duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring, removeOnCompletion: false, completion: { _ in
        })
        self.statusButtonNode.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.25, removeOnCompletion: false)
        self.statusButtonNode.layer.animateScale(from: 1.0, to: 0.2, duration: 0.25, removeOnCompletion: false)
        
        if let playbackControlsView = self.playbackControls.view {
            playbackControlsView.layer.animatePosition(from: playbackControlsView.layer.position, to: CGPoint(x: transformedSelfFrame.midX, y: transformedSelfFrame.midY), duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring, removeOnCompletion: false, completion: { _ in
            })
            playbackControlsView.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.25, removeOnCompletion: false)
            playbackControlsView.layer.animateScale(from: 1.0, to: 0.2, duration: 0.25, removeOnCompletion: false)
        }
        
        let fromTransform: CATransform3D
        let toTransform: CATransform3D
        
        if let instantNode = node.0 as? GalleryItemTransitionNode, instantNode.isAvailableForInstantPageTransition(), videoNode.hasAttachedContext {
            copyView.removeFromSuperview()
            
            let previousFrame = videoNode.frame
            let previousSuperview = videoNode.view.superview
            addToTransitionSurface(videoNode.view)
            videoNode.view.superview?.bringSubviewToFront(videoNode.view)
            
            if let previousSuperview = previousSuperview {
                videoNode.frame = previousSuperview.convert(previousFrame, to: videoNode.view.superview)
                transformedSuperFrame = transformedSuperFrame.offsetBy(dx: videoNode.position.x - previousFrame.center.x, dy: videoNode.position.y - previousFrame.center.y)
            }
            
            let initialScale: CGFloat = 1.0
            let targetScale = max(transformedFrame.size.width / videoNode.layer.bounds.size.width, transformedFrame.size.height / videoNode.layer.bounds.size.height)
            
            videoNode.backgroundColor = .clear
        
            let transformScale: CGFloat = initialScale * targetScale
            fromTransform = CATransform3DScale(videoNode.layer.transform, initialScale, initialScale, 1.0)
            toTransform = CATransform3DScale(videoNode.layer.transform, transformScale, transformScale, 1.0)
            
            if videoNode.hasAttachedContext {
                if self.isPaused || !self.keepSoundOnDismiss {
                    videoNode.continuePlayingWithoutSound()
                }
            }
        } else if let interactiveMediaNode = node.0 as? GalleryItemTransitionNode, interactiveMediaNode.isAvailableForGalleryTransition(), videoNode.hasAttachedContext {
            self.imageNode?.alpha = 0.0
            
            copyView.removeFromSuperview()
            
            let previousFrame = videoNode.frame
            let previousSuperview = videoNode.view.superview
            addToTransitionSurface(videoNode.view)
            videoNode.view.superview?.bringSubviewToFront(videoNode.view)

            if let previousSuperview = previousSuperview {
                videoNode.frame = previousSuperview.convert(previousFrame, to: videoNode.view.superview)
                transformedSuperFrame = transformedSuperFrame.offsetBy(dx: videoNode.position.x - previousFrame.center.x, dy: videoNode.position.y - previousFrame.center.y)
            }
            
            let initialScale = min(videoNode.layer.bounds.width / node.0.view.bounds.width, videoNode.layer.bounds.height / node.0.view.bounds.height)
            let targetScale = max(transformedFrame.size.width / videoNode.layer.bounds.size.width, transformedFrame.size.height / videoNode.layer.bounds.size.height)
            
            videoNode.backgroundColor = .clear
            if let bubbleDecoration = interactiveMediaNode.decoration as? ChatBubbleVideoDecoration, let decoration = videoNode.decoration as? GalleryVideoDecoration  {
                transformedSuperFrame = transformedSuperFrame.offsetBy(dx: bubbleDecoration.corners.extendedEdges.right / 2.0 - bubbleDecoration.corners.extendedEdges.left / 2.0, dy: 0.0)
                if let item = self.item {
                    let size = item.content.dimensions.aspectFilled(bubbleDecoration.contentContainerNode.frame.size)
                    videoNode.updateLayout(size: size, transition: .immediate)
                    videoNode.bounds = CGRect(origin: CGPoint(), size: size)
                
                    boundsCompleted = false
                    decoration.updateCorners(bubbleDecoration.corners)
                    decoration.updateClippingFrame(bubbleDecoration.contentContainerNode.bounds, completion: {
                        boundsCompleted = true
                        intermediateCompletion()
                    })
                }
            }
        
            let transformScale: CGFloat = initialScale * targetScale
            fromTransform = CATransform3DScale(videoNode.layer.transform, initialScale, initialScale, 1.0)
            toTransform = CATransform3DScale(videoNode.layer.transform, transformScale, transformScale, 1.0)
            
            if videoNode.hasAttachedContext {
                if let status = self.playerStatusValue {
                    self.maybeStorePlaybackStatus(status: status)
                }
                
                if self.isPaused || !self.keepSoundOnDismiss {
                    if let item = self.item, item.content is HLSVideoContent {
                    } else {
                        videoNode.continuePlayingWithoutSound()
                    }
                }
            }
        } else {
            videoNode.allowsGroupOpacity = true
            videoNode.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.2, removeOnCompletion: false, completion: { [weak videoNode] _ in
                videoNode?.allowsGroupOpacity = false
            })
            
            fromTransform = videoNode.layer.transform
            toTransform = CATransform3DScale(videoNode.layer.transform, transformedFrame.size.width / videoNode.layer.bounds.size.width, transformedFrame.size.height / videoNode.layer.bounds.size.height, 1.0)
        }
        
        videoNode.layer.animatePosition(from: videoNode.layer.position, to: CGPoint(x: transformedSuperFrame.midX, y: transformedSuperFrame.midY), duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring, removeOnCompletion: false, completion: { _ in
            positionCompleted = true
            intermediateCompletion()
        })
        
        videoNode.layer.animate(from: NSValue(caTransform3D: fromTransform), to: NSValue(caTransform3D: toTransform), keyPath: "transform", timingFunction: kCAMediaTimingFunctionSpring, duration: 0.25, removeOnCompletion: false, completion: { _ in
            transformCompleted = true
            intermediateCompletion()
        })
        
        var scrubberContentTransition = scrubberTransition
        if !self.controlsVisibility() {
            scrubberContentTransition = nil
        }
        if let scrubberContentTransition, let contentTransition = scrubberContentTransition.content {
            let transitionContentView = contentTransition.makeView()
            let transitionSelfContentView = contentTransition.makeView()
            
            addToTransitionSurface(transitionContentView)
            //self.view.insertSubview(transitionSelfContentView, at: 0)
            transitionSelfContentView.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.18, removeOnCompletion: false)
            
            if let validLayout = self.validLayout, let transitionContentSuperview = transitionContentView.superview {
                let transitionContentSourceFrame = contentTransition.sourceView.convert(contentTransition.sourceRect, to: transitionContentSuperview)
                let transitionContentDestinationFrame = self.view.convert(self.view.bounds, to: transitionContentSuperview)
                
                let transitionContentSelfSourceFrame = contentTransition.sourceView.convert(contentTransition.sourceRect, to: self.view)
                let transitionContentSelfDestinationFrame = self.view.convert(self.view.bounds, to: self.view)
                
                let screenCornerRadius: CGFloat = validLayout.layout.deviceMetrics.screenCornerRadius
                
                transitionContentView.frame = transitionContentDestinationFrame
                contentTransition.updateView(transitionContentView, GalleryItemScrubberTransition.Content.TransitionState(sourceSize: transitionContentSourceFrame.size, destinationSize: transitionContentDestinationFrame.size, destinationCornerRadius: screenCornerRadius, progress: 1.0), .immediate)
                
                transitionSelfContentView.frame = transitionContentSelfDestinationFrame
                contentTransition.updateView(transitionSelfContentView, GalleryItemScrubberTransition.Content.TransitionState(sourceSize: transitionContentSelfSourceFrame.size, destinationSize: transitionContentSelfDestinationFrame.size, destinationCornerRadius: screenCornerRadius, progress: 1.0), .immediate)
                
                let transition: ContainedViewLayoutTransition = .animated(duration: 0.25, curve: .spring)
                
                transition.updateFrame(view: transitionContentView, frame: transitionContentSourceFrame, completion: { [weak transitionContentView] _ in
                    transitionContentView?.removeFromSuperview()
                })
                contentTransition.updateView(transitionContentView, GalleryItemScrubberTransition.Content.TransitionState(sourceSize: transitionContentSourceFrame.size, destinationSize: transitionContentDestinationFrame.size, destinationCornerRadius: screenCornerRadius, progress: 0.0), transition)
                
                transition.updateFrame(view: transitionSelfContentView, frame: transitionContentSelfSourceFrame, completion: { [weak transitionSelfContentView] _ in
                    transitionSelfContentView?.removeFromSuperview()
                })
                contentTransition.updateView(transitionSelfContentView, GalleryItemScrubberTransition.Content.TransitionState(sourceSize: transitionContentSelfSourceFrame.size, destinationSize: transitionContentSelfDestinationFrame.size, destinationCornerRadius: screenCornerRadius, progress: 0.0), transition)
            }
        }
        
        if let pictureInPictureNode = self.pictureInPictureNode {
            let transformedPlaceholderFrame = node.0.view.convert(node.0.view.bounds, to: pictureInPictureNode.view)
            let pictureInPictureTransform = CATransform3DScale(pictureInPictureNode.layer.transform, transformedPlaceholderFrame.size.width / pictureInPictureNode.layer.bounds.size.width, transformedPlaceholderFrame.size.height / pictureInPictureNode.layer.bounds.size.height, 1.0)
            pictureInPictureNode.layer.animate(from: NSValue(caTransform3D: pictureInPictureNode.layer.transform), to: NSValue(caTransform3D: pictureInPictureTransform), keyPath: "transform", timingFunction: kCAMediaTimingFunctionSpring, duration: 0.25, removeOnCompletion: false, completion: { _ in
            })
            
            pictureInPictureNode.layer.animatePosition(from: pictureInPictureNode.layer.position, to: CGPoint(x: transformedSuperFrame.midX, y: transformedSuperFrame.midY), duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring, removeOnCompletion: false, completion: { _ in
                positionCompleted = true
                intermediateCompletion()
            })
            pictureInPictureNode.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.2, removeOnCompletion: false)
        }
    }
    
    func animateOut(toOverlay node: ASDisplayNode, completion: @escaping () -> Void) {
        guard let videoNode = self.videoNode else {
            completion()
            return
        }
        
        var transformedFrame = node.view.convert(node.view.bounds, to: videoNode.view)
        let transformedSuperFrame = node.view.convert(node.view.bounds, to: videoNode.view.superview)
        let transformedSelfFrame = node.view.convert(node.view.bounds, to: self.view)
        let transformedCopyViewInitialFrame = videoNode.view.convert(videoNode.view.bounds, to: self.view)
        let transformedSelfTargetSuperFrame = videoNode.view.convert(videoNode.view.bounds, to: node.view.superview)
        
        var positionCompleted = false
        var boundsCompleted = false
        var copyCompleted = false
        var nodeCompleted = false
        
        let copyView = node.view.snapshotContentTree()!
        
        videoNode.isHidden = true
        copyView.frame = transformedSelfFrame
        
        let intermediateCompletion = { [weak copyView] in
            if positionCompleted && boundsCompleted && copyCompleted && nodeCompleted {
                copyView?.removeFromSuperview()
                completion()
            }
        }
        
        copyView.layer.animateAlpha(from: 0.0, to: 1.0, duration: 0.1, removeOnCompletion: false)
        
        copyView.layer.animatePosition(from: CGPoint(x: transformedCopyViewInitialFrame.midX, y: transformedCopyViewInitialFrame.midY), to: CGPoint(x: transformedSelfFrame.midX, y: transformedSelfFrame.midY), duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring, removeOnCompletion: false)
        let scale = CGSize(width: transformedCopyViewInitialFrame.size.width / transformedSelfFrame.size.width, height: transformedCopyViewInitialFrame.size.height / transformedSelfFrame.size.height)
        copyView.layer.animate(from: NSValue(caTransform3D: CATransform3DMakeScale(scale.width, scale.height, 1.0)), to: NSValue(caTransform3D: CATransform3DIdentity), keyPath: "transform", timingFunction: kCAMediaTimingFunctionSpring, duration: 0.25, removeOnCompletion: false, completion: { _ in
            copyCompleted = true
            intermediateCompletion()
        })
        
        videoNode.layer.animatePosition(from: videoNode.layer.position, to: CGPoint(x: transformedSuperFrame.midX, y: transformedSuperFrame.midY), duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring, removeOnCompletion: false, completion: { _ in
            positionCompleted = true
            intermediateCompletion()
        })
        
        videoNode.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.25, removeOnCompletion: false)
        
        self.statusButtonNode.layer.animatePosition(from: self.statusButtonNode.layer.position, to: CGPoint(x: transformedSelfFrame.midX, y: transformedSelfFrame.midY), duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring, removeOnCompletion: false, completion: { _ in
        })
        self.statusButtonNode.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.25, removeOnCompletion: false)
        self.statusButtonNode.layer.animateScale(from: 1.0, to: 0.2, duration: 0.25, removeOnCompletion: false)
        
        transformedFrame.origin = CGPoint()
        
        let videoTransform = CATransform3DScale(videoNode.layer.transform, transformedFrame.size.width / videoNode.layer.bounds.size.width, transformedFrame.size.height / videoNode.layer.bounds.size.height, 1.0)
        videoNode.layer.animate(from: NSValue(caTransform3D: videoNode.layer.transform), to: NSValue(caTransform3D: videoTransform), keyPath: "transform", timingFunction: kCAMediaTimingFunctionSpring, duration: 0.25, removeOnCompletion: false, completion: { _ in
            boundsCompleted = true
            intermediateCompletion()
        })
        
        if let pictureInPictureNode = self.pictureInPictureNode {
            pictureInPictureNode.isHidden = true
        }
        
        let nodeTransform = CATransform3DScale(node.layer.transform, videoNode.layer.bounds.size.width / transformedFrame.size.width, videoNode.layer.bounds.size.height / transformedFrame.size.height, 1.0)
        node.layer.animatePosition(from: CGPoint(x: transformedSelfTargetSuperFrame.midX, y: transformedSelfTargetSuperFrame.midY), to: node.layer.position, duration: 0.25, timingFunction: kCAMediaTimingFunctionSpring)
        node.layer.animate(from: NSValue(caTransform3D: nodeTransform), to: NSValue(caTransform3D: node.layer.transform), keyPath: "transform", timingFunction: kCAMediaTimingFunctionSpring, duration: 0.25, removeOnCompletion: false, completion: { _ in
            nodeCompleted = true
            intermediateCompletion()
        })
    }
    
