@available(iOS 15.0, *)
private final class NativePictureInPictureContentImpl: NSObject, AVPictureInPictureControllerDelegate {
    private final class PlaybackDelegate: NSObject, AVPictureInPictureSampleBufferPlaybackDelegate {
        private let node: UniversalVideoNode
        private let layer: AVSampleBufferDisplayLayer
        private var disposable: Disposable?
        private var status: MediaPlayerStatus?
        private let lock = NSLock()
        var changed: (() -> Void)?

        init(node: UniversalVideoNode, layer: AVSampleBufferDisplayLayer) {
            self.node = node
            self.layer = layer
            super.init()
            self.disposable = (node.status |> deliverOnMainQueue).start(next: { [weak self] value in
                guard let self else { return }
                self.lock.lock(); self.status = value; self.lock.unlock()
                self.changed?()
            })
        }

        deinit { self.disposable?.dispose() }

        private func snapshot() -> MediaPlayerStatus? {
            self.lock.lock(); defer { self.lock.unlock() }
            return self.status
        }

        func pictureInPictureController(_ controller: AVPictureInPictureController, setPlaying playing: Bool) {
            Queue.mainQueue().async { [weak self] in
                // AVKit sets a desired state; toggling inverted duplicate commands.
                if playing { self?.node.play() } else { self?.node.pause() }
            }
        }

        func pictureInPictureControllerTimeRangeForPlayback(_ controller: AVPictureInPictureController) -> CMTimeRange {
            let value = self.layer.controlTimebase.map { CMTimeGetSeconds(CMTimebaseGetTime($0)) } ?? 0
            let current = value.isFinite ? value : 0
            let start = min(0, current)
            guard let status = self.snapshot(), status.duration.isFinite, status.duration > 0 else {
                return CMTimeRange(start: CMTime(seconds: start, preferredTimescale: 600), duration: .positiveInfinity)
            }
            let end = max(status.duration, current + 0.001)
            return CMTimeRange(start: CMTime(seconds: start, preferredTimescale: 600), duration: CMTime(seconds: end - start, preferredTimescale: 600))
        }

        func pictureInPictureControllerIsPlaybackPaused(_ controller: AVPictureInPictureController) -> Bool {
            guard let status = self.snapshot() else { return true }
            switch status.status {
            case .playing: return false
            case .paused: return true
            case let .buffering(_, whilePlaying, _, _): return !whilePlaying
            }
        }

        func pictureInPictureController(_ controller: AVPictureInPictureController, didTransitionToRenderSize size: CMVideoDimensions) {}

        func pictureInPictureController(_ controller: AVPictureInPictureController, skipByInterval interval: CMTime, completion: @escaping () -> Void) {
            Queue.mainQueue().async { [weak self] in
                defer { completion() }
                guard let self, let status = self.snapshot(), interval.seconds.isFinite, status.timestamp.isFinite,
                      status.duration.isFinite, status.duration > 0 else { return }
                self.node.seek(max(0, min(status.duration, status.timestamp + interval.seconds)))
            }
        }

        func pictureInPictureControllerShouldProhibitBackgroundAudioPlayback(_ controller: AVPictureInPictureController) -> Bool { return false }
    }

    private let node: UniversalVideoNode
    private let sourceLayer: CALayer
    private var controller: AVPictureInPictureController?
    private var playbackDelegate: PlaybackDelegate?
    private var possibleObservation: NSKeyValueObservation?
    private var timeout: SwiftSignalKit.Timer?
    private var removedDisposable: Disposable?
    private var retired = false
    private let audioSession: ManagedAudioSession
    private let audioReadiness = MetaDisposable()
    private let silentAudioLease = MetaDisposable()
    private var audioReady = false
    private let willBegin: (NativePictureInPictureContentImpl) -> Bool
    private let didBegin: (NativePictureInPictureContentImpl) -> Void
    private let didEnd: (NativePictureInPictureContentImpl) -> Void
    private let expand: (@escaping (Bool) -> Void) -> Void
    private var didExpand = false

