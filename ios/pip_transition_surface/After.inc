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
final class NagramiXNativePlayerPiP: NSObject, AVPictureInPictureControllerDelegate {
    private static var current: NagramiXNativePlayerPiP?
    private let view = NagramiXPiPPlayerView()
    private let player: AVPlayer
    private var controller: AVPictureInPictureController?
    private let resources: Disposable
    private let context: AccountContext
    private let id = UUID()
    private var title = ""
    private var sourceStatus: MediaPlayerStatus?
    private var initialTimestamp: Double = 0
    private var audioLease: Disposable?
    private var timer: Foundation.Timer?
    private var deadline = CACurrentMediaTime() + 30
    private var seeking = true
    private var seekStarted = false
    private var failureReason = "Подготовка PiP не завершилась вовремя."
    private var starting = false
    private var active = false
    private var restored = false
    private var ended = false
    private var audioReady = false
    private var tookOver = false
    private var takeover: (() -> Void)?
    private var initialTimestampCaptureTime: CFTimeInterval = 0
    private var playbackWasRunning = true
    private var rate: Float = 1
    private let valid: () -> Bool
    private var retainGallery: ViewController?
    private let didStart: () -> Void
    private let restore: (@escaping (Bool) -> Void) -> Void
    private let finish: (Double, Bool, Bool, Bool) -> Void
    private let failed: (String) -> Void

