import Foundation
import UIKit
import AVKit
import Display
import SwiftSignalKit
import AccountContext
import TelegramCore
import UniversalMediaPlayer
import TelegramAudio

// Coordinates UIKit restoration and AVKit stop callbacks in either order.
private struct NagramiXSinglePiPRestoration {
    private(set) var isRestoring = false
    private(set) var didStop = false
    private var requested = false
    mutating func begin() -> Bool {
        guard !self.requested, !self.didStop else { return false }
        self.requested = true; self.isRestoring = true
        return true
    }
    mutating func stopped() -> Bool {
        guard !self.didStop else { return false }
        self.didStop = true
        return !self.isRestoring
    }
    mutating func restorationFinished() -> Bool {
        guard self.isRestoring else { return false }
        self.isRestoring = false
        return self.didStop
    }
}

// One AVKit session holds the gallery's real decoder and its display layer.
// It is created only for an explicit button or swipe request.
final class NagramiXNativePlayerPiP: NSObject, AVPictureInPictureControllerDelegate {
    struct ReturnState {
        let timestamp: Double
        let playing: Bool
        let rate: Double
    }
    private final class Playback: NSObject, AVPictureInPictureSampleBufferPlaybackDelegate {
        let node: UniversalVideoNode
        let layer: AVSampleBufferDisplayLayer
        private let lock = NSLock()
        private var status: MediaPlayerStatus?
        private var disposable: Disposable?
        var changed: ((MediaPlayerStatus?) -> Void)?
        init(node: UniversalVideoNode, layer: AVSampleBufferDisplayLayer) {
            self.node = node; self.layer = layer
            super.init()
            self.disposable = (node.status |> deliverOnMainQueue).start(next: { [weak self] status in
                guard let self else { return }
                self.lock.lock(); self.status = status; self.lock.unlock()
                self.changed?(status)
            })
        }
        deinit { self.disposable?.dispose() }
        private func snapshot() -> MediaPlayerStatus? {
            self.lock.lock(); defer { self.lock.unlock() }; return self.status
        }
        func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, setPlaying playing: Bool) {
            Queue.mainQueue().async { [weak self] in
                guard let self else { return }
                if playing { self.node.play() } else { self.node.pause() }
            }
        }
        func pictureInPictureControllerTimeRangeForPlayback(_ pictureInPictureController: AVPictureInPictureController) -> CMTimeRange {
            let raw = self.layer.controlTimebase.map { CMTimeGetSeconds(CMTimebaseGetTime($0)) } ?? 0
            let time = raw.isFinite ? raw : 0
            let start = min(0, time)
            guard let value = self.snapshot(), value.duration.isFinite, value.duration > 0 else {
                return CMTimeRange(start: CMTime(seconds: start, preferredTimescale: 600), duration: .positiveInfinity)
            }
            return CMTimeRange(start: CMTime(seconds: start, preferredTimescale: 600), duration: CMTime(seconds: max(value.duration, time + 0.001) - start, preferredTimescale: 600))
        }
        func pictureInPictureControllerIsPlaybackPaused(_ pictureInPictureController: AVPictureInPictureController) -> Bool {
            guard let value = self.snapshot() else { return true }
            switch value.status {
            case .playing: return false
            case .paused: return true
            case let .buffering(_, whilePlaying, _, _): return !whilePlaying
            }
        }
        func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, didTransitionToRenderSize newRenderSize: CMVideoDimensions) {}
        func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, skipByInterval skipInterval: CMTime, completion completionHandler: @escaping () -> Void) {
            Queue.mainQueue().async { [weak self] in
                defer { completionHandler() }
                guard let self, let status = self.snapshot(), skipInterval.seconds.isFinite,
                      status.duration.isFinite, status.duration > 0 else { return }
                let value = self.layer.controlTimebase.map { CMTimeGetSeconds(CMTimebaseGetTime($0)) } ?? status.timestamp
                guard value.isFinite else { return }
                self.node.seek(max(0, min(status.duration, value + skipInterval.seconds)))
            }
        }
        func pictureInPictureControllerShouldProhibitBackgroundAudioPlayback(_ pictureInPictureController: AVPictureInPictureController) -> Bool { return false }
    }

    private static var current: NagramiXNativePlayerPiP?
    static var isBusy: Bool { return self.current != nil }
    private let node: UniversalVideoNode
    private let resourceId: String
    private let title: String
    private let context: AccountContext
    private let owner = UUID()
    private let valid: () -> Bool
    private let sourceState: () -> ReturnState?
    private let didStart: () -> Void
    private let restore: (ReturnState, @escaping (Bool) -> Void) -> Void
    private let finish: (Double, Bool, Bool, Bool) -> Void
    private let failed: (String) -> Void
    private var retainGallery: ViewController?
    private var layer: CALayer?
    private var playerController: AVPictureInPictureController?
    private var playback: Playback?
    private var observation: NSKeyValueObservation?
    private var statusDisposable: Disposable?
    private var silentAudioLease: Disposable?
    private let audioReadiness = MetaDisposable()
    private var requestedSilentAudio = false
    private let preparedAt = CACurrentMediaTime()
    private var timer: Foundation.Timer?
    private var deadline = CACurrentMediaTime() + 12
    private var initial: ReturnState
    private var lastStatus: MediaPlayerStatus?
    private var lastPlaybackIntent: Bool?
    private var lastDuration: Double?
    private var starting = false
    private var startFailure: String?
    private var active = false
    private var stopping = false
    private var ended = false
    private var restored = false
    private var restoration = NagramiXSinglePiPRestoration()
    private var restoreCompletion: ((Bool) -> Void)?
    private var restoreTimer: Foundation.Timer?
    private var transferred = false
    private var openingSameResource = false
    private var openingCompletion: ((ReturnState?) -> Void)?
    private var pendingStopPlaying: Bool?
    var isActive: Bool { self.active && !self.ended }

    @discardableResult
    static func takeForOpening(resourceId: String?, completion: @escaping (ReturnState?) -> Void) -> Bool {
        assert(Thread.isMainThread)
        guard let session = self.current, !session.ended, session.openingCompletion == nil else { return false }
        session.openingSameResource = resourceId != nil && resourceId == session.resourceId
        session.openingCompletion = completion
        if session.restoration.isRestoring {
            session.finishRestoration(false)
            if session.ended { return true }
        }
        session.beginStopping()
        if !session.openingSameResource { session.node.pause() }
        if session.active || session.starting {
            session.playerController?.stopPictureInPicture()
            session.scheduleStopFallback(failedStart: false)
        } else { session.complete(success: true, notifyFailure: false) }
        return true
    }

    static func start(context: AccountContext, node: UniversalVideoNode, resourceId: String,
                      timestamp: Double, rate: Double, playing: Bool, title: String, gallery: ViewController,
                      valid: @escaping () -> Bool, sourceState: @escaping () -> ReturnState?,
                      didStart: @escaping () -> Void, restore: @escaping (ReturnState, @escaping (Bool) -> Void) -> Void,
                      finish: @escaping (Double, Bool, Bool, Bool) -> Void, failed: @escaping (String) -> Void) -> NagramiXNativePlayerPiP? {
        assert(Thread.isMainThread)
        guard self.current == nil, AVPictureInPictureController.isPictureInPictureSupported(), valid(),
              !context.sharedContext.mediaManager.audioSession.getIsRecordingActive() else { return nil }
        let session = NagramiXNativePlayerPiP(context: context, node: node, resourceId: resourceId,
            initial: ReturnState(timestamp: timestamp, playing: playing, rate: rate), title: title, gallery: gallery,
            valid: valid, sourceState: sourceState, didStart: didStart, restore: restore, finish: finish, failed: failed)
        self.current = session
        session.statusDisposable = (node.status |> deliverOnMainQueue).start(next: { [weak session] status in
            guard let session else { return }
            session.lastStatus = status
            if session.active { session.updateNowPlaying() }
        })
        node.setNagramiXBackgroundPlayback(id: session.owner, active: true)
        node.setCanPlaybackWithoutHierarchy(true)
        context.sharedContext.mediaManager.setNagramiXSystemPiPPlayback(id: session.owner, active: true)
        session.timer = Foundation.Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak session] _ in session?.update() }
        DispatchQueue.main.async { [weak session] in session?.update() }
        return session
    }
    private init(context: AccountContext, node: UniversalVideoNode, resourceId: String, initial: ReturnState,
                 title: String, gallery: ViewController, valid: @escaping () -> Bool, sourceState: @escaping () -> ReturnState?,
                 didStart: @escaping () -> Void, restore: @escaping (ReturnState, @escaping (Bool) -> Void) -> Void,
                 finish: @escaping (Double, Bool, Bool, Bool) -> Void, failed: @escaping (String) -> Void) {
        self.context = context; self.node = node; self.resourceId = resourceId; self.initial = initial; self.title = title
        self.retainGallery = gallery; self.valid = valid; self.sourceState = sourceState
        self.didStart = didStart; self.restore = restore; self.finish = finish; self.failed = failed
        super.init()
    }
    func updateFrame(_ frame: CGRect) {} // AVKit uses the original layer's geometry.
    func cancelPreparation() { if !self.active && !self.starting { self.complete(success: false, notifyFailure: false) } }
    private func update() {
        guard !self.ended, !self.stopping else { return }
        if self.active { return }
        // Once AVKit accepted start, its callback/timeout owns the outcome;
        // transient application-state changes must not tear down its layer.
        if !self.starting && (!self.valid() || UIApplication.shared.applicationState != .active) {
            self.complete(success: false, notifyFailure: false); return
        }
        guard CACurrentMediaTime() < self.deadline else {
            if self.starting, self.playerController?.isPictureInPictureActive == true, let controller = self.playerController {
                self.pictureInPictureControllerDidStartPictureInPicture(controller)
            } else if self.starting {
                // AVKit may deliver a delayed start/failure callback. Keep the
                // controller and layer alive while cancelling that transaction.
                self.startFailure = "Система не завершила запуск PiP вовремя."
                self.beginStopping()
                self.playerController?.stopPictureInPicture()
                self.scheduleStopFallback(failedStart: true)
            } else {
                let possible = self.playerController?.isPictureInPicturePossible == true
                let attached = self.node.view.window != nil
                let type = self.layer.map { String(describing: Swift.type(of: $0)) } ?? "отсутствует"
                self.complete(success: false, detail: "Время ожидания PiP: слой=\(type), в окне=\(attached), доступен=\(possible), звук=\(self.lastStatus?.soundEnabled == true).")
            }
            return
        }
        if self.playerController == nil, let layer = self.node.nagramiXPictureInPictureSourceLayer() {
            let controller: AVPictureInPictureController?
            if let sample = layer as? AVSampleBufferDisplayLayer {
                let playback = Playback(node: self.node, layer: sample)
                self.playback = playback
                controller = AVPictureInPictureController(contentSource: .init(sampleBufferDisplayLayer: sample, playbackDelegate: playback))
                playback.changed = { [weak self] status in
                    guard let self else { return }
                    self.lastStatus = status
                    guard let status else { return }
                    let playing: Bool
                    switch status.status {
                    case .playing: playing = true
                    case .paused: playing = false
                    case let .buffering(_, whilePlaying, _, _): playing = whilePlaying
                    }
                    if self.lastPlaybackIntent != playing || self.lastDuration != status.duration {
                        self.lastPlaybackIntent = playing
                        self.lastDuration = status.duration
                        self.playerController?.invalidatePlaybackState()
                    }
                }
            } else if let player = layer as? AVPlayerLayer {
                controller = AVPictureInPictureController(playerLayer: player)
            } else { controller = nil }
            guard let controller else { self.complete(success: false, detail: "Исходный видеослой не поддерживает PiP."); return }
            self.layer = layer; self.playerController = controller
            controller.delegate = self
            controller.canStartPictureInPictureAutomaticallyFromInline = false
            controller.requiresLinearPlayback = false
            self.observation = controller.observe(\.isPictureInPicturePossible, options: [.new]) { [weak self] _, _ in
                DispatchQueue.main.async { self?.update() }
            }
        }
        if !self.starting, let controller = self.playerController, !controller.isPictureInPicturePossible,
           !self.requestedSilentAudio, CACurrentMediaTime() - self.preparedAt >= 1.5,
           !self.context.sharedContext.mediaManager.audioSession.getIsRecordingActive() {
            // Some silent videos do not acquire a playback session. Only when
            // the manager reports no active playback, request a mixing lease.
            self.requestedSilentAudio = true
            let audio = self.context.sharedContext.mediaManager.audioSession
            self.audioReadiness.set((combineLatest(audio.isActive(), audio.isPlaybackActive()) |> take(1) |> deliverOnMainQueue).start(next: { [weak self] active, playback in
                guard let self, !self.ended, !self.stopping, !self.starting,
                      !(active && playback), !audio.getIsRecordingActive() else { return }
                self.silentAudioLease = audio.push(audioSessionType: .play(mixWithOthers: true), activate: { [weak self] _ in
                    DispatchQueue.main.async { self?.update() }
                }, deactivate: { _ in .complete() })
            }))
        }
        guard !self.starting, let controller = self.playerController, let layer = self.layer,
              self.node.nagramiXPictureInPictureSourceLayer() === layer,
              controller.isPictureInPicturePossible else { return }
        self.starting = true
        self.deadline = CACurrentMediaTime() + 8
        controller.startPictureInPicture()
    }
    private func updateNowPlaying() {
        guard let status = self.lastStatus else { return }
        self.context.sharedContext.mediaManager.setNagramiXVideoNowPlaying(id: self.owner,
            state: NagramiXVideoNowPlayingState(title: self.title, status: status, isPictureInPicture: true, control: { [weak node = self.node] action in
                guard let node else { return }
                switch action {
                case .playback(.play): node.play()
                case .playback(.pause): node.pause()
                case let .seek(time): if time.isFinite { node.seek(max(0, time)) }
                default: break
                }
            }))
    }
    private func returnState() -> ReturnState {
        if let state = self.sourceState() { self.initial = state }
        if let status = self.lastStatus {
            let time = (self.layer as? AVSampleBufferDisplayLayer)?.controlTimebase.map { CMTimeGetSeconds(CMTimebaseGetTime($0)) } ?? status.timestamp
            if time.isFinite { self.initial = ReturnState(timestamp: max(0, time), playing: self.initial.playing, rate: status.baseRate) }
            switch status.status {
            case .playing: self.initial = ReturnState(timestamp: self.initial.timestamp, playing: true, rate: self.initial.rate)
            case .paused: self.initial = ReturnState(timestamp: self.initial.timestamp, playing: false, rate: self.initial.rate)
            case let .buffering(_, whilePlaying, _, _): self.initial = ReturnState(timestamp: self.initial.timestamp, playing: whilePlaying, rate: self.initial.rate)
            }
        }
        return ReturnState(timestamp: self.initial.timestamp, playing: self.pendingStopPlaying ?? self.initial.playing, rate: self.initial.rate)
    }
    private func beginStopping() {
        guard !self.stopping else { return }
        self.pendingStopPlaying = self.returnState().playing
        self.stopping = true
        self.timer?.invalidate(); self.timer = nil
    }
    private func scheduleStopFallback(failedStart: Bool) {
        self.timer?.invalidate()
        self.timer = Foundation.Timer.scheduledTimer(withTimeInterval: 3, repeats: true) { [weak self] _ in
            guard let self, !self.ended, self.stopping, !self.restoration.isRestoring else { return }
            // Do not destroy an active system window. Retry stop until AVKit
            // confirms it is inactive; inactive missing callbacks get cleaned up.
            if self.playerController?.isPictureInPictureActive == true {
                self.playerController?.stopPictureInPicture()
            } else {
                self.complete(success: !failedStart, notifyFailure: failedStart,
                    detail: "Система не завершила подготовку PiP вовремя.")
            }
        }
    }
    private func finishRestoration(_ restored: Bool) {
        guard self.restoration.isRestoring, let completion = self.restoreCompletion else { return }
        let shouldComplete = self.restoration.restorationFinished()
        self.restored = restored; self.restoreCompletion = nil
        self.restoreTimer?.invalidate(); self.restoreTimer = nil
        completion(restored)
        if shouldComplete { self.complete(success: true) }
    }
    private func complete(success: Bool, notifyFailure: Bool = true, detail: String = "Не удалось запустить системный PiP.") {
        guard !self.ended else { return }
        let state = self.returnState()
        self.ended = true
        self.restoreTimer?.invalidate(); self.restoreTimer = nil
        let pendingRestore = self.restoreCompletion; self.restoreCompletion = nil
        _ = self.restoration.restorationFinished()
        pendingRestore?(false)
        self.timer?.invalidate(); self.timer = nil
        self.statusDisposable?.dispose(); self.statusDisposable = nil
        self.audioReadiness.dispose()
        self.silentAudioLease?.dispose(); self.silentAudioLease = nil
        self.context.sharedContext.mediaManager.setNagramiXVideoNowPlaying(id: self.owner, state: nil)
        self.observation?.invalidate(); self.observation = nil
        self.playerController?.delegate = nil
        self.playerController?.contentSource = nil
        self.playerController = nil; self.playback?.changed = nil; self.playback = nil; self.layer = nil
        self.node.setCanPlaybackWithoutHierarchy(false)
        self.node.setNagramiXBackgroundPlayback(id: self.owner, active: false)
        self.context.sharedContext.mediaManager.setNagramiXSystemPiPPlayback(id: self.owner, active: false)
        let completion = self.openingCompletion; self.openingCompletion = nil
        if self.active && !self.restored && completion == nil { self.node.pause() }
        else if self.active && self.restored && completion == nil {
            if state.playing { self.node.play() } else { self.node.pause() }
        }
        if Self.current === self { Self.current = nil }
        self.finish(state.timestamp, state.playing, completion == nil && (self.restored || !success), self.transferred)
        self.retainGallery = nil
        if let completion {
            let result = self.openingSameResource ? state : nil
            DispatchQueue.main.async { completion(result) }
        }
        if !success && notifyFailure { self.failed(detail) }
    }
    func pictureInPictureControllerDidStartPictureInPicture(_ pictureInPictureController: AVPictureInPictureController) {
        guard Thread.isMainThread else {
            DispatchQueue.main.async { [weak self] in self?.pictureInPictureControllerDidStartPictureInPicture(pictureInPictureController) }
            return
        }
        guard !self.ended else { pictureInPictureController.stopPictureInPicture(); return }
        self.active = true
        if self.stopping { pictureInPictureController.stopPictureInPicture(); return }
        guard self.valid() else {
            self.beginStopping()
            pictureInPictureController.stopPictureInPicture()
            self.scheduleStopFallback(failedStart: false)
            return
        }
        self.transferred = true
        self.timer?.invalidate(); self.timer = nil
        self.updateNowPlaying()
        self.didStart()
    }
    func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, failedToStartPictureInPictureWithError error: Error) {
        guard Thread.isMainThread else {
            DispatchQueue.main.async { [weak self] in self?.pictureInPictureController(pictureInPictureController, failedToStartPictureInPictureWithError: error) }
            return
        }
        let value = error as NSError
        self.complete(success: false, detail: "Система не запустила PiP (\(value.domain), \(value.code)).")
    }
    func pictureInPictureControllerWillStopPictureInPicture(_ pictureInPictureController: AVPictureInPictureController) {
        guard Thread.isMainThread else {
            DispatchQueue.main.async { [weak self] in self?.pictureInPictureControllerWillStopPictureInPicture(pictureInPictureController) }
            return
        }
        self.beginStopping()
    }
    func pictureInPictureControllerDidStopPictureInPicture(_ pictureInPictureController: AVPictureInPictureController) {
        guard Thread.isMainThread else {
            DispatchQueue.main.async { [weak self] in self?.pictureInPictureControllerDidStopPictureInPicture(pictureInPictureController) }
            return
        }
        if self.restoration.stopped() {
            if let reason = self.startFailure { self.complete(success: false, detail: reason) }
            else if !self.active && self.openingCompletion == nil {
                self.complete(success: false, detail: "Системный PiP остановился до запуска.")
            } else { self.complete(success: true) }
        }
    }
    func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler completionHandler: @escaping (Bool) -> Void) {
        guard Thread.isMainThread else {
            DispatchQueue.main.async { [weak self] in
                guard let self else { completionHandler(false); return }
                self.pictureInPictureController(pictureInPictureController, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: completionHandler)
            }
            return
        }
        guard !self.ended, self.playerController === pictureInPictureController,
              self.openingCompletion == nil, self.restoration.begin() else { completionHandler(false); return }
        let state = self.returnState()
        self.pendingStopPlaying = self.pendingStopPlaying ?? state.playing
        self.restoreCompletion = completionHandler
        self.restoreTimer = Foundation.Timer.scheduledTimer(withTimeInterval: 5, repeats: false) { [weak self] _ in
            self?.finishRestoration(false)
        }
        self.restore(state) { [weak self] value in
            DispatchQueue.main.async { self?.finishRestoration(value) }
        }
    }
}