    private lazy var session = NagramiXPiPPlaybackSession(
        prepare: { [weak self] in
            self?.node.setCanPlaybackWithoutHierarchy(true)
            self?.node.continueWithOverridingAmbientMode(isAmbient: false)
            self?.prepareAudioSession()
            self?.controller?.invalidatePlaybackState()
        }, possible: { [weak self] in self?.nagramiXCanStartPictureInPicture == true },
        active: { [weak self] in self?.controller?.isPictureInPictureActive == true },
        start: { [weak self] in self?.controller?.startPictureInPicture() },
        stop: { [weak self] in self?.controller?.stopPictureInPicture() },
        transfer: { [weak self] in
            guard let self, self.willBegin(self) else { return false }
            self.timeout?.invalidate(); self.timeout = nil
            self.didBegin(self)
            return true
        }, release: { [weak self] in
            guard let self else { return }
            self.timeout?.invalidate(); self.timeout = nil
            self.retired = true
            self.audioReady = false
            self.audioReadiness.set(nil)
            self.silentAudioLease.set(nil)
            self.node.setCanPlaybackWithoutHierarchy(false)
        }, ended: { [weak self] in
            guard let self else { return }
            self.didEnd(self)
        }
    )

    init?(context: AccountContext, mediaManager: MediaManager, accountId: AccountRecordId, hiddenMedia: (MessageId, Media)?, videoNode: UniversalVideoNode, canSkip: Bool, willBegin: @escaping (NativePictureInPictureContentImpl) -> Bool, didBegin: @escaping (NativePictureInPictureContentImpl) -> Void, didEnd: @escaping (NativePictureInPictureContentImpl) -> Void, expand: @escaping (@escaping (Bool) -> Void) -> Void) {
        guard let sourceLayer = videoNode.nagramiXPictureInPictureSourceLayer(),
              sourceLayer is AVSampleBufferDisplayLayer || sourceLayer is AVPlayerLayer else { return nil }
        self.node = videoNode
        self.audioSession = context.sharedContext.mediaManager.audioSession
        self.sourceLayer = sourceLayer
        self.willBegin = willBegin; self.didBegin = didBegin
        self.didEnd = didEnd; self.expand = expand
        super.init()
        if let layer = self.sourceLayer as? AVSampleBufferDisplayLayer {
            let delegate = PlaybackDelegate(node: videoNode, layer: layer)
            self.playbackDelegate = delegate
            self.controller = AVPictureInPictureController(contentSource: .init(sampleBufferDisplayLayer: layer, playbackDelegate: delegate))
            delegate.changed = { [weak self] in self?.invalidatePlaybackState() }
        } else if let layer = self.sourceLayer as? AVPlayerLayer {
            self.controller = AVPictureInPictureController(playerLayer: layer)
        }
        if let controller = self.controller {
            controller.delegate = self
            // Preparing a controller does not authorize an automatic start.
            controller.canStartPictureInPictureAutomaticallyFromInline = false
            controller.requiresLinearPlayback = !canSkip
            self.possibleObservation = controller.observe(\.isPictureInPicturePossible, options: [.new]) { [weak self] _, _ in
                Queue.mainQueue().async { self?.session.readinessChanged() }
            }
            controller.invalidatePlaybackState()
        }
        guard self.controller != nil else { return nil }
        NSLog("NagramiX PiP engine: bound=%@", self.sourceLayer is AVPlayerLayer ? "playerLayer" : "sampleBuffer")
        if let (messageId, _) = hiddenMedia {
            var hadMessage = false
            self.removedDisposable = (context.engine.data.subscribe(TelegramEngine.EngineData.Item.Messages.Message(id: messageId)) |> deliverOnMainQueue).start(next: { [weak self] message in
                if message != nil { hadMessage = true }
                else if hadMessage { self?.stop() }
            })
        }
    }

    deinit {
        self.audioReadiness.dispose(); self.silentAudioLease.dispose()
        self.removedDisposable?.dispose(); self.possibleObservation?.invalidate(); self.timeout?.invalidate()
        self.controller?.delegate = nil
        self.controller?.stopPictureInPicture()
        self.controller?.contentSource = nil
        self.playbackDelegate?.changed = nil
        self.node.setCanPlaybackWithoutHierarchy(false)
    }

