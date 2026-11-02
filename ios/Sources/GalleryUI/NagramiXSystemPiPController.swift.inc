@available(iOS 15.0, *)
private final class NagramiXSystemPiPController: NSObject, AVPictureInPictureControllerDelegate {
    private final class Playback: NSObject, AVPictureInPictureSampleBufferPlaybackDelegate {
        let node: UniversalVideoNode
        private let lock = NSLock()
        private var status: MediaPlayerStatus?
        private var disposable: Disposable?
        var changed: (() -> Void)?

        init(node: UniversalVideoNode) {
            self.node = node
            super.init()
            self.disposable = (node.status |> deliverOnMainQueue).start(next: { [weak self] status in
                guard let self else { return }
                self.lock.lock(); self.status = status; self.lock.unlock()
                self.changed?()
            })
        }
        deinit { self.disposable?.dispose() }
        func snapshot() -> MediaPlayerStatus? {
            self.lock.lock(); defer { self.lock.unlock() }
            return self.status
        }
        func pictureInPictureController(_ controller: AVPictureInPictureController, setPlaying playing: Bool) {
            Queue.mainQueue().async { [weak self] in
                if playing { self?.node.play() } else { self?.node.pause() }
            }
        }
        func pictureInPictureControllerTimeRangeForPlayback(_ controller: AVPictureInPictureController) -> CMTimeRange {
            guard let status = self.snapshot(), status.duration.isFinite, status.duration > 0 else {
                return CMTimeRange(start: .negativeInfinity, duration: .positiveInfinity)
            }
            return CMTimeRange(start: .zero, duration: CMTime(seconds: status.duration, preferredTimescale: 600))
        }
        func pictureInPictureControllerIsPlaybackPaused(_ controller: AVPictureInPictureController) -> Bool {
            guard let status = self.snapshot() else { return true }
            switch status.status {
            case .playing: return false
            case .paused: return true
            case let .buffering(_, whilePlaying, _, _): return !whilePlaying
            }
        }
        func pictureInPictureController(_ controller: AVPictureInPictureController, didTransitionToRenderSize size: CMVideoDimensions) {
            // AVKit obtains the aspect ratio from the original sample buffers.
            // Resizing the source here breaks the return animation, especially
            // with portrait video. Telegram continues rendering its real layer.
        }
        func pictureInPictureController(_ controller: AVPictureInPictureController, skipByInterval interval: CMTime, completion: @escaping () -> Void) {
            Queue.mainQueue().async { [weak self] in
                defer { completion() }
                guard let self, let status = self.snapshot(), interval.seconds.isFinite,
                      status.timestamp.isFinite, status.duration.isFinite, status.duration > 0 else { return }
                let layer = self.node.nagramiXPictureInPictureSourceLayer() as? AVSampleBufferDisplayLayer
                let layerTime = layer?.controlTimebase.map { CMTimeGetSeconds(CMTimebaseGetTime($0)) }
                let current = layerTime.flatMap { $0.isFinite ? $0 : nil } ?? status.timestamp
                self.node.seek(max(0, min(status.duration, current + interval.seconds)))
            }
        }
        func pictureInPictureControllerShouldProhibitBackgroundAudioPlayback(_ controller: AVPictureInPictureController) -> Bool { return false }
    }

    private let node: UniversalVideoNode
    private let mediaManager: MediaManager
    private let audioSession: ManagedAudioSession
    private let playback: Playback
    private let playbackOwner = UUID()
    private let transfer: (NagramiXSystemPiPController) -> Bool
    private let restore: (@escaping (Bool) -> Void) -> Void
    private let ended: (NagramiXSystemPiPController, Bool) -> Void
    private var controller: AVPictureInPictureController?
    private var sourceLayer: CALayer?
    private var possibleObservation: NSKeyValueObservation?
    private var timer: SwiftSignalKit.Timer?
    private let audioObservation = MetaDisposable()
    private let silentAudioLease = MetaDisposable()
    private var managedPlaybackActive = false
    private var requestedAudioLease = false
    private var preparedAt = 0.0
    private var removedDisposable: Disposable?
    private var validate: (() -> Bool)?
    private var acquirePrevious: (() -> Bool)?

    private lazy var lifecycle = NagramiXPiPLifecycle(
        now: { CACurrentMediaTime() }, valid: { [weak self] in self?.validSource() == true },
        prepare: { [weak self] in self?.prepare() },
        readiness: { [weak self] in self?.readiness() ?? .invalid },
        nativeActive: { [weak self] in self?.controller?.isPictureInPictureActive == true },
        start: { [weak self] in
            guard let self else { return }
            NSLog("NagramiX PiP v3: native_start")
            self.controller?.startPictureInPicture()
        }, stop: { [weak self] in self?.controller?.stopPictureInPicture() },
        commit: { [weak self] in
            guard let self else { return false }
            return self.transfer(self)
        }, restore: { [weak self] completion in
            guard let self else { completion(false); return }
            self.restore(completion)
        }, release: { [weak self] in self?.releaseResources() },
        ended: { [weak self] restored in
            guard let self else { return }
            self.ended(self, restored)
        }, changed: { [weak self] in self?.synchronizeTimer() }
    )

