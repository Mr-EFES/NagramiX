import Foundation
import UIKit
import AVKit
import Display
import SwiftSignalKit
import AccountContext
import TelegramCore
import UniversalMediaPlayer
import TelegramAudio

private final class NagramiXPiPPlayerView: UIView {
    override class var layerClass: AnyClass { return AVPlayerLayer.self }
    var playerLayer: AVPlayerLayer { return self.layer as! AVPlayerLayer }
    override func layoutSubviews() {
        super.layoutSubviews()
        CATransaction.begin(); CATransaction.setDisableActions(true)
        self.playerLayer.frame = self.bounds
        CATransaction.commit()
    }
}

// All state belongs to the main queue. Retaining one session keeps AVKit alive
// after the gallery is dismissed; ending the session releases its resources.
private struct NagramiXPiPStopState {
    private(set) var isStopping = false
    private(set) var playing: Bool?
    mutating func capture(playing: Bool) {
        if self.playing == nil { self.playing = playing }
    }
    mutating func begin(playing: Bool) {
        self.capture(playing: playing)
        self.isStopping = true
    }
}

final class NagramiXNativePlayerPiP: NSObject, AVPictureInPictureControllerDelegate {
    private static var current: NagramiXNativePlayerPiP?
    private let view = NagramiXPiPPlayerView()
    private let player: AVPlayer
    private let resourceLoader: NagramiXPiPResourceLoader
    private var controller: AVPictureInPictureController?
    private let resources: Disposable
    private let context: AccountContext
    private let id = UUID()
    private var title = ""
    private var sourceStatus: MediaPlayerStatus?
    private var initialTimestamp: Double = 0
    private var audioLease: Disposable?
    private var timer: Foundation.Timer?
    private var readinessObservers: [NSKeyValueObservation] = []
    private var deadline = CACurrentMediaTime() + 30
    private var seeking = true
    private var seekStarted = false
    private var failureReason = "Подготовка PiP не завершилась вовремя."
    private var starting = false
    private var active = false
    private var stopState = NagramiXPiPStopState()
    private var stopping: Bool { return self.stopState.isStopping }
    private var stopPlaying: Bool? { return self.stopState.playing }
    private var openingCompletion: ((ReturnState?) -> Void)?
    private var openingSameResource = false
    private var restorePreparing = false
    private var restored = false
    private var ended = false
    private var audioReady = false
    private var audioRequested = false
    private var playbackPrimed = false
    private var resourceId = ""
    private var tookOver = false
    private var takeover: (() -> Void)?
    private var sourceState: (() -> ReturnState?)?
    private var alignmentAttempts = 0
    private var initialTimestampCaptureTime: CFTimeInterval = 0
    private var playbackWasRunning = true
    private var rate: Float = 1
    private let valid: () -> Bool
    private var retainGallery: ViewController?
    private let didStart: () -> Void
    private let restore: (ReturnState, @escaping (Bool) -> Void) -> Void
    private let finish: (Double, Bool, Bool, Bool) -> Void
    private let failed: (String) -> Void

    struct ReturnState {
        let timestamp: Double
        let playing: Bool
        let rate: Double
    }
    static var isBusy: Bool { return self.current != nil }