    static var isBusy: Bool { return self.current != nil }
    var isActive: Bool { return self.active && !self.ended }
    static func start(context: AccountContext, url: URL, resources: Disposable,
                      host: UIView, frame: CGRect, timestamp: Double, rate: Double, playing: Bool, title: String, status: MediaPlayerStatus,
                      gallery: ViewController, valid: @escaping () -> Bool,
                      takeover: @escaping () -> Void, didStart: @escaping () -> Void,
                      restore: @escaping (@escaping (Bool) -> Void) -> Void,
                      finish: @escaping (Double, Bool, Bool, Bool) -> Void, failed: @escaping (String) -> Void) -> NagramiXNativePlayerPiP? {
        assert(Thread.isMainThread)
        guard self.current == nil, AVPictureInPictureController.isPictureInPictureSupported(),
              valid(), host.window != nil, frame.width > 0, frame.height > 0,
              !context.sharedContext.mediaManager.audioSession.getIsRecordingActive() else { resources.dispose(); return nil }
        let session = NagramiXNativePlayerPiP(context: context, url: url, resources: resources,
            gallery: gallery, valid: valid, didStart: didStart, restore: restore, finish: finish, failed: failed)
        self.current = session
        session.title = title; session.sourceStatus = status; session.initialTimestamp = timestamp
        session.initialTimestampCaptureTime = CACurrentMediaTime(); session.takeover = takeover
        session.view.frame = frame; session.view.isUserInteractionEnabled = false
        // The replacement player has no frame yet: leave the existing video
        // visible until its AVPlayerLayer can actually display a frame.
        session.view.alpha = 0.001
        session.view.playerLayer.videoGravity = .resizeAspect
        host.addSubview(session.view)
        session.rate = Float(rate.isFinite ? max(0.25, min(2, rate)) : 1)
        session.playbackWasRunning = playing
        session.player.isMuted = true
        session.player.automaticallyWaitsToMinimizeStalling = true
        session.view.playerLayer.player = session.player
        session.controller = AVPictureInPictureController(playerLayer: session.view.playerLayer)
        guard let controller = session.controller else { self.current = nil; session.view.removeFromSuperview(); resources.dispose(); return nil }
        controller.delegate = session
        controller.canStartPictureInPictureAutomaticallyFromInline = false
        controller.requiresLinearPlayback = false
        session.timer = Foundation.Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak session] _ in session?.update() }
        return session
    }

    private init(context: AccountContext, url: URL, resources: Disposable, gallery: ViewController,
                 valid: @escaping () -> Bool, didStart: @escaping () -> Void,
                 restore: @escaping (@escaping (Bool) -> Void) -> Void,
                 finish: @escaping (Double, Bool, Bool, Bool) -> Void, failed: @escaping (String) -> Void) {
        self.context = context; self.resources = resources
        self.player = AVPlayer(url: url); self.retainGallery = gallery
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
        guard !self.ended else { return }
        if self.active { self.updateNowPlaying(); return }
        guard self.valid(), UIApplication.shared.applicationState == .active else {
            if self.starting { self.controller?.stopPictureInPicture() }
            self.failureReason = "Просмотр видео был закрыт до запуска PiP."
            self.complete(success: false); return
        }
        if let item = self.player.currentItem, item.status == .failed {
            let error = item.error as NSError?
            self.failureReason = "Не удалось подготовить видео" + (error.map { " (\($0.domain), \($0.code))" } ?? "") + "."
            self.complete(success: false); return
        }
        guard CACurrentMediaTime() < self.deadline else {
            self.failureReason = "Время ожидания PiP истекло: аудио=\(self.audioReady), видео=\(self.player.currentItem?.status.rawValue ?? -1), кадр=\(self.view.playerLayer.isReadyForDisplay), доступен=\(self.controller?.isPictureInPicturePossible == true), старт=\(self.starting)."
            if self.starting { self.controller?.stopPictureInPicture() }
            self.complete(success: false); return
        }
        // Do not interrupt the original video or acquire its audio session until
        // AVFoundation has accepted the file. Failures leave the source untouched.
        if !self.tookOver, self.player.currentItem?.status == .readyToPlay {
            let elapsed = self.playbackWasRunning ? max(0, CACurrentMediaTime() - self.initialTimestampCaptureTime) * Double(self.rate) : 0
            let duration = self.sourceStatus?.duration ?? 0
            let position = max(0, self.initialTimestamp + elapsed)
            self.initialTimestamp = duration.isFinite && duration > 0 ? min(duration, position) : position
            self.tookOver = true
            let takeover = self.takeover; self.takeover = nil; takeover?()
            self.context.sharedContext.mediaManager.setNagramiXSystemPiPPlayback(id: self.id, active: true)
            self.audioLease = self.context.sharedContext.mediaManager.audioSession.push(audioSessionType: .play(mixWithOthers: false), activate: { [weak self] _ in
                DispatchQueue.main.async { self?.audioReady = true; self?.update() }
            }, deactivate: { [weak self] _ in
                DispatchQueue.main.async { self?.stop() }
                return .complete()
            })
        }
        // AVPlayer's first seek and playback must wait for both a playable item
        // and the managed audio session. This avoids racing the gallery player
        // and cancels no seek against an item whose duration is still unknown.
        if !self.seekStarted, self.audioReady, self.player.currentItem?.status == .readyToPlay {
            self.seekStarted = true
            self.player.seek(to: CMTime(seconds: self.initialTimestamp, preferredTimescale: 600), toleranceBefore: .zero, toleranceAfter: .zero) { [weak self] done in
                DispatchQueue.main.async {
                    guard let self, !self.ended else { return }
                    guard done else { self.failureReason = "Не удалось перейти к позиции видео."; self.complete(success: false); return }
                    self.seeking = false
                    self.player.playImmediately(atRate: self.rate)
                    self.update()
                }
            }
        }
        // Unhide before querying AVKit's PiP eligibility: the system needs a
        // visible source layer, but never show an uninitialized black surface.
        if !self.seeking, self.audioReady, self.view.playerLayer.isReadyForDisplay, self.view.alpha < 1 {
            self.view.alpha = 1
        }
        guard !self.starting, !self.seeking, self.audioReady, self.view.window != nil,
              self.view.playerLayer.isReadyForDisplay, self.controller?.isPictureInPicturePossible == true else { return }
        self.starting = true; self.deadline = CACurrentMediaTime() + 8
        self.player.isMuted = false
        self.controller?.startPictureInPicture()
    }
    func stop() {
        if self.active || self.starting { self.controller?.stopPictureInPicture() }
        else { self.complete(success: false) }
    }
    private func complete(success: Bool, notifyFailure: Bool = true) {
        guard !self.ended else { return }; self.ended = true
        let position = self.player.currentTime().seconds
        let running = self.active ? self.player.rate != 0 : self.playbackWasRunning
        self.timer?.invalidate(); self.timer = nil
        self.player.pause(); self.controller?.delegate = nil; self.controller = nil
        self.context.sharedContext.mediaManager.setNagramiXVideoNowPlaying(id: self.id, state: nil)
        self.view.playerLayer.player = nil; self.view.removeFromSuperview()
        // Release PiP's managed lease before the gallery reacquires sound.
        self.audioLease?.dispose(); self.audioLease = nil
        self.context.sharedContext.mediaManager.setNagramiXSystemPiPPlayback(id: self.id, active: false)
        self.takeover = nil
        self.finish(!self.seeking && position.isFinite ? max(0, position) : self.initialTimestamp, running, self.restored || !success, self.tookOver)
        self.resources.dispose(); self.retainGallery = nil
        if Self.current === self { Self.current = nil }
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
                guard let self, !self.ended else { return }
                switch action {
                case .playback(.play): self.player.playImmediately(atRate: self.rate)
                case .playback(.pause): self.player.pause()
                case let .seek(time): if time.isFinite { self.player.seek(to: CMTime(seconds: max(0, time), preferredTimescale: 600)) }
                default: break
                }
            }))
    }
    func pictureInPictureControllerDidStartPictureInPicture(_ controller: AVPictureInPictureController) {
        guard !self.ended else { controller.stopPictureInPicture(); return }
        self.active = true
        if !self.playbackWasRunning { self.player.pause() }
        self.updateNowPlaying()
        self.didStart()
    }
    func pictureInPictureController(_ controller: AVPictureInPictureController, failedToStartPictureInPictureWithError error: Error) {
        let detail = error as NSError
        self.failureReason = "Система не запустила PiP (\(detail.domain), \(detail.code))."
        self.complete(success: false)
    }
    func pictureInPictureControllerDidStopPictureInPicture(_ controller: AVPictureInPictureController) { self.complete(success: true) }
    func pictureInPictureController(_ controller: AVPictureInPictureController, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler completion: @escaping (Bool) -> Void) {
        self.restore { [weak self] restored in self?.restored = restored; completion(restored) }
    }
}
