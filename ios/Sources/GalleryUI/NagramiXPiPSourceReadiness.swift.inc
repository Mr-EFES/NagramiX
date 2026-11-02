    override func nagramiXStartDirectionalPiP(completion: @escaping (Bool) -> Void) -> Bool {
        guard #available(iOS 15.0, *), self.nagramiXCanBeginDirectionalPiPSwipe,
              self.nagramiXDirectionalPiPSourceRequest == nil,
              let videoNode = self.videoNode else { return false }
        let request = UUID()
        let deadline = CACurrentMediaTime() + 3.0
        self.nagramiXDirectionalPiPSourceRequest = request
        self.nagramiXDirectionalPiPSourceCompletion = completion

        let attempt: () -> Void = { [weak self, weak videoNode] in
            guard let self, self.nagramiXDirectionalPiPSourceRequest == request else { return }
            guard let videoNode, self.videoNode === videoNode,
                  self.nagramiXCanBeginDirectionalPiPSwipe,
                  UIApplication.shared.applicationState == .active,
                  self.galleryController()?.view.window != nil,
                  CACurrentMediaTime() < deadline else {
                self.nagramiXFinishDirectionalPiPSource(request: request, started: false)
                return
            }
            // Жест не зависит от готовности видеослоя. Ожидаем тот же плеер
            // в рамках одного запроса, без нового ресурса или элемента галереи.
            guard videoNode.getVideoLayer() != nil else { return }
            guard self.prepareForPictureInPictureSwipe(),
                  let content = self.nativePictureInPictureContent as? NativePictureInPictureContentImpl else {
                self.nagramiXFinishDirectionalPiPSource(request: request, started: false)
                return
            }
            self.nagramiXDirectionalPiPSourceTimer?.invalidate()
            self.nagramiXDirectionalPiPSourceTimer = nil
            self.nagramiXOwnsSwipePiPPreparation = true
            let accepted = content.nagramiXRequestDirectionalPiP(
                timeout: max(0.0, deadline - CACurrentMediaTime()),
                canCommit: { [weak self, weak content, weak videoNode] in
                    guard let self, let content, let videoNode else { return false }
                    return self.nagramiXDirectionalPiPSourceRequest == request
                        && self.videoNode === videoNode && self.nativePictureInPictureContent === content
                        && self.nagramiXCanBeginDirectionalPiPSwipe
                        && UIApplication.shared.applicationState == .active
                        && self.galleryController()?.view.window != nil
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
        let completion = self.nagramiXDirectionalPiPSourceCompletion
        // Очищаем до callback: отмена галереи может повторно обратиться к узлу.
        self.nagramiXDirectionalPiPSourceRequest = nil
        self.nagramiXDirectionalPiPSourceCompletion = nil
        self.nagramiXDirectionalPiPSourceTimer?.invalidate()
        self.nagramiXDirectionalPiPSourceTimer = nil
        completion?(started)
    }