    // A newly opened gallery takes ownership from the previous PiP session.
    // Stop its audio before the gallery can begin playback. The time is used
    // only when the same resource is reopened.
    @discardableResult
    static func takeForOpening(resourceId: String?, completion: @escaping (ReturnState?) -> Void) -> Bool {
        assert(Thread.isMainThread)
        guard let session = self.current, !session.ended, session.openingCompletion == nil else { return false }
        session.openingSameResource = resourceId != nil && resourceId == session.resourceId
        session.openingCompletion = completion
        session.beginStopping()
        // Silence PiP immediately, but retain AVKit and its delegate until the
        // stop callback. The destination must not autoplay during that interval.
        if !session.tookOver {
            session.tookOver = true
            let takeover = session.takeover; session.takeover = nil; takeover?()
        }
        session.player.pause()
        if session.active || session.starting { session.controller?.stopPictureInPicture() }
        else { session.complete(success: true, notifyFailure: false) }
        return true
    }
    private func returnState() -> ReturnState {
        let time = self.player.currentTime().seconds
        let elapsed = self.playbackWasRunning ? max(0, CACurrentMediaTime() - self.initialTimestampCaptureTime) * Double(self.rate) : 0
        let pending = self.initialTimestamp + elapsed
        return ReturnState(timestamp: !self.seeking && time.isFinite ? max(0, time) : max(0, pending),
            playing: self.stopPlaying ?? self.playbackWasRunning, rate: Double(self.rate))
    }
    private func beginStopping() {
        guard !self.stopping else { return }
        self.stopState.begin(playing: self.playbackWasRunning)
        self.timer?.invalidate(); self.timer = nil
    }
    var isActive: Bool { return self.active && !self.ended }
    static func start(context: AccountContext, resourceLoader: NagramiXPiPResourceLoader, resourceId: String, resources: Disposable,
                      host: UIView, frame: CGRect, timestamp: Double, rate: Double, playing: Bool, title: String, status: MediaPlayerStatus,
                      gallery: ViewController, valid: @escaping () -> Bool,
                      sourceState: @escaping () -> ReturnState?, takeover: @escaping () -> Void, didStart: @escaping () -> Void,
                      restore: @escaping (ReturnState, @escaping (Bool) -> Void) -> Void,
                      finish: @escaping (Double, Bool, Bool, Bool) -> Void, failed: @escaping (String) -> Void) -> NagramiXNativePlayerPiP? {
        assert(Thread.isMainThread)
        guard self.current == nil, AVPictureInPictureController.isPictureInPictureSupported(),
              valid(), host.window != nil, frame.width > 0, frame.height > 0,
              !context.sharedContext.mediaManager.audioSession.getIsRecordingActive() else { resources.dispose(); return nil }
        let session = NagramiXNativePlayerPiP(context: context, resourceLoader: resourceLoader, resources: resources,
            gallery: gallery, valid: valid, didStart: didStart, restore: restore, finish: finish, failed: failed)
        self.current = session
        session.title = title; session.sourceStatus = status; session.initialTimestamp = timestamp; session.resourceId = resourceId
        session.initialTimestampCaptureTime = CACurrentMediaTime(); session.takeover = takeover; session.sourceState = sourceState
        session.view.frame = frame; session.view.isUserInteractionEnabled = false
        // The replacement player has no frame yet: leave the existing video
        // visible until its AVPlayerLayer can actually display a frame.
        session.view.alpha = 0.001
        session.view.playerLayer.videoGravity = .resizeAspect
        host.addSubview(session.view)
        session.rate = Float(rate.isFinite ? max(0.25, min(2, rate)) : 1)
        session.playbackWasRunning = playing
        session.readinessObservers.append(session.player.observe(\.timeControlStatus, options: [.new]) { [weak session] _, _ in
            DispatchQueue.main.async {
                guard let session, session.active, !session.stopping, !session.restorePreparing else { return }
                switch session.player.timeControlStatus {
                case .playing: session.playbackWasRunning = true
                case .paused: session.playbackWasRunning = false
                case .waitingToPlayAtSpecifiedRate: break
                @unknown default: break
                }
            }
        })
        session.player.isMuted = true
        session.player.automaticallyWaitsToMinimizeStalling = true
        session.view.playerLayer.player = session.player
        session.controller = AVPictureInPictureController(playerLayer: session.view.playerLayer)
        guard let controller = session.controller else { self.current = nil; session.view.removeFromSuperview(); resources.dispose(); return nil }
        controller.delegate = session
        controller.canStartPictureInPictureAutomaticallyFromInline = false
        controller.requiresLinearPlayback = false
        // Readiness can change between timer ticks. Observe AVFoundation and
        // AVKit on their actual transitions, always returning to the main queue.
        if let item = session.player.currentItem {
            session.readinessObservers.append(item.observe(\.status, options: [.new]) { [weak session] _, _ in
                DispatchQueue.main.async { session?.update() }
            })
        }
        session.readinessObservers.append(session.view.playerLayer.observe(\.isReadyForDisplay, options: [.new]) { [weak session] _, _ in
            DispatchQueue.main.async { session?.update() }
        })
        session.readinessObservers.append(controller.observe(\.isPictureInPicturePossible, options: [.new]) { [weak session] _, _ in
            DispatchQueue.main.async { session?.update() }
        })
        DispatchQueue.main.async { [weak session] in session?.update() }
        session.timer = Foundation.Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak session] _ in session?.update() }
        return session
    }

    private init(context: AccountContext, resourceLoader: NagramiXPiPResourceLoader, resources: Disposable, gallery: ViewController,
                 valid: @escaping () -> Bool, didStart: @escaping () -> Void,
                 restore: @escaping (ReturnState, @escaping (Bool) -> Void) -> Void,
                 finish: @escaping (Double, Bool, Bool, Bool) -> Void, failed: @escaping (String) -> Void) {
        self.context = context; self.resources = resources
        self.resourceLoader = resourceLoader
        self.player = AVPlayer(playerItem: AVPlayerItem(asset: resourceLoader.asset)); self.retainGallery = gallery
        self.valid = valid; self.didStart = didStart; self.restore = restore
        self.finish = finish; self.failed = failed
        super.init()
    }

    func updateFrame(_ frame: CGRect) {
        guard !self.active, !self.ended else { return }
        self.view.frame = frame
    }
    func cancelPreparation() { if !self.active && !self.starting { self.complete(success: false, notifyFailure: false) } }
    private func update() {
        guard !self.ended, !self.stopping else { return }
        if self.active { self.updateNowPlaying(); return }
        guard self.valid(), UIApplication.shared.applicationState == .active else {
            if self.starting { self.controller?.stopPictureInPicture() }
            self.failureReason = "Просмотр видео был закрыт до запуска PiP."
            self.complete(success: false); return
        }
        if let item = self.player.currentItem, item.status == .failed {
            let error = item.error as NSError?
            self.failureReason = "Не удалось подготовить видео" + (error.map { " (\($0.domain), \($0.code))" } ?? "") + "." + " Поток: " + self.resourceLoader.diagnostic
            self.complete(success: false); return
        }
        guard CACurrentMediaTime() < self.deadline else {
            self.failureReason = "Время ожидания PiP истекло: аудио=\(self.audioReady), видео=\(self.player.currentItem?.status.rawValue ?? -1), кадр=\(self.view.playerLayer.isReadyForDisplay), доступен=\(self.controller?.isPictureInPicturePossible == true), старт=\(self.starting)." + " Поток: " + self.resourceLoader.diagnostic
            if self.starting { self.controller?.stopPictureInPicture() }
            self.complete(success: false); return
        }
        // Seek the replacement while the original keeps playing. Only hand
        // over audio after AVFoundation has prepared the requested position.
        if !self.seekStarted, self.player.currentItem?.status == .readyToPlay {
            self.seekStarted = true
            let elapsed = self.playbackWasRunning ? max(0, CACurrentMediaTime() - self.initialTimestampCaptureTime) * Double(self.rate) : 0
            let duration = self.sourceStatus?.duration ?? 0
            let live = self.sourceState?()
            if let live { self.playbackWasRunning = live.playing; self.rate = Float(live.rate.isFinite ? max(0.25, min(2, live.rate)) : 1) }
            let position = max(0, live?.timestamp ?? (self.initialTimestamp + elapsed))
            self.initialTimestamp = duration.isFinite && duration > 0 ? min(duration, position) : position
            self.initialTimestampCaptureTime = CACurrentMediaTime()
            self.player.seek(to: CMTime(seconds: self.initialTimestamp, preferredTimescale: 600), toleranceBefore: .zero, toleranceAfter: .zero) { [weak self] done in
                DispatchQueue.main.async {
                    guard let self, !self.ended else { return }
                    guard done, self.valid() else { self.failureReason = "Не удалось перейти к позиции видео."; self.complete(success: false); return }
                    self.seeking = false
                    self.update()
                }
            }
        }
        if !self.seeking, !self.playbackPrimed {
            self.playbackPrimed = true
            // Decode a frame even when the source was paused. didStart restores
            // the requested paused state after AVKit has acquired the layer.
            self.player.playImmediately(atRate: self.rate)
        }
        // Keep the original playing until the new player has a decoded frame.
        if !self.seeking, self.view.playerLayer.isReadyForDisplay, !self.audioRequested {
            // Capture intent before the managed audio session can pause the
            // original player as part of activating this replacement.
            if let live = self.sourceState?() {
                self.playbackWasRunning = live.playing
                self.rate = Float(live.rate.isFinite ? max(0.25, min(2, live.rate)) : 1)
            }
            self.audioRequested = true
            self.context.sharedContext.mediaManager.setNagramiXSystemPiPPlayback(id: self.id, active: true)
            self.audioLease = self.context.sharedContext.mediaManager.audioSession.push(audioSessionType: .play(mixWithOthers: false), activate: { [weak self] _ in
                DispatchQueue.main.async {
                    guard let self, !self.ended, !self.stopping else { return }
                    self.audioReady = true
                    self.update()
                }
            }, deactivate: { [weak self] _ in
                DispatchQueue.main.async { self?.stop() }
                return .complete()
            })
        }
        // Unhide before querying AVKit's PiP eligibility: the system needs a
        // visible source layer, but never show an uninitialized black surface.
        if !self.seeking, self.audioReady, self.view.playerLayer.isReadyForDisplay, !self.tookOver,
           let live = self.sourceState?() {
            // The old player's pause here can be caused by audio activation;
            // preserve the intent captured immediately before requesting it.
            self.rate = Float(live.rate.isFinite ? max(0.25, min(2, live.rate)) : 1)
            let position = self.player.currentTime().seconds
            if self.alignmentAttempts == 0, position.isFinite, abs(position - live.timestamp) > 0.2 {
                self.alignmentAttempts += 1
                self.seeking = true
                self.playbackPrimed = false
                self.initialTimestamp = live.timestamp
                self.initialTimestampCaptureTime = CACurrentMediaTime()
                self.player.seek(to: CMTime(seconds: live.timestamp, preferredTimescale: 600), toleranceBefore: .zero, toleranceAfter: .zero) { [weak self] done in
                    DispatchQueue.main.async {
                        guard let self, !self.ended, !self.stopping else { return }
                        guard done else { self.failureReason = "Не удалось синхронизировать позицию видео."; self.complete(success: false); return }
                        self.seeking = false
                        self.update()
                    }
                }
                return
            }
        }
        if !self.seeking, self.audioReady, self.view.playerLayer.isReadyForDisplay, !self.tookOver {
            self.tookOver = true
            let takeover = self.takeover; self.takeover = nil; takeover?()
            if self.playbackWasRunning { self.player.playImmediately(atRate: self.rate) }
            else { self.player.pause() }
            self.player.isMuted = false
            self.view.alpha = 1
        }
        guard !self.starting, !self.seeking, self.audioReady, self.view.window != nil,
              self.view.playerLayer.isReadyForDisplay, self.controller?.isPictureInPicturePossible == true else { return }
        self.starting = true; self.deadline = CACurrentMediaTime() + 8
        self.player.isMuted = false
        self.controller?.startPictureInPicture()
    }
    func stop() {
        self.beginStopping()
        if self.active || self.starting { self.controller?.stopPictureInPicture() }
        else { self.complete(success: false) }
    }
    private func complete(success: Bool, notifyFailure: Bool = true) {
        guard !self.ended else { return }; self.ended = true
        let state = self.returnState()
        let openingCompletion = self.openingCompletion
        self.openingCompletion = nil
        self.timer?.invalidate(); self.timer = nil
        self.readinessObservers.removeAll()
        self.player.pause(); self.controller?.delegate = nil; self.controller = nil
        self.context.sharedContext.mediaManager.setNagramiXVideoNowPlaying(id: self.id, state: nil)
        self.view.playerLayer.player = nil; self.view.removeFromSuperview()
        // Release PiP's managed lease before the gallery reacquires sound.
        self.audioLease?.dispose(); self.audioLease = nil
        self.context.sharedContext.mediaManager.setNagramiXSystemPiPPlayback(id: self.id, active: false)
        self.takeover = nil
        self.sourceState = nil
        // Clear the global session before delivering ownership to a new gallery.
        if Self.current === self { Self.current = nil }
        self.finish(state.timestamp, state.playing, openingCompletion == nil && (self.restored || !success), openingCompletion == nil && self.tookOver)
        self.resourceLoader.cancelAll()
        self.resources.dispose(); self.retainGallery = nil
        if let openingCompletion {
            let result = self.openingSameResource ? state : nil
            DispatchQueue.main.async { openingCompletion(result) }
        }
        if !success && notifyFailure { self.failed(self.failureReason) }
    }
    private func updateNowPlaying() {
        guard let original = self.sourceStatus else { return }
        let position = self.player.currentTime().seconds
        let duration = self.player.currentItem?.duration.seconds ?? original.duration
        let status = MediaPlayerStatus(generationTimestamp: CACurrentMediaTime(), duration: duration.isFinite ? duration : original.duration,
            dimensions: original.dimensions, timestamp: position.isFinite ? position : self.initialTimestamp,
            baseRate: Double(self.rate), seekId: original.seekId, status: self.player.rate > 0 ? .playing : .paused, soundEnabled: true)
        self.context.sharedContext.mediaManager.setNagramiXVideoNowPlaying(id: self.id,
            state: NagramiXVideoNowPlayingState(title: self.title, status: status, isPictureInPicture: true, control: { [weak self] action in
                guard let self, !self.ended, !self.stopping else { return }
                switch action {
                case .playback(.play): self.playbackWasRunning = true; self.player.playImmediately(atRate: self.rate)
                case .playback(.pause): self.playbackWasRunning = false; self.player.pause()
                case let .seek(time): if time.isFinite { self.player.seek(to: CMTime(seconds: max(0, time), preferredTimescale: 600)) }
                default: break
                }
            }))
    }
    func pictureInPictureControllerDidStartPictureInPicture(_ controller: AVPictureInPictureController) {
        guard !self.ended else { controller.stopPictureInPicture(); return }
        self.active = true
        if self.stopping { controller.stopPictureInPicture(); return }
        if !self.playbackWasRunning { self.player.pause() }
        self.updateNowPlaying()
        self.didStart()
    }
    func pictureInPictureController(_ controller: AVPictureInPictureController, failedToStartPictureInPictureWithError error: Error) {
        let detail = error as NSError
        self.failureReason = "Система не запустила PiP (\(detail.domain), \(detail.code))."
        self.complete(success: false)
    }
    func pictureInPictureControllerWillStopPictureInPicture(_ controller: AVPictureInPictureController) { self.beginStopping() }
    func pictureInPictureControllerDidStopPictureInPicture(_ controller: AVPictureInPictureController) { self.complete(success: true) }
    func pictureInPictureController(_ controller: AVPictureInPictureController, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler completion: @escaping (Bool) -> Void) {
        guard self.openingCompletion == nil else { completion(false); return }
        self.restorePreparing = true
        self.stopState.capture(playing: self.playbackWasRunning)
        self.restore(self.returnState()) { [weak self] restored in self?.restored = restored; completion(restored) }
    }
}
