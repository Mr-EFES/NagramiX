        private var nagramiXDidRequestInitialRecording = false
        private var nagramiXCountdownTimer: SwiftSignalKit.Timer?
        private var nagramiXCountdownPositionDisposable: Disposable?
        private var nagramiXCountdownBackgroundObserver: NSObjectProtocol?

        private func nagramiXArmCountdown(controller: VideoMessageCameraScreen) {
            controller.node.nagramiXCountdownPending = true
            controller.node.nagramiXUpdateCountdown(3)
            controller.camera?.focus(at: CGPoint(x: 0.5, y: 0.5), autoFocus: true)
            self.nagramiXCountdownBackgroundObserver = NotificationCenter.default.addObserver(forName: UIApplication.willResignActiveNotification, object: nil, queue: .main) { [weak self] _ in
                guard let controller = self?.getController(), controller.node.nagramiXCountdownPending else { return }
                controller.discardVideo()
                controller.completion(nil, nil, nil, nil)
            }
        }

        private func nagramiXClearCountdown() {
            self.nagramiXCountdownTimer?.invalidate()
            self.nagramiXCountdownTimer = nil
            self.nagramiXCountdownPositionDisposable?.dispose()
            self.nagramiXCountdownPositionDisposable = nil
            if let observer = self.nagramiXCountdownBackgroundObserver {
                NotificationCenter.default.removeObserver(observer)
                self.nagramiXCountdownBackgroundObserver = nil
            }
            if let controller = self.getController() {
                controller.node.nagramiXCountdownPending = false
                controller.node.nagramiXUpdateCountdown(nil)
            }
        }

        private func nagramiXBeginCountdown(generation: UInt64, start: @escaping () -> Void) {
            guard let controller = self.getController(), let camera = controller.camera,
                  !controller.isDismissed, controller.node.nagramiXCountdownPending,
                  self.nagramiXRecordingGeneration == generation else { return }
            guard UIApplication.shared.applicationState == .active else {
                controller.discardVideo()
                controller.completion(nil, nil, nil, nil)
                return
            }
            // Readiness was awaited before the clock starts. Preview/focus frames
            // never reach the writer or live upload during these three seconds.
            let deadline = CACurrentMediaTime() + 3.0
            let finish: () -> Void = { [weak self] in
                guard let self, let controller = self.getController(), !controller.isDismissed,
                      controller.node.nagramiXCountdownPending,
                      self.nagramiXRecordingGeneration == generation else { return }
                self.nagramiXClearCountdown()
                start()
            }
            if controller.cameraState.position != .front {
                finish()
                return
            }
            let timer = SwiftSignalKit.Timer(timeout: 0.05, repeat: true, completion: { [weak self] in
                guard let self, let controller = self.getController(), !controller.isDismissed,
                      controller.node.nagramiXCountdownPending,
                      self.nagramiXRecordingGeneration == generation else { return }
                let remaining = Int(ceil(max(0.0, deadline - CACurrentMediaTime())))
                if remaining == 0 {
                    finish()
                } else {
                    controller.node.nagramiXUpdateCountdown(min(3, remaining))
                }
            }, queue: .mainQueue())
            self.nagramiXCountdownTimer = timer
            timer.start()
            self.nagramiXCountdownPositionDisposable = (camera.position
            |> deliverOnMainQueue).startStrict(next: { position in
                if position != .front { finish() }
            })
        }
