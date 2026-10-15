        private var nagramiXStoppingRecording = false
        private var nagramiXRecordingGeneration: UInt64 = 0
        private var nagramiXCancelled = false
        private var nagramiXWriterRequested = false
        private var nagramiXSwitchingCamera = false
        private var nagramiXStopAfterCameraSwitch = false
        private var nagramiXPendingSwitchResult: VideoMessageCameraScreen.CaptureResult?
        private let nagramiXStopDisposable = MetaDisposable()
        private let nagramiXReadyDisposable = MetaDisposable()
        private var nagramiXPreparationTimer: SwiftSignalKit.Timer?
        private var nagramiXCountdownTimer: SwiftSignalKit.Timer?
        private var nagramiXCountdownPositionDisposable: Disposable?
        private var nagramiXCountdownBackgroundObserver: NSObjectProtocol?

        private func nagramiXAbortRecording() {
            guard !self.nagramiXCancelled, let controller = self.getController(), !controller.isDismissed else { return }
            self.cancelVideoRecording()
            controller.discardVideo()
            controller.completion(nil, nil, nil, nil)
        }

        private func nagramiXWatchPreparation(generation: UInt64) {
            self.nagramiXPreparationTimer?.invalidate()
            let timer = SwiftSignalKit.Timer(timeout: 12.0, repeat: false, completion: { [weak self] in
                guard let self, self.nagramiXRecordingGeneration == generation else { return }
                self.nagramiXAbortRecording()
            }, queue: .mainQueue())
            self.nagramiXPreparationTimer = timer
            timer.start()
        }

        private func nagramiXArmPreparation(controller: VideoMessageCameraScreen) {
            controller.node.nagramiXCountdownPending = true
            if self.nagramiXCountdownBackgroundObserver == nil {
                self.nagramiXCountdownBackgroundObserver = NotificationCenter.default.addObserver(forName: UIApplication.willResignActiveNotification, object: nil, queue: .main) { [weak self] _ in
                    guard let self, self.getController()?.node.nagramiXCountdownPending == true else { return }
                    self.nagramiXAbortRecording()
                }
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
                controller.node.nagramiXCameraSwitchPending = false
                controller.node.nagramiXUpdateCountdown(nil)
            }
        }

        private var nagramiXRetainedDuration: Double {
            guard let controller = self.getController() else { return 0.0 }
            return controller.node.results.reduce(0.0, { value, result in
                if case let .video(video) = result { return value + video.duration }
                return value
            })
        }

        private func nagramiXAwaitCamera(generation: UInt64, ready: @escaping () -> Void) {
            guard let controller = self.getController(), let camera = controller.camera else { return }
            // The position signal can arrive before the hardware reconfiguration commits.
            let request = MetaDisposable()
            self.nagramiXReadyDisposable.set(request)
            request.set((combineLatest(camera.position, camera.modeChange)
            |> filter { _, mode in
                if case .none = mode { return true }
                return false
            }
            |> take(1)
            |> deliverOnMainQueue).startStrict(next: { [weak self] _, _ in
                guard let self, let controller = self.getController(), !controller.isDismissed,
                      !self.nagramiXCancelled, !self.nagramiXStopAfterCameraSwitch,
                      self.nagramiXRecordingGeneration == generation else { return }
                controller.node.withReadyCamera { [weak self] in
                    guard let self, let controller = self.getController(), !controller.isDismissed,
                          !self.nagramiXCancelled, !self.nagramiXStopAfterCameraSwitch,
                          self.nagramiXRecordingGeneration == generation else { return }
                    guard UIApplication.shared.applicationState == .active else {
                        self.nagramiXAbortRecording()
                        return
                    }
                    ready()
                }
            }))
        }

        private func nagramiXPrepareWriter(generation: UInt64) {
            guard let controller = self.getController(), let camera = controller.camera,
                  !controller.isDismissed, !self.nagramiXCancelled,
                  self.nagramiXRecordingGeneration == generation else { return }
            if controller.cameraState.position == .front && NagramiXTabSettings.current.selfieCountdown {
                controller.node.nagramiXUpdateCountdown(3)
                camera.focus(at: CGPoint(x: 0.5, y: 0.5), autoFocus: true)
                let deadline = CACurrentMediaTime() + 3.0
                let finish: () -> Void = { [weak self] in
                    guard let self, self.nagramiXCountdownTimer != nil, self.nagramiXRecordingGeneration == generation,
                          !self.nagramiXStopAfterCameraSwitch, !self.nagramiXCancelled else { return }
                    self.nagramiXCountdownTimer?.invalidate()
                    self.nagramiXCountdownTimer = nil
                    self.nagramiXCountdownPositionDisposable?.dispose()
                    self.nagramiXCountdownPositionDisposable = nil
                    if CACurrentMediaTime() >= deadline, self.getController()?.cameraState.position == .front {
                        self.nagramiXStartWriter(generation: generation, countdownComplete: true)
                    } else {
                        self.nagramiXAwaitCamera(generation: generation, ready: { [weak self] in
                            self?.nagramiXStartWriter(generation: generation, countdownComplete: false)
                        })
                    }
                }
                let timer = SwiftSignalKit.Timer(timeout: 0.05, repeat: true, completion: { [weak self] in
                    guard let self, self.nagramiXRecordingGeneration == generation, !self.nagramiXStopAfterCameraSwitch else { return }
                    let remaining = Int(ceil(max(0.0, deadline - CACurrentMediaTime())))
                    if remaining == 0 { finish() }
                    else { self.getController()?.node.nagramiXUpdateCountdown(min(3, remaining)) }
                }, queue: .mainQueue())
                self.nagramiXCountdownTimer = timer
                timer.start()
                self.nagramiXCountdownPositionDisposable = (camera.position
                |> deliverOnMainQueue).startStrict(next: { position in
                    if position != .front { finish() }
                })
            } else {
                Queue.mainQueue().after(0.15) { [weak self] in
                    self?.nagramiXStartWriter(generation: generation, countdownComplete: false)
                }
            }
        }

        private func nagramiXStartWriter(generation: UInt64, countdownComplete: Bool) {
            guard let controller = self.getController(), let camera = controller.camera,
                  !controller.isDismissed, !self.nagramiXCancelled, !self.nagramiXStopAfterCameraSwitch,
                  !self.nagramiXWriterRequested, !self.nagramiXStoppingRecording,
                  self.nagramiXRecordingGeneration == generation else { return }
            guard UIApplication.shared.applicationState == .active else {
                self.nagramiXAbortRecording()
                return
            }
            // A flip can happen in the native delayed-start interval.
            if controller.cameraState.position == .front && NagramiXTabSettings.current.selfieCountdown && !countdownComplete {
                self.nagramiXAwaitCamera(generation: generation, ready: { [weak self] in
                    self?.nagramiXPrepareWriter(generation: generation)
                })
                return
            }
            if let result = self.nagramiXPendingSwitchResult {
                self.nagramiXPendingSwitchResult = nil
                controller.node.nagramiXAppendSwitchResult(result)
            }
            self.nagramiXClearCountdown()
            self.nagramiXReadyDisposable.set(nil)
            self.nagramiXSwitchingCamera = false
            self.nagramiXWriterRequested = true
            // Give every writer a fresh token, including fragments after a flip.
            self.nagramiXRecordingGeneration &+= 1
            let writerGeneration = self.nagramiXRecordingGeneration
            let initialDuration = self.nagramiXRetainedDuration
            controller.recordingStartTime = CACurrentMediaTime() - initialDuration
            self.nagramiXWatchPreparation(generation: writerGeneration)
            let request = MetaDisposable()
            self.resultDisposable.set(request)
            request.set((camera.startRecording()
            |> deliverOnMainQueue).startStrict(next: { [weak self] data in
                guard let self, let controller = self.getController(), !controller.isDismissed,
                      !self.nagramiXCancelled, self.nagramiXRecordingGeneration == writerGeneration,
                      self.nagramiXWriterRequested else { return }
                if data.duration > 0.0 {
                    self.nagramiXPreparationTimer?.invalidate()
                    self.nagramiXPreparationTimer = nil
                }
                let duration = initialDuration + data.duration
                controller.updateCameraState({ $0.updatedDuration(duration) }, transition: .easeInOut(duration: 0.1))
                if initialDuration.isZero { controller.node.setupLiveUpload(filePath: data.filePath) }
                if duration > 59.5 { controller.onStop() }
            }, error: { [weak self] _ in
                guard let self, self.nagramiXRecordingGeneration == writerGeneration else { return }
                self.nagramiXAbortRecording()
            }, completed: { [weak self] in
                guard let self, self.nagramiXRecordingGeneration == writerGeneration, !self.nagramiXStoppingRecording else { return }
                self.nagramiXAbortRecording()
            }))
        }

        func startVideoRecording(pressing: Bool) {
            guard !self.nagramiXStoppingRecording, !self.nagramiXSwitchingCamera, !self.nagramiXCancelled,
                  let controller = self.getController(), controller.camera != nil, !controller.isDismissed,
                  case .none = controller.cameraState.recording else { return }
            let currentTimestamp = CACurrentMediaTime()
            if let last = controller.lastActionTimestamp, currentTimestamp - last < 0.5 { return }
            controller.lastActionTimestamp = currentTimestamp
            self.nagramiXRecordingGeneration &+= 1
            let generation = self.nagramiXRecordingGeneration
            self.nagramiXStopAfterCameraSwitch = false
            self.nagramiXArmPreparation(controller: controller)
            self.nagramiXWatchPreparation(generation: generation)
            let initialDuration = controller.node.previewState?.composition.duration.seconds ?? self.nagramiXRetainedDuration
            controller.node.resumeCameraCapture()
            controller.node.dismissAllTooltips()
            controller.updateCameraState({ $0.updatedRecording(pressing ? .holding : .handsFree).updatedDuration(initialDuration) }, transition: .spring(duration: 0.4))
            controller.updatePreviewState({ _ in nil }, transition: .spring(duration: 0.4))
            self.nagramiXAwaitCamera(generation: generation, ready: { [weak self] in
                self?.nagramiXPrepareWriter(generation: generation)
            })
            if initialDuration > 0.0 { controller.onResume() }
            if controller.cameraState.position == .front && controller.cameraState.flashMode == .on { self.updateScreenBrightness() }
        }

        private func nagramiXSwitchToSelfie() {
            guard !self.nagramiXStoppingRecording, !self.nagramiXSwitchingCamera,
                  let controller = self.getController(), let camera = controller.camera else { return }
            self.nagramiXSwitchingCamera = true
            self.nagramiXStopAfterCameraSwitch = false
            self.nagramiXArmPreparation(controller: controller)
            controller.node.nagramiXCameraSwitchPending = true
            self.nagramiXStopWriter(forCameraSwitch: true, camera: camera)
        }

        private func nagramiXFinishStop(_ result: VideoMessageCameraScreen.CaptureResult) {
            guard let controller = self.getController(), !controller.isDismissed, !self.nagramiXCancelled else { return }
            self.nagramiXPreparationTimer?.invalidate()
            self.nagramiXPreparationTimer = nil
            self.nagramiXClearCountdown()
            self.nagramiXReadyDisposable.set(nil)
            self.nagramiXRestoreBrightness()
            self.nagramiXStoppingRecording = false
            self.nagramiXSwitchingCamera = false
            self.nagramiXStopAfterCameraSwitch = false
            self.nagramiXPendingSwitchResult = nil
            self.completion.invoke(result)
            controller.updateCameraState({ $0.updatedRecording(.none) }, transition: .spring(duration: 0.4))
        }

        private func nagramiXStopWriter(forCameraSwitch: Bool, camera: CameraProtocol) {
            self.nagramiXStoppingRecording = true
            self.nagramiXPreparationTimer?.invalidate()
            self.nagramiXPreparationTimer = nil
            let generation = self.nagramiXRecordingGeneration
            var received = false
            let request = MetaDisposable()
            self.nagramiXStopDisposable.set(request)
            // Keep the start subscription alive until the writer has finished preparing/stopping.
            request.set((camera.stopRecording()
            |> timeout(12.0, queue: .mainQueue(), alternate: .single(.failed))
            |> deliverOnMainQueue).startStrict(next: { [weak self] result in
                received = true
                guard let self, let controller = self.getController(), !controller.isDismissed,
                      !self.nagramiXCancelled, self.nagramiXRecordingGeneration == generation else { return }
                self.resultDisposable.set(nil)
                self.nagramiXWriterRequested = false
                guard case let .finished(main, _, duration, _, _) = result, duration.isFinite, duration > 0.0 else {
                    self.nagramiXAbortRecording()
                    return
                }
                let capture = VideoMessageCameraScreen.CaptureResult.video(.init(videoPath: main.path, dimensions: PixelDimensions(main.dimensions), duration: duration, thumbnail: main.thumbnail))
                if forCameraSwitch && !self.nagramiXStopAfterCameraSwitch {
                    self.nagramiXStoppingRecording = false
                    self.nagramiXPendingSwitchResult = capture
                    let totalDuration = self.nagramiXRetainedDuration + duration
                    controller.updateCameraState({ $0.updatedDuration(totalDuration) }, transition: .immediate)
                    if totalDuration > 59.5 {
                        controller.onStop()
                        return
                    }
                    camera.setPosition(.front)
                    camera.setTorchActive(false)
                    self.hapticFeedback.impact(.veryLight)
                    self.updateScreenBrightness(isFrontCamera: true)
                    self.nagramiXWatchPreparation(generation: generation)
                    self.nagramiXAwaitCamera(generation: generation, ready: { [weak self] in
                        self?.nagramiXSwitchingCamera = false
                        self?.nagramiXPrepareWriter(generation: generation)
                    })
                } else {
                    self.nagramiXFinishStop(capture)
                }
            }, completed: { [weak self] in
                guard !received, let self, self.nagramiXRecordingGeneration == generation else { return }
                self.nagramiXAbortRecording()
            }))
        }

        func stopVideoRecording() {
            guard let controller = self.getController(), let camera = controller.camera, !self.nagramiXCancelled else { return }
            if controller.node.nagramiXCameraSwitchPending {
                guard !self.nagramiXStopAfterCameraSwitch else { return }
                self.nagramiXStopAfterCameraSwitch = true
                self.nagramiXReadyDisposable.set(nil)
                self.nagramiXCountdownTimer?.invalidate()
                controller.node.nagramiXUpdateCountdown(nil)
                if let result = self.nagramiXPendingSwitchResult {
                    // Let send/preview install its resultsPipe subscription before publishing.
                    let generation = self.nagramiXRecordingGeneration
                    Queue.mainQueue().async { [weak self] in
                        guard let self, self.nagramiXRecordingGeneration == generation else { return }
                        self.nagramiXFinishStop(result)
                    }
                }
                return
            }
            if controller.node.nagramiXCountdownPending {
                self.nagramiXAbortRecording()
                return
            }
            guard !self.nagramiXStoppingRecording, self.nagramiXWriterRequested else { return }
            controller.lastActionTimestamp = CACurrentMediaTime()
            self.nagramiXStopWriter(forCameraSwitch: false, camera: camera)
            self.nagramiXRestoreBrightness()
        }

        func lockVideoRecording() {
            guard !self.nagramiXCancelled, let controller = self.getController(), !controller.isDismissed else { return }
            controller.updateCameraState({ $0.updatedRecording(.handsFree) }, transition: .spring(duration: 0.4))
        }

        private func nagramiXRestoreBrightness() {
            if let initialBrightness = self.initialBrightness {
                self.initialBrightness = nil
                self.brightnessArguments = (CACurrentMediaTime(), 0.2, UIScreen.main.brightness, initialBrightness)
                self.animateBrightnessChange()
            }
        }

        func cancelVideoRecording() {
            self.nagramiXCancelled = true
            self.nagramiXRecordingGeneration &+= 1
            self.nagramiXClearCountdown()
            self.nagramiXPreparationTimer?.invalidate()
            self.nagramiXPreparationTimer = nil
            self.nagramiXReadyDisposable.set(nil)
            self.nagramiXStopDisposable.set(nil)
            self.resultDisposable.set(nil)
            self.nagramiXPendingSwitchResult = nil
            self.nagramiXWriterRequested = false
            self.nagramiXRestoreBrightness()
        }