    init(context: AccountContext, videoNode: UniversalVideoNode, hiddenMedia: (MessageId, Media)?,
         transfer: @escaping (NagramiXSystemPiPController) -> Bool,
         restore: @escaping (@escaping (Bool) -> Void) -> Void,
         ended: @escaping (NagramiXSystemPiPController, Bool) -> Void) {
        self.node = videoNode
        self.mediaManager = context.sharedContext.mediaManager
        self.audioSession = context.sharedContext.mediaManager.audioSession
        self.playback = Playback(node: videoNode)
        self.transfer = transfer; self.restore = restore; self.ended = ended
        super.init()
        self.playback.changed = { [weak self] in self?.invalidatePlaybackState() }
        self.bindSourceIfNeeded()
        if let (id, _) = hiddenMedia {
            var hadMessage = false
            self.removedDisposable = (context.engine.data.subscribe(TelegramEngine.EngineData.Item.Messages.Message(id: id)) |> deliverOnMainQueue).start(next: { [weak self] message in
                if message != nil { hadMessage = true }
                else if hadMessage { self?.stop() }
            })
        }
    }

    deinit {
        self.timer?.invalidate(); self.possibleObservation?.invalidate()
        self.audioObservation.dispose(); self.silentAudioLease.dispose(); self.removedDisposable?.dispose()
        self.playback.changed = nil
        self.controller?.delegate = nil
        self.controller?.stopPictureInPicture()
        self.controller?.contentSource = nil
        self.node.setNagramiXBackgroundPlayback(id: self.playbackOwner, active: false)
        self.mediaManager.setNagramiXSystemPiPPlayback(id: self.playbackOwner, active: false)
    }

    var nagramiXHasPiPRequest: Bool { self.lifecycle.phase != .idle && self.lifecycle.phase != .finished }
    var nagramiXNativeStartInFlight: Bool {
        self.lifecycle.phase == .starting || self.lifecycle.phase == .active || self.lifecycle.phase == .stopping
    }
    func nagramiXMatchesSource(_ node: UniversalVideoNode, requireLayer: Bool = true) -> Bool {
        guard self.lifecycle.phase != .finished, self.node === node else { return false }
        return !requireLayer || self.sourceLayer == nil || node.nagramiXPictureInPictureSourceLayer() === self.sourceLayer
    }

    func start(acquirePrevious: @escaping () -> Bool, validate: @escaping () -> Bool, completion: @escaping (Bool) -> Void) -> Bool {
        guard self.lifecycle.phase == .idle else { return false }
        self.validate = validate; self.acquirePrevious = acquirePrevious
        return self.lifecycle.begin(timeout: 8.0, completion: completion)
    }

    private func validSource() -> Bool {
        self.validate?() == true && self.nagramiXMatchesSource(self.node, requireLayer: self.nagramiXNativeStartInFlight)
    }

    private func prepare() {
        self.preparedAt = CACurrentMediaTime()
        NSLog("NagramiX PiP v3: prepare_system_session")
        self.mediaManager.setNagramiXSystemPiPPlayback(id: self.playbackOwner, active: true)
        self.node.setNagramiXBackgroundPlayback(id: self.playbackOwner, active: true)
        // Changes only the renderer's category; does not play, unmute or seek.
        self.node.continueWithOverridingAmbientMode(isAmbient: false)
        self.audioObservation.set((combineLatest(self.audioSession.isActive(), self.audioSession.isPlaybackActive()) |> deliverOnMainQueue).start(next: { [weak self] active, playback in
            guard let self else { return }
            self.managedPlaybackActive = active && playback
            self.lifecycle.update()
        }))
    }

    private func bindSourceIfNeeded() {
        guard let layer = self.node.nagramiXPictureInPictureSourceLayer() else { return }
        if self.sourceLayer === layer { return }
        // Before start, a quality switch may replace the renderer. Bind the new
        // layer rather than keeping the first, now detached, layer forever.
        guard self.lifecycle.phase == .idle || self.lifecycle.phase == .preparing else { return }
        self.possibleObservation?.invalidate()
        self.controller?.delegate = nil
        self.controller?.contentSource = nil
        self.controller = nil; self.sourceLayer = nil
        if let sampleLayer = layer as? AVSampleBufferDisplayLayer {
            self.controller = AVPictureInPictureController(contentSource: .init(sampleBufferDisplayLayer: sampleLayer, playbackDelegate: self.playback))
        } else if let playerLayer = layer as? AVPlayerLayer {
            self.controller = AVPictureInPictureController(playerLayer: playerLayer)
        }
        guard let controller = self.controller else { return }
        self.sourceLayer = layer
        controller.delegate = self
        controller.canStartPictureInPictureAutomaticallyFromInline = false
        controller.requiresLinearPlayback = false
        self.possibleObservation = controller.observe(\.isPictureInPicturePossible, options: [.new]) { [weak self] _, _ in
            Queue.mainQueue().async { self?.lifecycle.update() }
        }
        controller.invalidatePlaybackState()
    }