    var nagramiXHasPiPRequest: Bool { self.session.phase != .idle || self.controller?.isPictureInPictureActive == true }
    var nagramiXNativeStartInFlight: Bool { self.session.phase == .starting || self.session.phase == .active }

    func nagramiXMatchesSource(_ node: UniversalVideoNode, requireLayer: Bool = true) -> Bool {
        guard !self.retired, self.node === node else { return false }
        return !requireLayer || node.nagramiXPictureInPictureSourceLayer() === self.sourceLayer
    }

    var nagramiXCanStartPictureInPicture: Bool {
        self.audioReady && self.nagramiXMatchesSource(self.node) && self.controller?.isPictureInPicturePossible == true
    }

    private func prepareAudioSession() {
        // Silent clips may have no audio renderer to acquire .playback for PiP.
        // Use Telegram's manager, never overwrite its category behind its back.
        self.audioReady = false
        self.audioReadiness.set((combineLatest(self.audioSession.isActive(), self.audioSession.isPlaybackActive()) |> take(1) |> deliverOnMainQueue).start(next: { [weak self] active, playback in
            guard let self, self.session.phase == .waiting else { return }
            if active && playback {
                self.audioReady = true
                self.invalidatePlaybackState()
                return
            }
            guard !self.audioSession.getIsRecordingActive() else { return }
            self.silentAudioLease.set(self.audioSession.push(audioSessionType: .play(mixWithOthers: true), activate: { [weak self] _ in
                Queue.mainQueue().async {
                    guard let self, self.session.phase == .waiting else { return }
                    self.audioReady = true
                    self.invalidatePlaybackState()
                }
            }, deactivate: { [weak self] _ in
                Queue.mainQueue().async { self?.audioReady = false }
                return .complete()
            }))
        }))
    }

    func nagramiXRequestDirectionalPiP(timeout: Double = 8, canCommit: @escaping () -> Bool, completion: @escaping (Bool) -> Void) -> Bool {
        guard !self.retired, self.controller != nil else { return false }
        let timer = SwiftSignalKit.Timer(timeout: max(0.1, timeout), repeat: false, completion: { [weak self] in self?.session.timedOut() }, queue: Queue.mainQueue())
        self.timeout = timer
        timer.start()
        let accepted = self.session.request(validate: canCommit, completion: completion)
        if !accepted { timer.invalidate(); self.timeout = nil }
        return accepted
    }

    func nagramiXCancelDirectionalPiP() { self.session.cancelPreparation() }
    func nagramiXCancelSwipePreparation() -> Bool {
        guard !self.nagramiXHasPiPRequest else { return false }
        return true
    }
    func updateIsCentral(isCentral: Bool) { if !isCentral { self.session.cancelPreparation() } }
    func invalidatePlaybackState() { self.controller?.invalidatePlaybackState(); self.session.readinessChanged() }
    func requestExpand() { self.stop() }
    func stop() { self.session.stopRequested() }

    func pictureInPictureControllerWillStartPictureInPicture(_ controller: AVPictureInPictureController) {
        // No gallery dismissal here: willStart is not a successful start.
    }
    func pictureInPictureControllerDidStartPictureInPicture(_ controller: AVPictureInPictureController) {
        Queue.mainQueue().async { [weak self] in
            guard let self, self.controller === controller else { return }
            self.session.didStart()
        }
    }
    func pictureInPictureController(_ controller: AVPictureInPictureController, failedToStartPictureInPictureWithError error: Error) {
        let error = error as NSError
        NSLog("NagramiX PiP engine: failed %@/%ld", error.domain, error.code)
        Queue.mainQueue().async { [weak self] in
            guard let self, self.controller === controller else { return }
            self.session.failedToStart()
        }
    }
    func pictureInPictureControllerDidStopPictureInPicture(_ controller: AVPictureInPictureController) {
        Queue.mainQueue().async { [weak self] in
            guard let self, self.controller === controller else { return }
            self.session.didStop()
        }
    }
    func pictureInPictureController(_ controller: AVPictureInPictureController, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler completion: @escaping (Bool) -> Void) {
        Queue.mainQueue().async { [weak self] in
            guard let self, self.controller === controller, !self.didExpand else { completion(false); return }
            self.didExpand = true
            self.expand { completion($0) }
        }
    }
}
