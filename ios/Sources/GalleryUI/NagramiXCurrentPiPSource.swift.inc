    override var nagramiXPiPSwipeView: UIView { return self.scrollNode.view }

    override var nagramiXBlocksPiPSourcePan: Bool {
        guard #available(iOS 15.0, *), NagramiXTabSettings.videoPiPSwipeEnabled else { return false }
        if self.pictureInPictureNode != nil || self.context.sharedContext.mediaManager.currentPictureInPictureNode === self {
            return true
        }
        return (self.nativePictureInPictureContent as? NativePictureInPictureContentImpl)?.nagramiXHasPiPRequest == true
    }

    override var nagramiXCanBeginDirectionalPiPSwipe: Bool {
        guard #available(iOS 15.0, *), self.nagramiXCanUseDirectionalPiP,
              self.pictureInPictureNode == nil, self.videoNode?.ownsContentNode == true,
              self.context.sharedContext.mediaManager.currentPictureInPictureNode !== self else { return false }
        return (self.nativePictureInPictureContent as? NativePictureInPictureContentImpl)?.nagramiXHasPiPRequest != true
    }

    override func nagramiXStartDirectionalPiP(completion: @escaping (Bool) -> Void) -> Bool {
        guard #available(iOS 15.0, *), self.nagramiXCanBeginDirectionalPiPSwipe,
              self.nagramiXDirectionalPiPSourceRequest == nil,
              let videoNode = self.videoNode else { return false }
        let request = UUID()
        NSLog("NagramiX PiP: request=%@ begin", request.uuidString)
        let deadline = CACurrentMediaTime() + 3.0
        let previousOwner = self.context.sharedContext.mediaManager.currentPictureInPictureNode
        var askedPreviousToStop = false
        self.nagramiXDirectionalPiPSourceRequest = request
        self.nagramiXDirectionalPiPSourceCompletion = completion

        let attempt: () -> Void = { [weak self, weak videoNode] in
            guard let self, self.nagramiXDirectionalPiPSourceRequest == request else { return }
            guard let videoNode, self.videoNode === videoNode, self.nagramiXCanUseDirectionalPiP,
                  UIApplication.shared.applicationState == .active,
                  self.galleryController()?.view.window != nil, self.baseNavigationController() != nil,
                  CACurrentMediaTime() < deadline else {
                NSLog("NagramiX PiP: request=%@ invalid_or_timeout", request.uuidString)
                self.nagramiXFinishDirectionalPiPSource(request: request, started: false)
                return
            }
            if let current = self.context.sharedContext.mediaManager.currentPictureInPictureNode {
                // Только тот предыдущий владелец, который существовал при отпускании.
                // Поздний запрос не закрывает новое окно, открытое другим действием.
                guard current === previousOwner, current !== self,
                      let previous = current as? UniversalVideoGalleryItemNode,
                      let content = previous.nativePictureInPictureContent as? NativePictureInPictureContentImpl else {
                    self.nagramiXFinishDirectionalPiPSource(request: request, started: false)
                    return
                }
                if !askedPreviousToStop {
                    askedPreviousToStop = true
                    NSLog("NagramiX PiP: request=%@ previous_stop", request.uuidString)
                    content.stop()
                }
                // didStop очищает владельца. До этого новый контроллер не запускается.
                return
            }
            guard videoNode.ownsContentNode, self.pictureInPictureNode == nil,
                  videoNode.getVideoLayer() != nil else { return }
            guard self.prepareForPictureInPictureSwipe(),
                  let content = self.nativePictureInPictureContent as? NativePictureInPictureContentImpl,
                  content.nagramiXMatchesSource(videoNode) else {
                self.nagramiXFinishDirectionalPiPSource(request: request, started: false)
                return
            }
            NSLog("NagramiX PiP: request=%@ source_ready", request.uuidString)
            self.nagramiXDirectionalPiPSourceTimer?.invalidate()
            self.nagramiXDirectionalPiPSourceTimer = nil
            self.nagramiXOwnsSwipePiPPreparation = true
            let accepted = content.nagramiXRequestDirectionalPiP(
                timeout: max(0.0, deadline - CACurrentMediaTime()),
                canCommit: { [weak self, weak content, weak videoNode] in
                    guard let self, let content, let videoNode else { return false }
                    let owner = self.context.sharedContext.mediaManager.currentPictureInPictureNode
                    return self.nagramiXDirectionalPiPSourceRequest == request
                        && self.videoNode === videoNode && self.nativePictureInPictureContent === content
                        && content.nagramiXMatchesSource(videoNode, requireLayer: false)
                        && (owner == nil || owner === self) && self.nagramiXCanUseDirectionalPiP
                        && UIApplication.shared.applicationState == .active
                        && self.galleryController()?.view.window != nil && self.baseNavigationController() != nil
                }, completion: { [weak self] started in
                    self?.nagramiXFinishDirectionalPiPSource(request: request, started: started)
                }
            )
            if !accepted {
                self.nagramiXFinishDirectionalPiPSource(request: request, started: false)
            }
        }
        let timer = SwiftSignalKit.Timer(timeout: 0.05, repeat: true, completion: attempt, queue: Queue.mainQueue())
        self.nagramiXDirectionalPiPSourceTimer = timer
        timer.start()
        attempt()
        return true
    }

    private func nagramiXFinishDirectionalPiPSource(request: UUID, started: Bool) {
        guard self.nagramiXDirectionalPiPSourceRequest == request else { return }
        NSLog("NagramiX PiP: request=%@ started=%@", request.uuidString, started ? "true" : "false")
        let completion = self.nagramiXDirectionalPiPSourceCompletion
        self.nagramiXDirectionalPiPSourceRequest = nil
        self.nagramiXDirectionalPiPSourceCompletion = nil
        self.nagramiXDirectionalPiPSourceTimer?.invalidate()
        self.nagramiXDirectionalPiPSourceTimer = nil
        completion?(started)
    }