    private func readiness() -> NagramiXPiPLifecycle.Readiness {
        guard UIApplication.shared.applicationState == .active, self.node.view.window != nil else { return .invalid }
        guard self.acquirePrevious?() == true, self.node.ownsContentNode else { return .waiting }
        self.bindSourceIfNeeded()
        guard let layer = self.sourceLayer, let controller = self.controller, layer.superlayer != nil,
              layer.bounds.width > 0, layer.bounds.height > 0, !layer.isHidden else { return .waiting }
        guard !self.audioSession.getIsRecordingActive() else { return .invalid }
        // Let the current audio renderer finish its own asynchronous activation.
        // A second holder must never preempt an already playing video's audio.
        let category: NagramiXPiPAudioPolicy.Category
        switch AVAudioSession.sharedInstance().category {
        case .ambient, .soloAmbient: category = .ambient
        case .playback: category = .playback
        case .playAndRecord: category = .playAndRecord
        default: category = .other
        }
        if controller.isPictureInPicturePossible,
           NagramiXPiPAudioPolicy.isReady(managedPlaybackActive: self.managedPlaybackActive, category: category) {
            return .ready
        }
        if NagramiXPiPAudioPolicy.needsPlaybackLease(managedPlaybackActive: self.managedPlaybackActive,
                category: category, elapsed: CACurrentMediaTime() - self.preparedAt, alreadyRequested: self.requestedAudioLease) {
            self.requestedAudioLease = true
            NSLog("NagramiX PiP v3: playback_audio_activation")
            self.silentAudioLease.set(self.audioSession.push(audioSessionType: .play(mixWithOthers: true), activate: { [weak self] _ in
                Queue.mainQueue().async { self?.lifecycle.update() }
            }, deactivate: { [weak self] _ in
                Queue.mainQueue().async { self?.silentAudioLease.set(nil) }
                return .complete()
            }))
        }
        return .waiting
    }

    private func synchronizeTimer() {
        guard self.lifecycle.needsTimer else { self.timer?.invalidate(); self.timer = nil; return }
        guard self.timer == nil else { return }
        let timer = SwiftSignalKit.Timer(timeout: 0.1, repeat: true, completion: { [weak self] in self?.lifecycle.update() }, queue: Queue.mainQueue())
        self.timer = timer; timer.start()
    }
    private func releaseResources() {
        self.timer?.invalidate(); self.timer = nil
        self.validate = nil; self.acquirePrevious = nil
        self.audioObservation.set(nil); self.silentAudioLease.set(nil)
        self.possibleObservation?.invalidate(); self.possibleObservation = nil
        self.controller?.delegate = nil
        self.controller?.stopPictureInPicture()
        self.controller?.contentSource = nil
        self.controller = nil; self.sourceLayer = nil
        self.node.setNagramiXBackgroundPlayback(id: self.playbackOwner, active: false)
        self.mediaManager.setNagramiXSystemPiPPlayback(id: self.playbackOwner, active: false)
    }
    func nagramiXCancelDirectionalPiP() { self.lifecycle.cancelPreparation() }
    func nagramiXCancelSwipePreparation() -> Bool { return !self.nagramiXHasPiPRequest }
    func updateIsCentral(isCentral: Bool) { if !isCentral { self.lifecycle.cancelPreparation() } }
    func invalidatePlaybackState() {
        self.controller?.invalidatePlaybackState()
        self.lifecycle.update()
    }
    func requestExpand() {
        self.lifecycle.restoreInterface { [weak self] restored in if restored { self?.stop() } }
    }
    func stop() { self.lifecycle.stopRequested() }

    func pictureInPictureControllerDidStartPictureInPicture(_ controller: AVPictureInPictureController) {
        Queue.mainQueue().async { [weak self] in
            guard let self, self.controller === controller else { return }
            self.lifecycle.didStart()
        }
    }
    func pictureInPictureController(_ controller: AVPictureInPictureController, failedToStartPictureInPictureWithError error: Error) {
        let error = error as NSError
        NSLog("NagramiX PiP v3: failure %@/%ld", error.domain, error.code)
        Queue.mainQueue().async { [weak self] in
            guard let self, self.controller === controller else { return }
            self.lifecycle.failedToStart()
        }
    }
    func pictureInPictureControllerDidStopPictureInPicture(_ controller: AVPictureInPictureController) {
        Queue.mainQueue().async { [weak self] in
            guard let self, self.controller === controller else { return }
            self.lifecycle.didStop()
        }
    }
    func pictureInPictureController(_ controller: AVPictureInPictureController, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler completion: @escaping (Bool) -> Void) {
        Queue.mainQueue().async { [weak self] in
            guard let self, self.controller === controller else { completion(false); return }
            self.lifecycle.restoreInterface(completion: completion)
        }
    }
}
