    func nagramiXRequestDirectionalPiP(canCommit: @escaping () -> Bool, completion: @escaping (Bool) -> Void) -> Bool {
        guard self.nagramiXDirectionalPiPCompletion == nil,
              !self.nagramiXPiPStartRequested, self.nagramiXPendingPiPStart == nil,
              self.pictureInPictureController?.isPictureInPictureActive != true else { return false }
        self.nagramiXDirectionalPiPCompletion = completion
        self.nagramiXDirectionalPiPValidation = canCommit
        self.nagramiXDirectionalPiPDidTransfer = false
        // Bound both initial readiness and the native start acknowledgement.
        // Keep the gallery until native PiP confirms an active transfer.
        let timer = SwiftSignalKit.Timer(timeout: 3.0, repeat: false, completion: { [weak self] in
            guard let self else { return }
            if self.pictureInPictureController?.isPictureInPictureActive == true {
                // A delayed delegate notification must not stop an active PiP.
                self.nagramiXConfirmDirectionalPiPStart()
            } else {
                self.nagramiXFinishDirectionalPiP(started: false)
            }
        }, queue: Queue.mainQueue())
        self.nagramiXDirectionalPiPTimer = timer
        timer.start()
        let accepted = self.nagramiXRequestPictureInPicture(unavailable: { [weak self] in
            self?.nagramiXFinishDirectionalPiP(started: false)
        })
        if !accepted {
            self.nagramiXDirectionalPiPCompletion = nil
            self.nagramiXDirectionalPiPValidation = nil
            self.nagramiXDirectionalPiPTimer?.invalidate()
            self.nagramiXDirectionalPiPTimer = nil
        }
        return accepted
    }

    private func nagramiXConfirmDirectionalPiPStart() {
        guard self.nagramiXDirectionalPiPCompletion != nil,
              !self.nagramiXDirectionalPiPDidTransfer else { return }
        guard self.nagramiXDirectionalPiPValidation?() == true else {
            self.nagramiXFinishDirectionalPiP(started: false)
            return
        }
        self.nagramiXDirectionalPiPDidTransfer = true
        self.nagramiXPiPStartFailure = nil
        self.node.setCanPlaybackWithoutHierarchy(true)
        self.willBegin(self)
        self.didBegin(self)
        self.nagramiXFinishDirectionalPiP(started: true)
    }

    private func nagramiXFinishDirectionalPiP(started: Bool) {
        guard let completion = self.nagramiXDirectionalPiPCompletion else { return }
        self.nagramiXDirectionalPiPCompletion = nil
        self.nagramiXDirectionalPiPValidation = nil
        self.nagramiXDirectionalPiPTimer?.invalidate()
        self.nagramiXDirectionalPiPTimer = nil
        if !started {
            self.nagramiXCancelPendingPiPStart()
            self.nagramiXPiPStartRequested = false
            self.nagramiXPiPStartFailure = nil
            self.pictureInPictureController?.stopPictureInPicture()
            self.node.setCanPlaybackWithoutHierarchy(false)
        }
        completion(started)
    }

    func nagramiXCancelDirectionalPiP() {
        // Resign-active/rotation/centrality cancellation must not tear down an
        // already active system window. Its native delegate owns that lifetime.
        if self.pictureInPictureController?.isPictureInPictureActive != true {
            self.nagramiXFinishDirectionalPiP(started: false)
        }
    }
