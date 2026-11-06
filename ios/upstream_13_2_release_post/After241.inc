import Foundation
import AVFoundation
import AlertUI
import UIKit
import Display
import AsyncDisplayKit
import ComponentFlow
import SwiftSignalKit
import ViewControllerComponent
import ComponentDisplayAdapters
import TelegramPresentationData
import AccountContext
import NagramiXCore
import TelegramCore
import PresentationDataUtils
import Camera
import CameraLegacy
import CameraNeo
import MultilineTextComponent
import BlurredBackgroundComponent
import PlainButtonComponent
import Photos
import TooltipUI
import BundleIconComponent
import CameraButtonComponent
import TelegramNotices
import DeviceAccess
import MediaEditor
import MediaResources
import LocalMediaResources
import ImageCompression
import LegacyMediaPickerUI
import TelegramAudio
import ChatSendMessageActionUI
import ChatControllerInteraction
import LottieComponent
import GlassBackgroundComponent

private func storeUneditedVideoMessage(
    path: String,
    hasAdjustments: Bool,
    liveUploadId: Int64?,
    store: (Int64, Data) -> Bool
) -> Int64? {
    guard !hasAdjustments,
          let data = try? Data(contentsOf: URL(fileURLWithPath: path), options: .mappedIfSafe),
          !data.isEmpty else {
        return nil
    }
    let id = liveUploadId ?? Int64.random(in: Int64.min ... Int64.max)
    guard store(id, data) else {
        return nil
    }
    return id
}

struct CameraState: Equatable {
    enum Recording: Equatable {
        case none
        case holding
        case handsFree
    }
    enum FlashTint: Equatable {
        case white
        case yellow
        case blue
        
        var color: UIColor {
            switch self {
            case .white:
                return .white
            case .yellow:
                return UIColor(rgb: 0xffed8c)
            case .blue:
                return UIColor(rgb: 0x8cdfff)
            }
        }
    }
    
    let position: Camera.Position
    let flashMode: Camera.FlashMode
    let flashModeDidChange: Bool
    let flashTint: FlashTint
    let flashTintSize: CGFloat
    let recording: Recording
    let duration: Double
    let isDualCameraEnabled: Bool
    let isViewOnceEnabled: Bool
    
    func updatedPosition(_ position: Camera.Position) -> CameraState {
        return CameraState(position: position, flashMode: self.flashMode, flashModeDidChange: self.flashModeDidChange, flashTint: self.flashTint, flashTintSize: self.flashTintSize, recording: self.recording, duration: self.duration, isDualCameraEnabled: self.isDualCameraEnabled, isViewOnceEnabled: self.isViewOnceEnabled)
    }
    
    func updatedFlashMode(_ flashMode: Camera.FlashMode) -> CameraState {
        return CameraState(position: self.position, flashMode: flashMode, flashModeDidChange: self.flashMode != flashMode, flashTint: self.flashTint, flashTintSize: self.flashTintSize, recording: self.recording, duration: self.duration, isDualCameraEnabled: self.isDualCameraEnabled, isViewOnceEnabled: self.isViewOnceEnabled)
    }
    
    func updatedFlashTint(_ flashTint: FlashTint) -> CameraState {
        return CameraState(position: self.position, flashMode: self.flashMode, flashModeDidChange: self.flashModeDidChange, flashTint: flashTint, flashTintSize: self.flashTintSize, recording: self.recording, duration: self.duration, isDualCameraEnabled: self.isDualCameraEnabled, isViewOnceEnabled: self.isViewOnceEnabled)
    }
    
    func updatedFlashTintSize(_ flashTintSize: CGFloat) -> CameraState {
        return CameraState(position: self.position, flashMode: self.flashMode, flashModeDidChange: self.flashModeDidChange, flashTint: self.flashTint, flashTintSize: flashTintSize, recording: self.recording, duration: self.duration, isDualCameraEnabled: self.isDualCameraEnabled, isViewOnceEnabled: self.isViewOnceEnabled)
    }

    func updatedRecording(_ recording: Recording) -> CameraState {
        var flashModeDidChange = self.flashModeDidChange
        if case .none = self.recording {
            flashModeDidChange = false
        }
        return CameraState(position: self.position, flashMode: self.flashMode, flashModeDidChange: flashModeDidChange, flashTint: self.flashTint, flashTintSize: self.flashTintSize, recording: recording, duration: self.duration, isDualCameraEnabled: self.isDualCameraEnabled, isViewOnceEnabled: self.isViewOnceEnabled)
    }
    
    func updatedDuration(_ duration: Double) -> CameraState {
        return CameraState(position: self.position, flashMode: self.flashMode, flashModeDidChange: self.flashModeDidChange, flashTint: self.flashTint, flashTintSize: self.flashTintSize, recording: self.recording, duration: duration, isDualCameraEnabled: self.isDualCameraEnabled, isViewOnceEnabled: self.isViewOnceEnabled)
    }
    
    func updatedIsViewOnceEnabled(_ isViewOnceEnabled: Bool) -> CameraState {
        return CameraState(position: self.position, flashMode: self.flashMode, flashModeDidChange: self.flashModeDidChange, flashTint: self.flashTint, flashTintSize: self.flashTintSize, recording: self.recording, duration: self.duration, isDualCameraEnabled: self.isDualCameraEnabled, isViewOnceEnabled: isViewOnceEnabled)
    }
}

struct PreviewState: Equatable {
    let composition: AVComposition
    let trimRange: Range<Double>?
    let isMuted: Bool
}

enum CameraScreenTransition {
    case animateIn
    case animateOut
    case finishedAnimateIn
}

private let viewOnceButtonTag = GenericComponentViewTag()

private final class VideoMessageCameraScreenComponent: CombinedComponent {
    typealias EnvironmentType = ViewControllerComponentContainer.Environment
    
    let context: AccountContext
    let cameraState: CameraState
    let containerSize: CGSize
    let previewFrame: CGRect
    let safeInsets: UIEdgeInsets
    let layoutHeight: CGFloat
    let isPreviewing: Bool
    let isMuted: Bool
    let totalDuration: Double
    let getController: () -> VideoMessageCameraScreen?
    let present: (ViewController) -> Void
    let push: (ViewController) -> Void
    let startRecording: ActionSlot<Void>
    let stopRecording: ActionSlot<Void>
    let cancelRecording: ActionSlot<Void>
    let completion: ActionSlot<VideoMessageCameraScreen.CaptureResult>
    
    init(
        context: AccountContext,
        cameraState: CameraState,
        containerSize: CGSize,
        previewFrame: CGRect,
        safeInsets: UIEdgeInsets,
        layoutHeight: CGFloat,
        isPreviewing: Bool,
        isMuted: Bool,
        totalDuration: Double,
        getController: @escaping () -> VideoMessageCameraScreen?,
        present: @escaping (ViewController) -> Void,
        push: @escaping (ViewController) -> Void,
        startRecording: ActionSlot<Void>,
        stopRecording: ActionSlot<Void>,
        cancelRecording: ActionSlot<Void>,
        completion: ActionSlot<VideoMessageCameraScreen.CaptureResult>
    ) {
        self.context = context
        self.cameraState = cameraState
        self.containerSize = containerSize
        self.previewFrame = previewFrame
        self.safeInsets = safeInsets
        self.layoutHeight = layoutHeight
        self.isPreviewing = isPreviewing
        self.isMuted = isMuted
        self.totalDuration = totalDuration
        self.getController = getController
        self.present = present
        self.push = push
        self.startRecording = startRecording
        self.stopRecording = stopRecording
        self.cancelRecording = cancelRecording
        self.completion = completion
    }
    
    static func ==(lhs: VideoMessageCameraScreenComponent, rhs: VideoMessageCameraScreenComponent) -> Bool {
        if lhs.context !== rhs.context {
            return false
        }
        if lhs.previewFrame != rhs.previewFrame {
            return false
        }
        if lhs.safeInsets != rhs.safeInsets {
            return false
        }
        if lhs.layoutHeight != rhs.layoutHeight {
            return false
        }
        if lhs.cameraState != rhs.cameraState {
            return false
        }
        if lhs.containerSize != rhs.containerSize {
            return false
        }
        if lhs.isPreviewing != rhs.isPreviewing {
            return false
        }
        if lhs.isMuted != rhs.isMuted {
            return false
        }
        if lhs.totalDuration != rhs.totalDuration {
            return false
        }
        return true
    }
    
    final class State: ComponentState {
        enum ImageKey: Hashable {
            case flip
            case flash
            case flashImage
        }
        private var cachedImages: [ImageKey: UIImage] = [:]
        func image(_ key: ImageKey, theme: PresentationTheme) -> UIImage {
            if let image = self.cachedImages[key] {
                return image
            } else {
                var image: UIImage
                switch key {
                case .flip:
                    image = UIImage(bundleImageName: "Camera/VideoMessageFlip")!.withRenderingMode(.alwaysTemplate)
                case .flash:
                    image = UIImage(bundleImageName: "Camera/VideoMessageFlash")!.withRenderingMode(.alwaysTemplate)
                case .flashImage:
                    image = generateImage(CGSize(width: 393.0, height: 852.0), rotatedContext: { size, context in
                        context.clear(CGRect(origin: .zero, size: size))
                        
                        var locations: [CGFloat] = [0.0, 0.2, 0.6, 1.0]
                        let colors: [CGColor] = [UIColor(rgb: 0xffffff, alpha: 0.25).cgColor, UIColor(rgb: 0xffffff, alpha: 0.25).cgColor, UIColor(rgb: 0xffffff, alpha: 1.0).cgColor, UIColor(rgb: 0xffffff, alpha: 1.0).cgColor]
                        let colorSpace = CGColorSpaceCreateDeviceRGB()
                        let gradient = CGGradient(colorsSpace: colorSpace, colors: colors as CFArray, locations: &locations)!
                        
                        let center = CGPoint(x: size.width / 2.0, y: size.height / 2.0 - 10.0)
                        context.drawRadialGradient(gradient, startCenter: center, startRadius: 0.0, endCenter: center, endRadius: size.width, options: .drawsAfterEndLocation)
                    })!.withRenderingMode(.alwaysTemplate)
                }
                cachedImages[key] = image
                return image
            }
        }
                
        private let context: AccountContext
        private let present: (ViewController) -> Void
        private let startRecording: ActionSlot<Void>
        private let stopRecording: ActionSlot<Void>
        private let cancelRecording: ActionSlot<Void>
        private let completion: ActionSlot<VideoMessageCameraScreen.CaptureResult>
        private let getController: () -> VideoMessageCameraScreen?
        
        private var resultDisposable = MetaDisposable()
                
        var cameraState: CameraState?
        
        var didDisplayViewOnce = false
        
        var displayingFlashTint = false
                    
        private let hapticFeedback = HapticFeedback()
        
        init(
            context: AccountContext,
            present: @escaping (ViewController) -> Void,
            startRecording: ActionSlot<Void>,
            stopRecording: ActionSlot<Void>,
            cancelRecording: ActionSlot<Void>,
            completion: ActionSlot<VideoMessageCameraScreen.CaptureResult>,
            getController: @escaping () -> VideoMessageCameraScreen? = {
                return nil
            }
        ) {
            self.context = context
            self.present = present
            self.startRecording = startRecording
            self.stopRecording = stopRecording
            self.cancelRecording = cancelRecording
            self.completion = completion
            self.getController = getController
            
            super.init()
            
            self.startRecording.connect({ [weak self] _ in
                if let self, let controller = getController() {
                    self.startVideoRecording(pressing: !controller.scheduledLock)
                    controller.scheduledLock = false
                    // Timestamp is set when the writer starts, after any countdown.
                }
            })
            self.stopRecording.connect({ [weak self] _ in
                self?.stopVideoRecording()
            })
            
            self.cancelRecording.connect({ [weak self] _ in
                self?.cancelVideoRecording()
            })
        }
        
        deinit {
            self.nagramiXPreparationTimer?.invalidate()
            self.nagramiXReadyDisposable.dispose()
            self.nagramiXStopDisposable.dispose()
            self.nagramiXCountdownTimer?.invalidate()
            self.nagramiXCountdownPositionDisposable?.dispose()
            if let observer = self.nagramiXCountdownBackgroundObserver {
                NotificationCenter.default.removeObserver(observer)
            }
            self.resultDisposable.dispose()
        }
        
        func toggleViewOnce() {
            guard let controller = self.getController() else {
                return
            }
            controller.updateCameraState({ $0.updatedIsViewOnceEnabled(!$0.isViewOnceEnabled) }, transition: .easeInOut(duration: 0.2))
        }
        
        private var lastFlipTimestamp: Double?
        func togglePosition() {
            guard !self.nagramiXStoppingRecording, !self.nagramiXSwitchingCamera, !self.nagramiXCancelled,
                  let controller = self.getController(), let camera = controller.camera, !controller.isDismissed else {
                return
            }
            let currentTimestamp = CACurrentMediaTime()
            if let lastFlipTimestamp = self.lastFlipTimestamp, currentTimestamp - lastFlipTimestamp < 1.0 {
                return
            }
            self.lastFlipTimestamp = currentTimestamp
            
            let isFrontCamera = controller.cameraState.position == .back
            if isFrontCamera && NagramiXTabSettings.current.selfieCountdown && self.nagramiXWriterRequested {
                self.nagramiXSwitchToSelfie()
                return
            }
            camera.togglePosition()
                                    
            self.hapticFeedback.impact(.veryLight)
            
            self.updateScreenBrightness(isFrontCamera: isFrontCamera)
            
            if isFrontCamera {
                camera.setTorchActive(false)
            } else {
                camera.setTorchActive(controller.cameraState.flashMode == .on)
            }
        }
        
        func toggleFlashMode() {
            guard let controller = self.getController(), let camera = controller.camera else {
                return
            }
            var isFlashOn = false
            switch controller.cameraState.flashMode {
            case .off:
                isFlashOn = true
                camera.setFlashMode(.on)
            case .on:
                camera.setFlashMode(.off)
            default:
                camera.setFlashMode(.off)
            }
            self.hapticFeedback.impact(.light)
            
            self.updateScreenBrightness(isFlashOn: isFlashOn)
            
            if controller.cameraState.position == .back {
                camera.setTorchActive(isFlashOn)
            }
        }
        
        private var initialBrightness: CGFloat?
        private var brightnessArguments: (Double, Double, CGFloat, CGFloat)?
        private var brightnessAnimator: ConstantDisplayLinkAnimator?
        
        func updateScreenBrightness(isFrontCamera: Bool? = nil, isFlashOn: Bool? = nil) {
            guard let controller = self.getController() else {
                return
            }
            let isFrontCamera = isFrontCamera ?? (controller.cameraState.position == .front)
            let isFlashOn = isFlashOn ?? (controller.cameraState.flashMode == .on)
            
            if isFrontCamera && isFlashOn {
                if self.initialBrightness == nil {
                    self.initialBrightness = mainWindowScreen.brightness
                    self.brightnessArguments = (CACurrentMediaTime(), 0.2, mainWindowScreen.brightness, 1.0)
                    self.animateBrightnessChange()
                }
            } else {
                if let initialBrightness = self.initialBrightness {
                    self.initialBrightness = nil
                    self.brightnessArguments = (CACurrentMediaTime(), 0.2, mainWindowScreen.brightness, initialBrightness)
                    self.animateBrightnessChange()
                }
            }
        }
        
        private func animateBrightnessChange() {
            if self.brightnessAnimator == nil {
                self.brightnessAnimator = ConstantDisplayLinkAnimator(update: { [weak self] in
                    self?.animateBrightnessChange()
                })
                self.brightnessAnimator?.isPaused = true
            }
            
            if let (startTime, duration, initial, target) = self.brightnessArguments {
                self.brightnessAnimator?.isPaused = false
                
                let t = CGFloat(max(0.0, min(1.0, (CACurrentMediaTime() - startTime) / duration)))
                let value = initial + (target - initial) * t
                
                mainWindowScreen.brightness = value
                
                if t >= 1.0 {
                    self.brightnessArguments = nil
                    self.brightnessAnimator?.isPaused = true
                    self.brightnessAnimator?.invalidate()
                    self.brightnessAnimator = nil
                }
            } else {
                self.brightnessAnimator?.isPaused = true
                self.brightnessAnimator?.invalidate()
                self.brightnessAnimator = nil
            }
        }
        
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
            // Publish only after state is coherent: replay can synchronously
            // enqueue/dismiss the controller from inside completion.invoke.
            controller.updateCameraState({ $0.updatedRecording(.none) }, transition: .spring(duration: 0.4))
            self.completion.invoke(result)
        }

        private func nagramiXStopWriter(forCameraSwitch: Bool, camera: CameraProtocol) {
            self.nagramiXStoppingRecording = true
            Logger.shared.log("NagramiX", "Round writer stop requested; cameraSwitch=\(forCameraSwitch)")
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
                self.brightnessArguments = (CACurrentMediaTime(), 0.2, mainWindowScreen.brightness, initialBrightness)
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
        func updateZoom(fraction: CGFloat) {
            guard let camera = self.getController()?.camera else {
                return
            }
            camera.setZoomLevel(fraction)
        }
    }
    
    func makeState() -> State {
        return State(context: self.context, present: self.present, startRecording: self.startRecording, stopRecording: self.stopRecording, cancelRecording: self.cancelRecording, completion: self.completion, getController: self.getController)
    }
    
    static var body: Body {
        let frontFlash = Child(Image.self)
        let flipButtonBackground = Child(GlassBackgroundComponent.self)
        let flipButton = Child(CameraButton.self)
        let flashButtonBackground = Child(GlassBackgroundComponent.self)
        let flashButton = Child(CameraButton.self)
        
        let viewOnceButton = Child(PlainButtonComponent.self)
        let recordMoreButton = Child(PlainButtonComponent.self)
        
        let muteIcon = Child(ZStack<Empty>.self)
        
        let flashAction = ActionSlot<Void>()
                        
        return { context in
            let environment = context.environment[ViewControllerComponentContainer.Environment.self].value
            let component = context.component
            let state = context.state
            let availableSize = context.component.containerSize
            
            var sideInset: CGFloat = 8.0
            if component.safeInsets.bottom <= 32.0 && environment.inputHeight == 0.0 {
                sideInset += 18.0
            }
            
            state.cameraState = component.cameraState
            
            var viewOnceOffset: CGFloat = 102.0
            
            var showViewOnce = false
            var showRecordMore = false
            if component.isPreviewing {
                showViewOnce = true
                if component.totalDuration < 59.0 {
                    showRecordMore = true
                    viewOnceOffset = 67.0
                } else {
                    viewOnceOffset = 14.0
                }
            } else if case .handsFree = component.cameraState.recording {
                showViewOnce = true
            }
            
            if let controller = component.getController() {
                if controller.scheduledLock {
                    showViewOnce = true
                }
                if !controller.viewOnceAvailable {
                    showViewOnce = false
                }
            }
            
            if state.didDisplayViewOnce {
                showViewOnce = true
            } else if showViewOnce {
                state.didDisplayViewOnce = true
            }
            
            if !component.isPreviewing {
                if case .on = component.cameraState.flashMode, case .front = component.cameraState.position {
                    let frontFlashPosition = CGPoint(x: component.previewFrame.midX, y: component.previewFrame.midY)
                    let frontFlashSize = CGSize(
                        width: max(abs(frontFlashPosition.x), abs(context.availableSize.width - frontFlashPosition.x)) * 2.0,
                        height: max(abs(frontFlashPosition.y), abs(context.availableSize.height - frontFlashPosition.y)) * 2.0
                    )
                    let frontFlash = frontFlash.update(
                        component: Image(image: state.image(.flashImage, theme: environment.theme), tintColor: component.cameraState.flashTint.color, contentMode: .scaleAspectFill),
                        availableSize: frontFlashSize,
                        transition: .easeInOut(duration: 0.2)
                    )
                    context.add(frontFlash
                        .position(frontFlashPosition)
                        .scale(1.5 - component.cameraState.flashTintSize * 0.5)
                        .appear(.default(alpha: true))
                        .disappear(ComponentTransition.Disappear({ view, transition, completion in
                            view.superview?.sendSubviewToBack(view)
                            transition.setAlpha(view: view, alpha: 0.0, completion: { _ in
                                completion()
                            })
                        }))
                    )
                }
                
                let flipButtonBackground = flipButtonBackground.update(
                    component: GlassBackgroundComponent(
                        size: CGSize(width: 40.0, height: 40.0),
                        cornerRadius: 40.0 * 0.5,
                        isDark: environment.theme.overallDarkAppearance,
                        tintColor: .init(kind: .panel)
                    ),
                    availableSize: CGSize(width: 40.0, height: 40.0),
                    transition: .immediate
                )
                
                let flipButton = flipButton.update(
                    component: CameraButton(
                        content: AnyComponentWithIdentity(
                            id: "flip",
                            component: AnyComponent(
                                Image(
                                    image: state.image(.flip, theme: environment.theme),
                                    tintColor: environment.theme.chat.inputPanel.panelControlColor,
                                    size: CGSize(width: 30.0, height: 30.0)
                                )
                            )
                        ),
                        minSize: CGSize(width: 40.0, height: 40.0),
                        isExclusive: false,
                        action: { [weak state] in
                            if let state {
                                state.togglePosition()
                            }
                        }
                    ),
                    availableSize: availableSize,
                    transition: context.transition
                )
                
                context.add(flipButtonBackground
                    .position(CGPoint(x: flipButton.size.width / 2.0 + sideInset, y: availableSize.height - flipButton.size.height / 2.0 - 8.0))
                    .appear(.default(scale: true, alpha: true))
                    .disappear(.default(scale: true, alpha: true))
                )
                context.add(flipButton
                    .position(CGPoint(x: flipButton.size.width / 2.0 + sideInset, y: availableSize.height - flipButton.size.height / 2.0 - 8.0))
                    .appear(.default(scale: true, alpha: true))
                    .disappear(.default(scale: true, alpha: true))
                )
                
                let flashContentComponent: AnyComponentWithIdentity<Empty>
                if "".isEmpty {
                    let flashIconName: String
                    switch component.cameraState.flashMode {
                    case .off:
                        flashIconName = "roundFlash_off"
                    case .on:
                        flashIconName = "roundFlash_on"
                    default:
                        flashIconName = "roundFlash_off"
                    }
                    
                    flashContentComponent = AnyComponentWithIdentity(
                        id: "animatedIcon",
                        component: AnyComponent(
                            LottieComponent(
                                content: LottieComponent.AppBundleContent(name: flashIconName),
                                color: environment.theme.chat.inputPanel.panelControlColor,
                                startingPosition: !component.cameraState.flashModeDidChange ? .end : .begin,
                                size: CGSize(width: 40.0, height: 40.0),
                                loop: false,
                                playOnce: flashAction
                            )
                        )
                    )
                } else {
                    flashContentComponent = AnyComponentWithIdentity(
                        id: "staticIcon",
                        component: AnyComponent(
                            Image(
                                image: state.image(.flash, theme: environment.theme),
                                tintColor: environment.theme.chat.inputPanel.panelControlColor,
                                size: CGSize(width: 30.0, height: 30.0)
                            )
                        )
                    )
                }
                
                if !environment.metrics.isTablet {
                    let flashButton = flashButton.update(
                        component: CameraButton(
                            content: flashContentComponent,
                            minSize: CGSize(width: 40.0, height: 40.0),
                            isExclusive: false,
                            action: { [weak state] in
                                if let state {
                                    state.toggleFlashMode()
                                    Queue.mainQueue().justDispatch {
                                        flashAction.invoke(Void())
                                    }
                                }
                            }
                        ),
                        availableSize: availableSize,
                        transition: context.transition
                    )
                    
                    let flashButtonBackground = flashButtonBackground.update(
                        component: GlassBackgroundComponent(
                            size: CGSize(width: 40.0, height: 40.0),
                            cornerRadius: 40.0 * 0.5,
                            isDark: environment.theme.overallDarkAppearance,
                            tintColor: .init(kind: .panel)
                        ),
                        availableSize: CGSize(width: 40.0, height: 40.0),
                        transition: .immediate
                    )
                    
                    context.add(flashButtonBackground
                        .position(CGPoint(x: flipButton.size.width + sideInset + flashButton.size.width / 2.0 + 11.0, y: availableSize.height - flashButton.size.height / 2.0 - 8.0))
                        .appear(.default(scale: true, alpha: true))
                        .disappear(.default(scale: true, alpha: true))
                    )
                    
                    context.add(flashButton
                        .position(CGPoint(x: flipButton.size.width + sideInset + flashButton.size.width / 2.0 + 11.0, y: availableSize.height - flashButton.size.height / 2.0 - 8.0))
                        .appear(.default(scale: true, alpha: true))
                        .disappear(.default(scale: true, alpha: true))
                    )
                }
            }
            
            // The view-once and record-more buttons (40pt circles) share one column, which keeps clear of a corner
            // block that reaches either of them.
            let trailingButtonSize: CGFloat = 40.0
            var trailingColumnRows: (minY: CGFloat, maxY: CGFloat)?
            if showViewOnce {
                trailingColumnRows = (availableSize.height - 8.0 - viewOnceOffset - trailingButtonSize, availableSize.height - 8.0 - viewOnceOffset)
            }
            if showRecordMore {
                let recordMoreRows: (minY: CGFloat, maxY: CGFloat) = (availableSize.height - 22.0 - trailingButtonSize, availableSize.height - 22.0)
                trailingColumnRows = trailingColumnRows.map { (min($0.minY, recordMoreRows.minY), max($0.maxY, recordMoreRows.maxY)) } ?? recordMoreRows
            }
            let trailingColumnInset = trailingColumnRows.map { videoMessageCameraTrailingControlInset(minY: $0.minY, maxY: $0.maxY, containerHeight: component.layoutHeight, safeInsets: component.safeInsets, reservedCorners: environment.reservedCorners) } ?? 0.0
            
            if showViewOnce {
                let viewOnceButton = viewOnceButton.update(
                    component: PlainButtonComponent(
                        content: AnyComponent(
                            ZStack([
                                AnyComponentWithIdentity(
                                    id: "background",
                                    component: AnyComponent(
                                        GlassBackgroundComponent(
                                            size: CGSize(width: 40.0, height: 40.0),
                                            cornerRadius: 40.0 * 0.5,
                                            isDark: environment.theme.overallDarkAppearance,
                                            tintColor: .init(kind: .panel)
                                        )
                                    )
                                ),
                                AnyComponentWithIdentity(
                                    id: "icon",
                                    component: AnyComponent(
                                        BundleIconComponent(
                                            name: component.cameraState.isViewOnceEnabled ? "Media Gallery/ViewOnceEnabled" : "Media Gallery/ViewOnce",
                                            tintColor: environment.theme.chat.inputPanel.panelControlColor
                                        )
                                    )
                                )
                            ])
                        ),
                        effectAlignment: .center,
                        action: { [weak state] in
                            if let state {
                                state.toggleViewOnce()
                            }
                        },
                        animateAlpha: false,
                        tag: viewOnceButtonTag
                    ),
                    availableSize: availableSize,
                    transition: context.transition
                )
                context.add(viewOnceButton
                    .position(CGPoint(x: availableSize.width - trailingColumnInset - viewOnceButton.size.width / 2.0 - sideInset, y: availableSize.height - viewOnceButton.size.height / 2.0 - 8.0 - viewOnceOffset))
                    .appear(.default(scale: true, alpha: true))
                    .disappear(.default(scale: true, alpha: true))
                )
            }
            
            if showRecordMore {
                let recordMoreButton = recordMoreButton.update(
                    component: PlainButtonComponent(
                        content: AnyComponent(
                            ZStack([
                                AnyComponentWithIdentity(
                                    id: "background",
                                    component: AnyComponent(GlassBackgroundComponent(
                                        size: CGSize(width: 40.0, height: 40.0),
                                        cornerRadius: 40.0 * 0.5,
                                        isDark: environment.theme.overallDarkAppearance,
                                        tintColor: .init(kind: .panel)
                                    ))
                                ),
                                AnyComponentWithIdentity(
                                    id: "icon",
                                    component: AnyComponent(
                                        BundleIconComponent(
                                            name: "Chat/Input/Text/IconVideo",
                                            tintColor: environment.theme.chat.inputPanel.panelControlColor
                                        )
                                    )
                                )
                            ])
                        ),
                        effectAlignment: .center,
                        action: { [weak state] in
                            state?.startVideoRecording(pressing: false)
                        }
                    ),
                    availableSize: availableSize,
                    transition: context.transition
                )
                context.add(recordMoreButton
                    .position(CGPoint(x: availableSize.width - trailingColumnInset - recordMoreButton.size.width / 2.0 - sideInset, y: availableSize.height - recordMoreButton.size.height / 2.0 - 22.0))
                    .appear(.default(scale: true, alpha: true))
                    .disappear(.default(scale: true, alpha: true))
                )
            }
            
            if component.isPreviewing && component.isMuted {
                let muteIcon = muteIcon.update(
                    component: ZStack([
                        AnyComponentWithIdentity(
                            id: "background",
                            component: AnyComponent(
                                RoundedRectangle(color: UIColor(rgb: 0x000000, alpha: 0.3), cornerRadius: 24.0)
                            )
                        ),
                        AnyComponentWithIdentity(
                            id: "icon",
                            component: AnyComponent(
                                BundleIconComponent(
                                    name: "Chat/Message/InstantVideoMute",
                                    tintColor: .white
                                )
                            )
                        )
                    ]),
                    availableSize: CGSize(width: 24.0, height: 24.0),
                    transition: context.transition
                )
                context.add(muteIcon
                    .position(CGPoint(x: component.previewFrame.midX, y: component.previewFrame.maxY - 24.0))
                    .appear(.default(scale: true, alpha: true))
                    .disappear(.default(scale: true, alpha: true))
                )
            }
            
            return context.availableSize
        }
    }
}

public class VideoMessageCameraScreen: ViewController {
    public enum CaptureResult {
        public struct Video {
            public let videoPath: String
            public let dimensions: PixelDimensions
            public let duration: Double
            public let thumbnail: UIImage
        }
        
        case video(Video)
    }
    
    fileprivate final class Node: ViewControllerTracingNode, ASGestureRecognizerDelegate {
        private weak var controller: VideoMessageCameraScreen?
        private let context: AccountContext
        private let cameraImpl: CameraImpl
        fileprivate var camera: CameraProtocol?
        private var pinchStartTimestamp: Double?
        private let updateState: ActionSlot<CameraState>
        
        fileprivate var liveUploadInterface: LegacyLiveUploadInterface?
        private var currentLiveUploadPath: String?
        fileprivate var currentLiveUploadData: LegacyLiveUploadInterfaceResult?
                
        fileprivate let backgroundView: UIVisualEffectView
        fileprivate let containerView: UIView
        fileprivate let componentHost: ComponentView<ViewControllerComponentContainer.Environment>
        fileprivate let previewContainerView: UIView
        fileprivate let previewContainerContentView: UIView
        private var previewSnapshotView: UIView?
        private var previewBlurView: BlurView
        
        fileprivate var mainPreviewView: CameraSimplePreviewView
        fileprivate var additionalPreviewView: CameraSimplePreviewView
        private var progressView: RecordingProgressView
        fileprivate var nagramiXCountdownPending = false
        fileprivate var nagramiXCameraSwitchPending = false
        fileprivate let nagramiXPreviewReadyDisposables = DisposableSet()
        private let nagramiXCountdownLabel = UILabel()

        fileprivate func nagramiXUpdateCountdown(_ value: Int?) {
            let changed = self.nagramiXCountdownLabel.text != value.map(String.init)
            self.nagramiXCountdownLabel.text = value.map(String.init)
            self.nagramiXCountdownLabel.isHidden = value == nil
            if changed, value != nil {
                self.nagramiXCountdownLabel.layer.removeAllAnimations()
                if !UIAccessibility.isReduceMotionEnabled {
                    self.nagramiXCountdownLabel.layer.animateScale(from: 1.12, to: 1.0, duration: 0.2)
                }
                UIAccessibility.post(notification: .announcement, argument: value.map(String.init))
            }
        }
        private let loadingView: LoadingEffectView
        
        private var resultPreviewView: ResultPreviewView?
        
        private var cameraStateDisposable: Disposable?
                
        private let idleTimerExtensionDisposable = MetaDisposable()
        
        fileprivate var cameraIsActive = true {
            didSet {
                if self.cameraIsActive {
                    self.idleTimerExtensionDisposable.set(self.context.sharedContext.applicationBindings.pushIdleTimerExtension())
                } else {
                    self.idleTimerExtensionDisposable.set(nil)
                }
            }
        }
        
        private var presentationData: PresentationData
        private var validLayout: ContainerViewLayout?
        
        fileprivate var didAppear: () -> Void = {}
        
        fileprivate let startRecording = ActionSlot<Void>()
        fileprivate let stopRecording = ActionSlot<Void>()
        fileprivate let cancelRecording = ActionSlot<Void>()
        private let completion = ActionSlot<VideoMessageCameraScreen.CaptureResult>()
                
        var cameraState: CameraState {
            didSet {
                if self.cameraState.isViewOnceEnabled != oldValue.isViewOnceEnabled {
                    if self.cameraState.isViewOnceEnabled {
                        let presentationData = self.context.sharedContext.currentPresentationData.with { $0 }
                        self.displayViewOnceTooltip(text: presentationData.strings.Chat_PlayVideoMessageOnceTooltip, hasIcon: true)
                        
                        let _ = ApplicationSpecificNotice.incrementVideoMessagesPlayOnceSuggestion(accountManager: self.context.sharedContext.accountManager, count: 3).startStandalone()
                    } else {
                        self.dismissAllTooltips()
                    }
                }
            }
        }
        var previewState: PreviewState? {
            didSet {
                self.previewStatePromise.set(.single(self.previewState))
                self.resultPreviewView?.isMuted = self.previewState?.isMuted ?? true
            }
        }
        var previewStatePromise = Promise<PreviewState?>()
        
        var transitioningToPreview = false
        fileprivate let nagramiXQuality: NagramiXRoundVideoSettings?
        private var nagramiXShowFPSFallback = false
        private var nagramiXShowCinematicFallback = false
        
        init(controller: VideoMessageCameraScreen) {
            self.controller = controller
            self.context = controller.context
            
            let requested = NagramiXRoundVideoSettings.current
            var quality: NagramiXRoundVideoSettings? = requested.enabled ? requested : nil
            if requested.enabled && requested.frameRate == .smooth {
                // Both positions are used by native camera switching. Validate the actual
                // NV12 formats accepted by the custom recorder, not merely a nominal FPS.
                let supported = [AVCaptureDevice.Position.front, .back].allSatisfy { position in
                    guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: position) else { return false }
                    return device.formats.contains { format in
                        let dimensions = CMVideoFormatDescriptionGetDimensions(format.formatDescription)
                        let subtype = CMFormatDescriptionGetMediaSubType(format.formatDescription)
                        return min(dimensions.width, dimensions.height) >= Int32(requested.quality.rawValue)
                            && max(dimensions.width, dimensions.height) <= 1920
                            && (subtype == kCVPixelFormatType_420YpCbCr8BiPlanarFullRange || subtype == kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange)
                            && format.videoSupportedFrameRateRanges.contains { $0.minFrameRate <= 60 && $0.maxFrameRate >= 60 }
                    }
                }
                let actualSupport = requested.cinematic ? NagramiXCinematicCapture.supports(requested) : supported
                if !actualSupport {
                    quality = requested.resolved(supports60FPS: false)
                    self.nagramiXShowFPSFallback = true
                }
            }
            if var resolved = quality, resolved.cinematic, !NagramiXCinematicCapture.supports(resolved) {
                let previous = resolved
                resolved.cinematic = false
                if NagramiXRoundVideoSettings.current == previous { NagramiXRoundVideoSettings.update(resolved) }
                quality = resolved
                self.nagramiXShowCinematicFallback = true
            }
            self.nagramiXQuality = quality
            let experimentalSettings = self.context.sharedContext.immediateExperimentalUISettings
            let useModernVideoMessagePipeline = experimentalSettings.useModernVideoMessagePipeline ?? (self.context.getAppConfigValue("ios_killswitch_disable_neo_round_camera_v2") == nil)
            let mode: NeoCameraImpl.RoundVideoMode?
            switch quality != nil ? .hdBilinear : (useModernVideoMessagePipeline ? experimentalSettings.videoMessageCameraMode : .legacy) {
            case .legacy:
                mode = nil
            case .vga:
                mode = .vga
            case .hdBilinear:
                mode = .hdBilinear
            case .hdLanczos:
                mode = .hdLanczos
            }
            if let mode {
                self.cameraImpl = NeoCameraImpl(roundVideoMode: mode, log: { message in
                    Logger.shared.log("CameraNeo", message)
                })
            } else {
                self.cameraImpl = LegacyCameraImpl.shared
            }
            self.updateState = ActionSlot<CameraState>()
            
            self.presentationData = controller.updatedPresentationData?.initial ?? self.context.sharedContext.currentPresentationData.with { $0 }
            
            self.backgroundView = UIVisualEffectView(effect: UIBlurEffect(style: self.presentationData.theme.overallDarkAppearance ? .dark : .light))
            
            self.containerView = UIView()
            
            self.componentHost = ComponentView<ViewControllerComponentContainer.Environment>()
            
            self.previewContainerView = UIView()
            
            self.previewContainerContentView = UIView()
            self.previewContainerContentView.clipsToBounds = true
            self.previewContainerView.addSubview(self.previewContainerContentView)
                        
            let isDualCameraEnabled = quality == nil && cameraImpl.isDualCameraSupported(forRoundVideo: true)
            let prefersRearCamera = NagramiXTabSettings.current.useRearCameraForVideoMessages
            let isFrontPosition = !prefersRearCamera
            Logger.shared.log("NagramiX", "Round video initial camera preference: rear=\(prefersRearCamera), position=\(isFrontPosition ? "front" : "back")")
            
            self.mainPreviewView = cameraImpl.makeCameraSimplePreviewView(frame: .zero, main: true, roundVideo: true)
            self.additionalPreviewView = cameraImpl.makeCameraSimplePreviewView(frame: .zero, main: false, roundVideo: true)
            
            self.progressView = RecordingProgressView(frame: .zero)
            
            self.loadingView = LoadingEffectView(effectAlpha: 0.1, borderAlpha: 0.25, duration: 1.0)
            
            self.previewBlurView = BlurView()
            self.previewBlurView.isUserInteractionEnabled = false
            
            if isDualCameraEnabled {
                self.mainPreviewView.resetPlaceholder(front: false)
                self.additionalPreviewView.resetPlaceholder(front: true)
            } else {
                self.mainPreviewView.resetPlaceholder(front: isFrontPosition)
            }
            
            self.cameraState = CameraState(
                position: isFrontPosition ? .front : .back,
                flashMode: .off,
                flashModeDidChange: false,
                flashTint: .white,
                flashTintSize: 1.0,
                recording: .none,
                duration: 0.0,
                isDualCameraEnabled: isDualCameraEnabled,
                isViewOnceEnabled: NagramiXRecordingSettings.initialViewOnce(available: controller.viewOnceAvailable)
            )
            
            self.previewState = nil
            
            super.init()
            
            self.backgroundColor = .clear
            
            self.view.addSubview(self.containerView)
            
            self.containerView.addSubview(self.previewContainerView)

            self.previewContainerContentView.addSubview(self.mainPreviewView)
            if isDualCameraEnabled {
                self.previewContainerContentView.addSubview(self.additionalPreviewView)
            }
            self.previewContainerContentView.addSubview(self.progressView)
            self.previewContainerContentView.addSubview(self.previewBlurView)
            self.previewContainerContentView.addSubview(self.loadingView)
            self.nagramiXCountdownLabel.font = Font.semibold(88.0)
            self.nagramiXCountdownLabel.textColor = .white
            self.nagramiXCountdownLabel.textAlignment = .center
            self.nagramiXCountdownLabel.isUserInteractionEnabled = false
            self.nagramiXCountdownLabel.isHidden = true
            self.nagramiXCountdownLabel.layer.shadowColor = UIColor.black.cgColor
            self.nagramiXCountdownLabel.layer.shadowOpacity = 0.2
            self.nagramiXCountdownLabel.layer.shadowRadius = 3.0
            self.nagramiXCountdownLabel.layer.shadowOffset = CGSize(width: 0.0, height: 1.0)
            self.previewContainerContentView.addSubview(self.nagramiXCountdownLabel)
            
            self.completion.connect { [weak self] result in
                if let self {
                    self.addCaptureResult(result)
                }
            }
            if isDualCameraEnabled {
                self.mainPreviewView.removePlaceholder(delay: 0.0)
            }
            self.withReadyCamera(isFirstTime: true, { [weak self] in
                guard let self else {
                    return
                }
                if !isDualCameraEnabled {
                    self.mainPreviewView.removePlaceholder(delay: 0.0)
                }
                self.loadingView.alpha = 0.0
                self.additionalPreviewView.removePlaceholder(delay: 0.0)
            })
                        
            self.idleTimerExtensionDisposable.set(self.context.sharedContext.applicationBindings.pushIdleTimerExtension())
        }
        
        deinit {
            self.nagramiXCompositionDisposable.dispose()
            self.nagramiXPreviewReadyDisposables.dispose()
            self.cameraStateDisposable?.dispose()
            self.idleTimerExtensionDisposable.dispose()
            self.backgroundView.removeFromSuperview()
        }
        
        func withReadyCamera(isFirstTime: Bool = false, _ f: @escaping () -> Void) {
            let previewReady: Signal<Bool, NoError>
            if #available(iOS 13.0, *) {
                previewReady = self.cameraState.isDualCameraEnabled ? self.additionalPreviewView.isPreviewing : self.mainPreviewView.isPreviewing |> delay(0.3, queue: Queue.mainQueue())
            } else {
                previewReady = .single(true) |> delay(0.35, queue: Queue.mainQueue())
            }
            
            self.nagramiXPreviewReadyDisposables.add((previewReady
            |> filter { $0 }
            |> take(1)
            |> deliverOnMainQueue).start(next: { _ in
                f()
            }))
        }
        
        func setupLiveUpload(filePath: String) {
            guard let controller = self.controller, controller.allowLiveUpload, self.liveUploadInterface == nil else {
                return
            }
            let liveUploadInterface = LegacyLiveUploadInterface(context: self.context)
            Queue.mainQueue().after(1.5, {
                liveUploadInterface.setup(withFileURL: URL(fileURLWithPath: filePath))
            })
            self.liveUploadInterface = liveUploadInterface
        }
        
        override func didLoad() {
            super.didLoad()
            
            self.view.disablesInteractiveModalDismiss = true
            self.view.disablesInteractiveKeyboardGestureRecognizer = true
            
            let pinchGestureRecognizer = UIPinchGestureRecognizer(target: self, action: #selector(self.handlePinch(_:)))
            self.view.addGestureRecognizer(pinchGestureRecognizer)
        }
                
        fileprivate func setupCamera() {
            guard self.camera == nil else {
                return
            }
            
            let camera = self.cameraImpl.makeCamera(
                configuration: Camera.Configuration(
                    preset: .hd1920x1080,
                    position: self.cameraState.position,
                    isDualEnabled: self.cameraState.isDualCameraEnabled,
                    audio: true,
                    photo: false,
                    metadata: false,
                    isRoundVideo: true,
                    nagramiXQuality: self.nagramiXQuality
                ),
                previewView: self.mainPreviewView,
                secondaryPreviewView: self.additionalPreviewView
            )
            
            self.cameraStateDisposable = combineLatest(
                queue: Queue.mainQueue(),
                camera.flashMode,
                camera.position
            ).startStrict(next: { [weak self] flashMode, position in
                guard let self else {
                    return
                }
                self.cameraState = self.cameraState.updatedPosition(position).updatedFlashMode(flashMode)
                
                if !self.cameraState.isDualCameraEnabled {
                    self.animatePositionChange()
                }
                
                self.requestUpdateLayout(transition: .easeInOut(duration: 0.2))
            })
            
            camera.focus(at: CGPoint(x: 0.5, y: 0.5), autoFocus: true)
            camera.startCapture()
            if self.nagramiXShowFPSFallback || self.nagramiXShowCinematicFallback {
                let cinematicMessage = self.nagramiXShowCinematicFallback ? self.presentationData.strings.nagramiXUILocalized("Киноэффект недоступен на этом устройстве с выбранными параметрами и выключен. ") : ""
                let fpsMessage = self.nagramiXShowFPSFallback ? self.presentationData.strings.nagramiXUILocalized("Ваше устройство не поддерживает запись кружков с выбранным качеством при 60 FPS. Установлено 30 FPS. ") : ""
                self.nagramiXShowCinematicFallback = false
                self.nagramiXShowFPSFallback = false
                Queue.mainQueue().async { [weak self] in
                    guard let self, let controller = self.controller else { return }
                    controller.present(textAlertController(context: self.context, title: nil,
                        text: cinematicMessage + fpsMessage + self.presentationData.strings.nagramiXUILocalized("Остальные параметры качества сохранены."),
                        actions: [TextAlertAction(type: .defaultAction, title: self.presentationData.strings.Common_OK, action: {})]), in: .window(.root))
                }
            }
            
            self.camera = camera
            
            Queue.mainQueue().justDispatch {
                self.startRecording.invoke(Void())
            }
        }
        
        @objc private func handlePinch(_ gestureRecognizer: UIPinchGestureRecognizer) {
            switch gestureRecognizer.state {
            case .began:
                self.pinchStartTimestamp = CACurrentMediaTime()
            case .changed:
                guard let camera = self.camera else {
                    return
                }
                let scale = gestureRecognizer.scale
                camera.setZoomDelta(scale)
                gestureRecognizer.scale = 1.0
            case .ended:
                let pinchStartTimestamp = self.pinchStartTimestamp
                self.pinchStartTimestamp = nil
                if let pinchStartTimestamp, CACurrentMediaTime() - pinchStartTimestamp <= 0.5 {
                    return
                }
                self.camera?.rampZoom(1.0, rate: 8.0)
            case .cancelled:
                self.pinchStartTimestamp = nil
                self.camera?.rampZoom(1.0, rate: 8.0)
            case .failed:
                self.pinchStartTimestamp = nil
            default:
                break
            }
        }
                
        private var animatingIn = false
        func animateIn() {
            self.animatingIn = true
            
            self.backgroundView.alpha = 0.0
            UIView.animate(withDuration: 0.4, animations: {
                self.backgroundView.alpha = 1.0
            })
            
            let targetPosition = self.previewContainerView.center
            self.previewContainerView.center = CGPoint(x: targetPosition.x, y: self.frame.height + self.previewContainerView.frame.height / 2.0)
            
            UIView.animate(withDuration: 0.5, delay: 0.0, usingSpringWithDamping: 0.8, initialSpringVelocity: 0.2, animations: {
                self.previewContainerView.center = targetPosition
            }, completion: { [weak self] _ in
                self?.animatingIn = false
            })
            
            if let view = self.componentHost.view {
                view.layer.animateAlpha(from: 0.1, to: 1.0, duration: 0.25)
            }
        }

        func animateOut(completion: @escaping () -> Void) {
            self.camera?.stopCapture(invalidate: true)
                                    
            UIView.animate(withDuration: 0.25, animations: {
                self.backgroundView.alpha = 0.0
            }, completion: { [weak self] _ in
                self?.backgroundView.removeFromSuperview()
                completion()
            })
            
            self.componentHost.view?.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.15, removeOnCompletion: false)
            self.previewContainerView.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.25, removeOnCompletion: false)
        }
        
        private func animatePositionChange() {
            self.previewSnapshotView?.removeFromSuperview()
            self.previewSnapshotView = nil
            guard let snapshot = self.mainPreviewView.snapshotView(afterScreenUpdates: false) else { return }
            self.previewContainerContentView.insertSubview(snapshot, belowSubview: self.progressView)
            self.previewSnapshotView = snapshot
            self.requestUpdateLayout(transition: .immediate)
            Queue.mainQueue().after(0.35) { [weak self, weak snapshot] in
                guard let self, let snapshot, self.previewSnapshotView === snapshot else { return }
                UIView.animate(withDuration: 0.2, animations: {
                    snapshot.alpha = 0.0
                }, completion: { [weak self, weak snapshot] _ in
                    snapshot?.removeFromSuperview()
                    if self?.previewSnapshotView === snapshot { self?.previewSnapshotView = nil }
                })
            }
        }

        func pauseCameraCapture() {
            self.mainPreviewView.isEnabled = false
            self.additionalPreviewView.isEnabled = false
            self.camera?.stopCapture()
            
            self.cameraIsActive = false
            self.requestUpdateLayout(transition: .immediate)
        }
        
        func resumeCameraCapture() {
            self.nagramiXCompositionDisposable.set(nil)
            self.transitioningToPreview = false
            if !self.mainPreviewView.isEnabled {
                if let snapshotView = self.resultPreviewView?.snapshotView(afterScreenUpdates: false) {
                    self.previewContainerContentView.insertSubview(snapshotView, belowSubview: self.previewBlurView)
                    self.previewSnapshotView = snapshotView
                }
                self.mainPreviewView.isEnabled = true
                self.additionalPreviewView.isEnabled = true
                self.camera?.startCapture()
                
                UIView.animate(withDuration: 0.25, animations: {
                    self.loadingView.alpha = 1.0
                    self.previewBlurView.effect = UIBlurEffect(style: .dark)
                })
                
                let action = { [weak self] in
                    guard let self else {
                        return
                    }
                    UIView.animate(withDuration: 0.4, animations: {
                        self.previewBlurView.effect = nil
                        self.previewSnapshotView?.alpha = 0.0
                    }, completion: { [weak self] _ in
                        self?.previewSnapshotView?.removeFromSuperview()
                        self?.previewSnapshotView = nil
                    })
                }
                let _ = (self.mainPreviewView.isPreviewing
                |> filter { $0 }
                |> take(1)).startStandalone(next: { _ in
                    action()
                })
                
                self.cameraIsActive = true
                self.requestUpdateLayout(transition: .immediate)
            }
        }
        
        fileprivate var results: [VideoMessageCameraScreen.CaptureResult] = []
        // Only final stops advance this revision. Retained camera-switch
        // fragments are not a completed recording for a send/preview waiter.
        fileprivate var nagramiXCompletedRevision = 0
        fileprivate let nagramiXCompletedResults = Promise<(revision: Int, results: [VideoMessageCameraScreen.CaptureResult])>()
        fileprivate let nagramiXCompositionDisposable = MetaDisposable()
        
        fileprivate func nagramiXAppendSwitchResult(_ result: VideoMessageCameraScreen.CaptureResult) {
            // A sealed fragment in the same outgoing message, without pausing preview.
            if self.results.isEmpty { _ = self.liveUploadInterface?.fileUpdated(true) }
            self.currentLiveUploadData = nil
            self.results.append(result)
        }

        func addCaptureResult(_ result: VideoMessageCameraScreen.CaptureResult) {
            guard let controller = self.controller else {
                return
            }
            
            if self.results.isEmpty {
                if let liveUploadData = self.liveUploadInterface?.fileUpdated(true) as? LegacyLiveUploadInterfaceResult {
                    self.currentLiveUploadData = liveUploadData
                }
            } else {
                self.currentLiveUploadData = nil
            }
            
            let _ = ApplicationSpecificNotice.incrementVideoMessagesPauseSuggestion(accountManager: self.context.sharedContext.accountManager, count: 3).startStandalone()
            
            self.pauseCameraCapture()
            
            self.results.append(result)
            self.nagramiXCompletedRevision += 1
            Logger.shared.log("NagramiX", "Round recording finalized; segments=\(self.results.count)")
            self.nagramiXCompletedResults.set(.single((revision: self.nagramiXCompletedRevision, results: self.results)))
            
            if !controller.isSendingImmediately && !controller.didSend && !controller.isDismissed {
                let revision = self.nagramiXCompletedRevision
                let request = MetaDisposable()
                self.nagramiXCompositionDisposable.set(request)
                Logger.shared.log("NagramiX", "Round preview preparation started")
                request.set(nagramiXRecordingComposition(with: self.results).start(next: { [weak self, weak controller] composition in
                    guard let self, let controller, !controller.isDismissed,
                          !controller.didSend, !controller.isSendingImmediately,
                          self.nagramiXCompletedRevision == revision,
                          case .none = controller.cameraState.recording else { return }
                    self.transitioningToPreview = false
                    Logger.shared.log("NagramiX", "Round preview preparation finished")
                    controller.updatePreviewState({ _ in
                        return PreviewState(composition: composition, trimRange: nil, isMuted: true)
                    }, transition: .spring(duration: 0.4))
                }))
            } else {
                self.transitioningToPreview = false
            }
        }
        
        private func debugSaveResult(path: String) {
            guard let data = try? Data(contentsOf: URL(fileURLWithPath: path), options: .mappedIfSafe) else {
                return
            }
            let id = Int64.random(in: Int64.min ... Int64.max)
            let fileResource = LocalFileReferenceMediaResource(localFilePath: path, randomId: id)
            
            let file = TelegramMediaFile(fileId: EngineMedia.Id(namespace: Namespaces.Media.LocalFile, id: id), partialReference: nil, resource: fileResource, previewRepresentations: [], videoThumbnails: [], immediateThumbnailData: nil, mimeType: "video/mp4", size: Int64(data.count), attributes: [.FileName(fileName: "video.mp4")], alternativeRepresentations: [])
            let message: EnqueueMessage = .message(text: "", attributes: [], inlineStickers: [:], mediaReference: .standalone(media: file), threadId: nil, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: nil, correlationId: nil, bubbleUpEmojiOrStickersets: [])

            let _ = enqueueMessages(account: self.context.engine.account, peerId: self.context.engine.account.peerId, messages: [message]).startStandalone()
        }
        
        /// Whether `view` is a control the component host put on screen (the record-more, view-once,
        /// flip and flash buttons are all `UIButton`s; the mute badge and the front-flash image are not).
        private func isComponentControl(_ view: UIView?) -> Bool {
            guard let view, let componentView = self.componentHost.view, view.isDescendant(of: componentView) else {
                return false
            }
            if view is UIControl {
                return true
            }
            if let gestureRecognizers = view.gestureRecognizers, !gestureRecognizers.isEmpty {
                return true
            }
            return false
        }
        
        override func hitTest(_ point: CGPoint, with event: UIEvent?) -> UIView? {
            let result = super.hitTest(point, with: event)
            
            // The preview is claimed by its *bounding square*, while only the inscribed circle is
            // visible - `previewContainerContentView` clips to a corner radius. The component host is a
            // full-screen sibling above `previewContainerView`, and when the keyboard is up the container
            // is only as tall as the input panel's top edge, so on a small screen the controls pinned to
            // its bottom edge sit inside that square's bottom corners while remaining outside the circle.
            // `super.hitTest` has already resolved which of the two the touch really landed on, so only
            // fall back to the preview when it did not land on a control. Over the input panel's rows the
            // square's corners cover the panel's trash and send, so there only the circle is the preview's.
            var passesToInputPanel = false
            if let controller = self.controller, let layout = self.validLayout {
                let insets = layout.insets(options: .input)
                passesToInputPanel = videoMessageCameraPassesTouchToInputPanel(y: point.y, layoutHeight: layout.size.height, bottomInset: max(insets.bottom, layout.additionalInsets.bottom), inputPanelFrame: controller.inputPanelFrame.0, hasInputNode: controller.inputPanelFrame.1)
            }
            
            if let resultPreviewView = self.resultPreviewView, !self.isComponentControl(result) {
                if videoMessageCameraPreviewClaimsTouch(point: self.view.convert(point, to: resultPreviewView), bounds: resultPreviewView.bounds, overInputPanel: passesToInputPanel) {
                    return resultPreviewView
                }
            }
            
            if passesToInputPanel, let layout = self.validLayout {
                if layout.metrics.isTablet {
                    if point.x < layout.size.width * 0.33 {
                        return result
                    }
                }
                return nil
            }
            
            return result
        }
        
        fileprivate func maybePresentTooltips() {
            let presentationData = self.context.sharedContext.currentPresentationData.with { $0 }
            
            let _ = (ApplicationSpecificNotice.getVideoMessagesPauseSuggestion(accountManager: self.context.sharedContext.accountManager)
            |> deliverOnMainQueue).startStandalone(next: { [weak self] pauseCounter in
                guard let self else {
                    return
                }
                
                if pauseCounter >= 3 {
                    let _ = (ApplicationSpecificNotice.getVideoMessagesPlayOnceSuggestion(accountManager: self.context.sharedContext.accountManager)
                    |> deliverOnMainQueue).startStandalone(next: { [weak self] counter in
                        guard let self else {
                            return
                        }
                        if counter >= 3 {
                            return
                        }
                        Queue.mainQueue().after(0.3) {
                            self.displayViewOnceTooltip(text: presentationData.strings.Chat_TapToPlayVideoMessageOnceTooltip, hasIcon: true)
                        }
                        let _ = ApplicationSpecificNotice.incrementVideoMessagesPlayOnceSuggestion(accountManager: self.context.sharedContext.accountManager).startStandalone()
                    })
                } else {
                    Queue.mainQueue().after(0.3) {
                        self.displayPauseTooltip(text: presentationData.strings.Chat_PauseVideoMessageTooltip)
                    }
                    let _ = ApplicationSpecificNotice.incrementVideoMessagesPauseSuggestion(accountManager: self.context.sharedContext.accountManager).startStandalone()
                }
            })
        }
        
        private func displayViewOnceTooltip(text: String, hasIcon: Bool) {
            guard let controller = self.controller, let sourceView = self.componentHost.findTaggedView(tag: viewOnceButtonTag) else {
                return
            }
            
            self.dismissAllTooltips()
            
            let absoluteFrame = sourceView.convert(sourceView.bounds, to: self.view)
            let location = CGRect(origin: CGPoint(x: absoluteFrame.midX - 20.0, y: absoluteFrame.midY), size: CGSize())
            
            let tooltipController = TooltipScreen(
                account: context.account,
                sharedContext: context.sharedContext,
                text: .markdown(text: text),
                balancedTextLayout: true,
                constrainWidth: 240.0,
                style: .customBlur(UIColor(rgb: 0x18181a), 0.0),
                arrowStyle: .small,
                icon: hasIcon ? .animation(name: "anim_autoremove_on", delay: 0.1, tintColor: nil) : nil,
                location: .point(location, .right),
                displayDuration: .default,
                inset: 8.0,
                cornerRadius: 8.0,
                shouldDismissOnTouch: { _, _ in
                    return .ignore
                }
            )
            controller.present(tooltipController, in: .window(.root))
        }
        
        private func displayPauseTooltip(text: String) {
            guard let controller = self.controller, let sourceView = self.componentHost.findTaggedView(tag: viewOnceButtonTag) else {
                return
            }
            
            self.dismissAllTooltips()
            
            let absoluteFrame = sourceView.convert(sourceView.bounds, to: self.view)
            // The tooltip points at the chat's pause button, under the view-once button unless that one keeps clear of
            // iPhone Duo's status corner (the pause button stays in the input panel's column).
            var columnInset: CGFloat = 0.0
            if let layout = self.validLayout {
                columnInset = videoMessageCameraTrailingControlInset(minY: absoluteFrame.minY, maxY: absoluteFrame.maxY, containerHeight: layout.size.height, safeInsets: layout.safeInsets, reservedCorners: layout.reservedCorners)
            }
            let location = CGRect(origin: CGPoint(x: absoluteFrame.midX + columnInset - 20.0, y: absoluteFrame.midY + 53.0), size: CGSize())
            
            let tooltipController = TooltipScreen(
                account: context.account,
                sharedContext: context.sharedContext,
                text: .markdown(text: text),
                balancedTextLayout: true,
                constrainWidth: 240.0,
                style: .customBlur(UIColor(rgb: 0x18181a), 0.0),
                arrowStyle: .small,
                icon: nil,
                location: .point(location, .right),
                displayDuration: .default,
                inset: 8.0,
                cornerRadius: 8.0,
                shouldDismissOnTouch: { _, _ in
                    return .ignore
                }
            )
            controller.present(tooltipController, in: .window(.root))
        }

        fileprivate func dismissAllTooltips() {
            guard let controller = self.controller else {
                return
            }
            controller.window?.forEachController({ controller in
                if let controller = controller as? TooltipScreen {
                    controller.dismiss()
                }
            })
            controller.forEachController({ controller in
                if let controller = controller as? TooltipScreen {
                    controller.dismiss()
                }
                return true
            })
        }
        
        func updateTrimRange(start: Double, end: Double, updatedEnd: Bool, apply: Bool) {
            guard let controller = self.controller else {
                return
            }
            self.resultPreviewView?.updateTrimRange(start: start, end: end, updatedEnd: updatedEnd, apply: apply)
            controller.updatePreviewState({ state in
                if let state {
                    return PreviewState(composition: state.composition, trimRange: start..<end, isMuted: state.isMuted)
                } else {
                    return nil
                }
            }, transition: .immediate)
        }
        
        @objc func resultTapped() {
            guard let controller = self.controller else {
                return
            }
            controller.updatePreviewState({ state in
                if let state {
                    return PreviewState(composition: state.composition, trimRange: state.trimRange, isMuted: !state.isMuted)
                } else {
                    return nil
                }
            }, transition: .easeInOut(duration: 0.2))
        }
        
        func requestUpdateLayout(transition: ComponentTransition) {
            if let layout = self.validLayout {
                self.containerLayoutUpdated(layout: layout, forceUpdate: true, transition: transition)
            }
        }

        func containerLayoutUpdated(layout: ContainerViewLayout, forceUpdate: Bool = false, transition: ComponentTransition) {
            guard let controller = self.controller else {
                return
            }
            let isFirstTime = self.validLayout == nil
            self.validLayout = layout
            
            let environment = ViewControllerComponentContainer.Environment(
                statusBarHeight: layout.statusBarHeight ?? 0.0,
                navigationHeight: 0.0,
                safeInsets: UIEdgeInsets(
                    top: (layout.statusBarHeight ?? 0.0) + 5.0,
                    left: layout.safeInsets.left,
                    bottom: 44.0,
                    right: layout.safeInsets.right
                ),
                reservedCorners: layout.reservedCorners,
                additionalInsets: layout.additionalInsets,
                inputHeight: layout.inputHeight ?? 0.0,
                metrics: layout.metrics,
                deviceMetrics: layout.deviceMetrics,
                orientation: nil,
                isVisible: true,
                theme: self.presentationData.theme,
                strings: self.presentationData.strings,
                dateTimeFormat: self.presentationData.dateTimeFormat,
                controller: { [weak self] in
                    return self?.controller
                }
            )

            if isFirstTime {
                self.didAppear()
            }

            var backgroundFrame = CGRect(origin: .zero, size: CGSize(width: layout.size.width, height: controller.inputPanelFrame.0.minY))
            let actualBackgroundFrame = CGRect(origin: .zero, size: CGSize(width: layout.size.width, height: layout.size.height))
            if backgroundFrame.maxY < layout.size.height - 100.0 && (layout.inputHeight ?? 0.0).isZero && !controller.inputPanelFrame.1 && layout.additionalInsets.bottom.isZero {
                backgroundFrame = CGRect(origin: .zero, size: CGSize(width: layout.size.width, height: layout.size.height - layout.intrinsicInsets.bottom - controller.inputPanelFrame.0.height - 8.0))
            }
                        
            transition.setPosition(view: self.backgroundView, position: actualBackgroundFrame.center)
            transition.setBounds(view: self.backgroundView, bounds: CGRect(origin: .zero, size: actualBackgroundFrame.size))
            
            transition.setPosition(view: self.containerView, position: backgroundFrame.center)
            transition.setBounds(view: self.containerView, bounds: CGRect(origin: .zero, size: backgroundFrame.size))
                        
            let availableHeight = layout.size.height - (layout.inputHeight ?? 0.0)
            // iPhone Duo: the circle keeps to the band beside the side strip (folded portrait: clear of the status
            // corner at the strip's top). Equal insets keep it centred on the full width.
            let previewBandInsets: (left: CGFloat, right: CGFloat) = layout.safeInsets.left != layout.safeInsets.right ? (layout.safeInsets.left, layout.safeInsets.right) : (0.0, 0.0)
            let previewBandWidth = layout.size.width - previewBandInsets.left - previewBandInsets.right
            let previewSide = min(369.0, previewBandWidth - 24.0)
            var previewFrame: CGRect
            if layout.metrics.isTablet {
                // Use the scene this view actually lives in; `connectedScenes` is unordered and a
                // tablet can have several window scenes.
                let statusBarOrientation = self.containerView.window?.windowScene?.interfaceOrientation ?? .portrait
                
                // The side the circle sits at keeps that side's strip inset too (iPhone Duo's unfolded screen in landscape).
                if statusBarOrientation == .landscapeLeft {
                    previewFrame = CGRect(origin: CGPoint(x: layout.size.width - previewBandInsets.right - 44.0 - previewSide, y: floorToScreenPixels((layout.size.height - previewSide) / 2.0)), size: CGSize(width: previewSide, height: previewSide))
                } else if statusBarOrientation == .landscapeRight {
                    previewFrame = CGRect(origin: CGPoint(x: previewBandInsets.left + 44.0, y: floorToScreenPixels((layout.size.height - previewSide) / 2.0)), size: CGSize(width: previewSide, height: previewSide))
                } else {
                    previewFrame = CGRect(origin: CGPoint(x: floorToScreenPixels((layout.size.width - previewSide) / 2.0), y: max(layout.statusBarHeight ?? 0.0 + 24.0, availableHeight * 0.2 - previewSide / 2.0)), size: CGSize(width: previewSide, height: previewSide))
                }
            } else {
                previewFrame = CGRect(origin: CGPoint(x: previewBandInsets.left + floorToScreenPixels((previewBandWidth - previewSide) / 2.0), y: max(layout.statusBarHeight ?? 0.0 + 24.0, availableHeight * 0.4 - previewSide / 2.0)), size: CGSize(width: previewSide, height: previewSide))
                // iPhone Duo: the folded screen is too short for the phone placement above a keyboard.
                if layout.reservedCorners != .none {
                    previewFrame = videoMessageCameraPreviewFrameAbovePanel(frame: previewFrame, bandMinX: previewBandInsets.left, bandMaxX: layout.size.width - previewBandInsets.right, topY: max(layout.statusBarHeight ?? 0.0, layout.safeInsets.top) + 12.0, panelTop: backgroundFrame.maxY)
                }
            }
            if !self.animatingIn {
                transition.setFrame(view: self.previewContainerView, frame: previewFrame)
                transition.setFrame(view: self.previewContainerContentView, frame: CGRect(origin: CGPoint(), size: previewFrame.size))
            }
            transition.setCornerRadius(layer: self.previewContainerContentView.layer, cornerRadius: previewFrame.width / 2.0)
                        
            let previewBounds = CGRect(origin: .zero, size: previewFrame.size)
           
            let previewInnerSize: CGSize
            let additionalPreviewInnerSize: CGSize
            
            if self.cameraState.isDualCameraEnabled {
                previewInnerSize = CGSize(width: previewFrame.size.width, height: previewFrame.size.width / 9.0 * 16.0)
                additionalPreviewInnerSize = CGSize(width: previewFrame.size.width, height: previewFrame.size.width / 3.0 * 4.0)
            } else {
                previewInnerSize = CGSize(width: previewFrame.size.width, height: previewFrame.size.width / 3.0 * 4.0)
                additionalPreviewInnerSize = CGSize(width: previewFrame.size.width, height: previewFrame.size.width / 3.0 * 4.0)
            }
            
            let previewInnerFrame = CGRect(origin: CGPoint(x: 0.0, y: floorToScreenPixels((previewFrame.height - previewInnerSize.height) / 2.0)), size: previewInnerSize)
            
            let additionalPreviewInnerFrame = CGRect(origin: CGPoint(x: 0.0, y: floorToScreenPixels((previewFrame.height - additionalPreviewInnerSize.height) / 2.0)), size: additionalPreviewInnerSize)
            if self.cameraState.isDualCameraEnabled {
                self.mainPreviewView.frame = previewInnerFrame
                self.additionalPreviewView.frame = additionalPreviewInnerFrame
            } else {
                self.mainPreviewView.frame = self.cameraState.position == .front ? additionalPreviewInnerFrame : previewInnerFrame
            }
            
            self.progressView.frame = previewBounds
            self.progressView.value = CGFloat(self.cameraState.duration / 60.0)
            
            transition.setAlpha(view: self.additionalPreviewView, alpha: self.cameraState.position == .front ? 1.0 : 0.0)
            
            self.nagramiXCountdownLabel.frame = previewBounds
            self.previewBlurView.frame = previewBounds
            self.previewSnapshotView?.center = previewBounds.center
            self.loadingView.update(size: previewBounds.size, transition: .immediate)
            
            let componentSize = self.componentHost.update(
                transition: transition,
                component: AnyComponent(
                    VideoMessageCameraScreenComponent(
                        context: self.context,
                        cameraState: self.cameraState,
                        containerSize: backgroundFrame.size,
                        previewFrame: previewFrame,
                        safeInsets: layout.safeInsets,
                        layoutHeight: layout.size.height,
                        isPreviewing: self.previewState != nil || self.transitioningToPreview,
                        isMuted: self.previewState?.isMuted ?? true,
                        totalDuration: self.previewState?.composition.duration.seconds ?? 0.0,
                        getController: { [weak self] in
                            return self?.controller
                        },
                        present: { [weak self] c in
                            self?.controller?.present(c, in: .window(.root))
                        },
                        push: { [weak self] c in
                            self?.controller?.push(c)
                        },
                        startRecording: self.startRecording,
                        stopRecording: self.stopRecording,
                        cancelRecording: self.cancelRecording,
                        completion: self.completion
                    )
                ),
                environment: {
                    environment
                },
                forceUpdate: forceUpdate,
                containerSize: actualBackgroundFrame.size
            )
            if let componentView = self.componentHost.view {
                if componentView.superview == nil {
                    self.containerView.addSubview(componentView)
                }
            
                let componentFrame = CGRect(origin: .zero, size: componentSize)
                transition.setFrame(view: componentView, frame: componentFrame)
            }
            
            if let previewState = self.previewState {
                if previewState.composition !== self.resultPreviewView?.composition {
                    self.resultPreviewView?.removeFromSuperview()
                    self.resultPreviewView = nil
                }
                
                let resultPreviewView: ResultPreviewView
                if let current = self.resultPreviewView {
                    resultPreviewView = current
                } else {
                    resultPreviewView = ResultPreviewView(composition: previewState.composition)
                    resultPreviewView.onLoop = { [weak self] in
                        if let self, let controller = self.controller {
                            controller.updatePreviewState({ state in
                                if let state {
                                    return PreviewState(composition: state.composition, trimRange: state.trimRange, isMuted: true)
                                }
                                return nil
                            }, transition: .easeInOut(duration: 0.2))
                        }
                    }
                    self.previewContainerContentView.addSubview(resultPreviewView)
                    
                    self.resultPreviewView = resultPreviewView
                    resultPreviewView.layer.animateAlpha(from: 0.0, to: 1.0, duration: 0.2)
                    
                    resultPreviewView.addGestureRecognizer(UITapGestureRecognizer(target: self, action: #selector(self.resultTapped)))
                }
                resultPreviewView.frame = previewBounds
            } else if let resultPreviewView = self.resultPreviewView {
                self.resultPreviewView = nil
                resultPreviewView.removeFromSuperview()
            }
            
            if isFirstTime {
                self.animateIn()
            }
        }
    }

    fileprivate var node: Node {
        return self.displayNode as! Node
    }

    private let context: AccountContext
    private let updatedPresentationData: (initial: PresentationData, signal: Signal<PresentationData, NoError>)?
    private let inputPanelFrame: (CGRect, Bool)
    fileprivate var allowLiveUpload: Bool
    fileprivate var viewOnceAvailable: Bool
    
    fileprivate let completion: (EnqueueMessage?, Bool?, Int32?, Int32?) -> Void
    
    private var audioSessionDisposable: Disposable?
    
    private let hapticFeedback = HapticFeedback()
    
    private var validLayout: ContainerViewLayout?
    
    fileprivate var camera: CameraProtocol? {
        return self.node.camera
    }
    
    fileprivate var cameraState: CameraState {
        return self.node.cameraState
    }
    
    fileprivate func updateCameraState(_ f: (CameraState) -> CameraState, transition: ComponentTransition) {
        self.node.cameraState = f(self.node.cameraState)
        self.node.requestUpdateLayout(transition: transition)
        self.durationValue.set(self.cameraState.duration)
    }
    
    fileprivate func updatePreviewState(_ f: (PreviewState?) -> PreviewState?, transition: ComponentTransition) {
        self.node.previewState = f(self.node.previewState)
        self.node.requestUpdateLayout(transition: transition)
    }
    
    public final class RecordingStatus {
        public let micLevel: Signal<Float, NoError>
        public let duration: Signal<TimeInterval, NoError>
        
        public init(micLevel: Signal<Float, NoError>, duration: Signal<TimeInterval, NoError>) {
            self.micLevel = micLevel
            self.duration = duration
        }
    }
    
    private let micLevelValue = ValuePromise<Float>(0.0)
    private let durationValue = ValuePromise<TimeInterval>(0.0)
    public let recordingStatus: RecordingStatus

    public var onStop: () -> Void = {
    }
    
    public var onResume: () -> Void = {
    }
    
    public var backgroundView: UIVisualEffectView {
        return self.node.backgroundView
    }
    
    public struct RecordedVideoData {
        public let duration: Double
        public let frames: [UIImage]
        public let framesUpdateTimestamp: Double
        public let trimRange: Range<Double>?
    }
    
    private var currentResults: Signal<[VideoMessageCameraScreen.CaptureResult], NoError> {
        guard self.waitingForNextResult else {
            return .single(self.node.results)
        }
        // Capture the stop revision when stop was requested, not when this
        // signal is constructed/subscribed. Promise replays a completed stop
        // even if thumbnail work or a synchronous callback delayed the waiter.
        let expectedRevision = self.nagramiXExpectedCompletedRevision
        self.waitingForNextResult = false
        return self.node.nagramiXCompletedResults.get()
        |> filter { $0.revision >= expectedRevision }
        |> take(1)
        |> map { $0.results }
    }

    public func takenRecordedData() -> Signal<RecordedVideoData?, NoError> {
        let previewState = self.node.previewStatePromise.get()
        let count = 13
        
        let initialPlaceholder: Signal<UIImage?, NoError>
        if let firstResult = self.node.results.first {
            if case let .video(video) = firstResult {
                initialPlaceholder = .single(video.thumbnail)
            } else {
                initialPlaceholder = .single(nil)
            }
        } else {
            initialPlaceholder = self.camera?.transitionImage ?? .single(nil)
        }
        
        var approximateDuration: Double
        if let recordingStartTime = self.recordingStartTime {
            approximateDuration = CACurrentMediaTime() - recordingStartTime
        } else {
            approximateDuration = 1.0
        }
        
        let immediateResult: Signal<RecordedVideoData?, NoError> = initialPlaceholder
        |> take(1)
        |> mapToSignal { initialPlaceholder in
            return videoFrames(asset: nil, count: count, initialPlaceholder: initialPlaceholder)
            |> map { framesAndUpdateTimestamp in
                return RecordedVideoData(
                    duration: approximateDuration,
                    frames: framesAndUpdateTimestamp.0,
                    framesUpdateTimestamp: framesAndUpdateTimestamp.1,
                    trimRange: nil
                )
            }
        }
        
        return immediateResult
        |> mapToSignal { immediateResult in
            return .single(immediateResult)
            |> then(
                self.currentResults
                |> take(1)
                |> mapToSignal { results in
                    var totalDuration: Double = 0.0
                    for result in results {
                        if case let .video(video) = result {
                            totalDuration += video.duration
                        }
                    }
                    return nagramiXRecordingComposition(with: results)
                    |> mapToSignal { composition in
                        return combineLatest(
                            queue: Queue.mainQueue(),
                            videoFrames(asset: composition, count: count, initialTimestamp: immediateResult?.framesUpdateTimestamp),
                            previewState
                        )
                        |> map { framesAndUpdateTimestamp, previewState in
                            return RecordedVideoData(
                                duration: totalDuration,
                                frames: framesAndUpdateTimestamp.0,
                                framesUpdateTimestamp: framesAndUpdateTimestamp.1,
                                trimRange: previewState?.trimRange
                            )
                        }
                    }
                }
            )
        }
    }
    
    fileprivate weak var chatNode: ASDisplayNode?
    
    public init(
        context: AccountContext,
        updatedPresentationData: (initial: PresentationData, signal: Signal<PresentationData, NoError>)?,
        allowLiveUpload: Bool,
        viewOnceAvailable: Bool,
        inputPanelFrame: (CGRect, Bool),
        chatNode: ASDisplayNode?,
        completion: @escaping (EnqueueMessage?, Bool?, Int32?, Int32?) -> Void
    ) {
        self.context = context
        self.updatedPresentationData = updatedPresentationData
        self.allowLiveUpload = allowLiveUpload
        self.viewOnceAvailable = viewOnceAvailable
        self.inputPanelFrame = inputPanelFrame
        self.chatNode = chatNode
        self.completion = completion
        
        self.recordingStatus = RecordingStatus(micLevel: self.micLevelValue.get(), duration: self.durationValue.get())

        super.init(navigationBarPresentationData: nil)

        self.statusBar.statusBarStyle = .Ignore
        self.supportedOrientations = ViewControllerSupportedOrientations(regularSize: .all, compactSize: .portrait)
        
        self.navigationPresentation = .flatModal
        
        self.requestAudioSession()
    }

    required public init(coder: NSCoder) {
        preconditionFailure()
    }
    
    deinit {
        self.audioSessionDisposable?.dispose()
    }

    override public func loadDisplayNode() {
        self.displayNode = Node(controller: self)

        super.displayNodeDidLoad()
    }
        
    fileprivate var didSend = false
    fileprivate var lastActionTimestamp: Double?
    fileprivate var isSendingImmediately = false
    public func sendVideoRecording(silentPosting: Bool? = nil, scheduleTime: Int32? = nil, repeatPeriod: Int32? = nil, messageEffect: ChatSendMessageEffect? = nil) {
        guard !self.didSend else {
            return
        }
        
        if self.node.nagramiXCountdownPending && !self.node.nagramiXCameraSwitchPending {
            self.node.cancelRecording.invoke(Void())
            self.completion(nil, nil, nil, nil)
            return
        }
        var skipAction = false
        let currentTimestamp = CACurrentMediaTime()
        if let lastActionTimestamp = self.lastActionTimestamp, currentTimestamp - lastActionTimestamp < 0.5 {
            skipAction = true
        }
        
        if case .none = self.cameraState.recording, self.node.results.isEmpty {
            self.completion(nil, nil, nil, nil)
            return
        }
        
        if case .none = self.cameraState.recording {
        } else {
            if self.cameraState.duration > 0.5 {
                if skipAction {
                    return
                }
                self.isSendingImmediately = true
                self.waitingForNextResult = true
                self.node.stopRecording.invoke(Void())
            } else {
                self.completion(nil, nil, nil, nil)
                return
            }
        }
        
        guard !skipAction else {
            return
        }
        
        self.didSend = true
        self.node.nagramiXCompositionDisposable.set(nil)
        Logger.shared.log("NagramiX", "Round send requested")

        let _ = (self.currentResults
        |> take(1)
        |> deliverOnMainQueue).startStandalone(next: { [weak self] results in
            guard let self, let firstResult = results.first, case let .video(video) = firstResult else {
                return
            }

            var videoPaths: [String] = []
            var duration: Double = 0.0
            
            var hasAdjustments = results.count > 1
            for result in results {
                if case let .video(video) = result {
                    videoPaths.append(video.videoPath)
                    duration += video.duration
                }
            }
            
            if duration < 1.0 {
                self.completion(nil, nil, nil, nil)
                return
            }
            
            var startTime: Double = 0.0
            let finalDuration: Double
            if let trimRange = self.node.previewState?.trimRange {
                startTime = trimRange.lowerBound
                finalDuration = trimRange.upperBound - trimRange.lowerBound
                if finalDuration != duration {
                    hasAdjustments = true
                }
            } else {
                finalDuration = duration
            }
            
            let dimensions = video.dimensions
            
            let thumbnailImage: Signal<UIImage, NoError>
            if startTime > 0.0 {
                thumbnailImage = nagramiXRecordingComposition(with: results)
                |> mapToSignal { composition in
                    return Signal { subscriber in
                        let imageGenerator = AVAssetImageGenerator(asset: composition)
                        imageGenerator.maximumSize = dimensions.cgSize
                        imageGenerator.appliesPreferredTrackTransform = true

                        imageGenerator.generateCGImagesAsynchronously(forTimes: [NSValue(time: CMTime(seconds: startTime, preferredTimescale: composition.duration.timescale))], completionHandler: { _, image, _, _, _ in
                            if let image {
                                subscriber.putNext(UIImage(cgImage: image))
                            } else {
                                subscriber.putNext(video.thumbnail)
                            }
                            subscriber.putCompletion()
                        })

                        return ActionDisposable {
                            imageGenerator.cancelAllCGImageGeneration()
                        }
                    }
                }
            } else {
                thumbnailImage = .single(video.thumbnail)
            }
            
            let _ = (thumbnailImage
            |> deliverOnMainQueue).startStandalone(next: { [weak self] thumbnailImage in
                guard let self else {
                    return
                }
                let values = MediaEditorValues(
                    peerId: self.context.account.peerId,
                    originalDimensions: dimensions,
                    cropOffset: .zero,
                    cropRect: CGRect(origin: .zero, size: dimensions.cgSize),
                    cropScale: 1.0,
                    cropRotation: 0.0,
                    cropMirroring: false,
                    cropOrientation: nil,
                    cropPerspective: .zero,
                    gradientColors: nil,
                    videoTrimRange: self.node.previewState?.trimRange,
                    videoBounce: false,
                    videoIsMuted: false,
                    videoIsFullHd: false,
                    videoIsMirrored: false,
                    videoVolume: nil,
                    additionalVideoPath: nil,
                    additionalVideoIsDual: false,
                    additionalVideoMirroringChanges: [],
                    additionalVideoPosition: nil,
                    additionalVideoScale: nil,
                    additionalVideoRotation: nil,
                    additionalVideoPositionChanges: [],
                    additionalVideoTrimRange: nil,
                    additionalVideoOffset: nil,
                    additionalVideoVolume: nil,
                    collage: [],
                    nightTheme: false,
                    drawing: nil,
                    maskDrawing: nil,
                    entities: [],
                    toolValues: [:],
                    audioTrack: nil,
                    audioTrackTrimRange: nil,
                    audioTrackOffset: nil,
                    audioTrackVolume: nil,
                    audioTrackSamples: nil,
                    collageTrackSamples: nil,
                    coverImageTimestamp: nil,
                    coverDimensions: nil,
                    qualityPreset: .videoMessage,
                    nagramiXRoundTuning: self.node.nagramiXQuality.map { [$0.quality.rawValue, $0.frameRate.rawValue, $0.codec.rawValue, $0.bitRate] }
                )
                
                var resourceAdjustments: VideoMediaResourceAdjustments? = nil
                if let valuesData = try? JSONEncoder().encode(values) {
                    let data = EngineMemoryBuffer(data: valuesData)
                    let digest = EngineMemoryBuffer(data: data.md5Digest())
                    resourceAdjustments = VideoMediaResourceAdjustments(data: data, digest: digest, isStory: false)
                }
     
                let resource: TelegramMediaResource
                let liveUploadData: LegacyLiveUploadInterfaceResult?
                if let current = self.node.currentLiveUploadData {
                    liveUploadData = current
                } else {
                    liveUploadData = self.node.liveUploadInterface?.fileUpdated(true) as? LegacyLiveUploadInterfaceResult
                }
                let outputDimensions: PixelDimensions
                let storedFileId = storeUneditedVideoMessage(
                    path: video.videoPath,
                    hasAdjustments: hasAdjustments,
                    liveUploadId: liveUploadData?.id,
                    store: { id, data in
                        let resourceId = EngineMediaResource.Id(LocalFileMediaResource(fileId: id).id)
                        self.context.engine.resources.storeResourceData(id: resourceId, data: data, synchronous: true)
                        guard let path = self.context.engine.resources.completedResourcePath(id: resourceId),
                              let attributes = try? FileManager.default.attributesOfItem(atPath: path),
                              let size = attributes[.size] as? NSNumber else {
                            return false
                        }
                        return size.int64Value == Int64(data.count)
                    }
                )
                if let storedFileId {
                    resource = LocalFileMediaResource(fileId: storedFileId)
                    outputDimensions = video.dimensions
                } else {
                    resource = LocalFileVideoMediaResource(randomId: Int64.random(in: Int64.min ... Int64.max), paths: videoPaths, adjustments: resourceAdjustments)
                    let exportConfiguration = recommendedVideoExportConfiguration(values: values, duration: duration, frameRate: 30.0)
                    outputDimensions = PixelDimensions(
                        width: Int32(exportConfiguration.videoSettings[AVVideoWidthKey] as? Int ?? Int(video.dimensions.width)),
                        height: Int32(exportConfiguration.videoSettings[AVVideoHeightKey] as? Int ?? Int(video.dimensions.height))
                    )
                }
                
                var previewRepresentations: [TelegramMediaImageRepresentation] = []
                            
                let thumbnailResource = LocalFileMediaResource(fileId: Int64.random(in: Int64.min ... Int64.max))
                let thumbnailSize = video.dimensions.cgSize.aspectFitted(CGSize(width: 320.0, height: 320.0))
                if let thumbnailData = scaleImageToPixelSize(image: thumbnailImage, size: thumbnailSize)?.jpegData(compressionQuality: 0.4) {
                    self.context.engine.resources.storeResourceData(id: EngineMediaResource.Id(thumbnailResource.id), data: thumbnailData)
                    previewRepresentations.append(TelegramMediaImageRepresentation(dimensions: PixelDimensions(thumbnailSize), resource: thumbnailResource, progressiveSizes: [], immediateThumbnailData: nil, hasVideo: false, isPersonal: false))
                }
                
                let tempFile = EngineTempBox.shared.tempFile(fileName: "file")
                defer {
                    EngineTempBox.shared.dispose(tempFile)
                }
                if let data = compressImageToJPEG(thumbnailImage, quality: 0.7, tempFilePath: tempFile.path) {
                    context.engine.resources.storeCachedRepresentation(resource: EngineMediaResource(resource), representation: CachedVideoFirstFrameRepresentation(), data: data)
                }

                let media = TelegramMediaFile(fileId: EngineMedia.Id(namespace: Namespaces.Media.LocalFile, id: Int64.random(in: Int64.min ... Int64.max)), partialReference: nil, resource: resource, previewRepresentations: previewRepresentations, videoThumbnails: [], immediateThumbnailData: nil, mimeType: "video/mp4", size: nil, attributes: [.FileName(fileName: "video.mp4"), .Video(duration: finalDuration, size: outputDimensions, flags: [.instantRoundVideo], preloadSize: nil, coverTime: nil, videoCodec: self.node.nagramiXQuality?.codec.telegramIdentifier)], alternativeRepresentations: [])
                
                var attributes: [EngineMessage.Attribute] = []
                if self.cameraState.isViewOnceEnabled && scheduleTime == nil && repeatPeriod == nil {
                    attributes.append(AutoremoveTimeoutMessageAttribute(timeout: viewOnceTimeout, countdownBeginTime: nil))
                }
                if let messageEffect {
                    attributes.append(EffectMessageAttribute(id: messageEffect.id))
                }
        
                let sourceBytes = (try? FileManager.default.attributesOfItem(atPath: video.videoPath)[.size] as? NSNumber)?.int64Value ?? -1
                Logger.shared.log("NagramiX", "Round enqueue: round=true; seconds=\(finalDuration); sourceBytes=\(sourceBytes); codec=\(self.node.nagramiXQuality?.codec.telegramIdentifier ?? "stock"); segments=\(videoPaths.count)")
                self.completion(.message(
                    text: "",
                    attributes: attributes,
                    inlineStickers: [:],
                    mediaReference: .standalone(media: media),
                    threadId: nil,
                    replyToMessageId: nil,
                    replyToStoryId: nil,
                    localGroupingKey: nil,
                    correlationId: nil,
                    bubbleUpEmojiOrStickersets: []
                ), silentPosting, scheduleTime, repeatPeriod)
            })
        })
    }
    
    private var nagramiXExpectedCompletedRevision = 0
    private var waitingForNextResult = false {
        didSet {
            if self.waitingForNextResult && !oldValue {
                self.nagramiXExpectedCompletedRevision = self.node.nagramiXCompletedRevision + 1
            }
        }
    }
    public func stopVideoRecording() -> Bool {
        guard !self.didSend else {
            return false
        }
        
        self.node.dismissAllTooltips()
        
        if self.node.nagramiXCountdownPending && !self.node.nagramiXCameraSwitchPending {
            self.discardVideo()
            self.completion(nil, nil, nil, nil)
            return false
        }
        self.waitingForNextResult = true
        self.node.transitioningToPreview = true
        self.node.requestUpdateLayout(transition: .spring(duration: 0.4))
        
        self.node.stopRecording.invoke(Void())
        
        return true
    }

    fileprivate var recordingStartTime: Double?
    fileprivate var scheduledLock = false
    public func lockVideoRecording() {
        guard !self.didSend else {
            return
        }
        
        if case .none = self.cameraState.recording {
            self.scheduledLock = true
            self.node.requestUpdateLayout(transition: .spring(duration: 0.4))
        } else {
            self.updateCameraState({ $0.updatedRecording(.handsFree) }, transition: .spring(duration: 0.4))
        }
        
        self.node.maybePresentTooltips()
    }
    
    public func discardVideo() {
        self.node.cancelRecording.invoke(Void())
        
        self.requestDismiss(animated: true)
    }
    
    public func extractVideoSnapshot() -> UIView? {
        if let snapshotView = self.node.previewContainerView.snapshotView(afterScreenUpdates: false) {
            snapshotView.frame = self.node.previewContainerView.convert(self.node.previewContainerView.bounds, to: nil)
            return snapshotView
        }
        return nil
    }

    public func hideVideoSnapshot() {
        self.node.previewContainerView.isHidden = true
    }
    
    public func updateTrimRange(start: Double, end: Double, updatedEnd: Bool, apply: Bool) {
        self.node.updateTrimRange(start: start, end: end, updatedEnd: updatedEnd, apply: apply)
    }
    
    private func requestAudioSession() {
        let audioSessionType: ManagedAudioSessionType
        if self.context.sharedContext.currentMediaInputSettings.with({ $0 }).pauseMusicOnRecording { 
            audioSessionType = .record(speaker: false, video: false, withOthers: false)
        } else {
            audioSessionType = .record(speaker: false, video: false, withOthers: true)
        }
      
        self.audioSessionDisposable = self.context.sharedContext.mediaManager.audioSession.push(audioSessionType: audioSessionType, activate: { [weak self] _ in
            if let self {
                let setupCamera = { [weak self] in
                    guard let self, !self.isDismissed else { return }
                    self.node.setupCamera()
                }
                if case .record(_, _, true) = audioSessionType {
                    Queue.mainQueue().async(setupCamera)
                } else {
                    Queue.mainQueue().after(0.05, setupCamera)
                }
            }
        }, deactivate: { _ in
            return .single(Void())
        })
    }
            
    fileprivate var isDismissed = false
    fileprivate func requestDismiss(animated: Bool) {
        guard !self.isDismissed else {
            return
        }
        
        self.node.dismissAllTooltips()
        
        self.isDismissed = true
        self.node.cancelRecording.invoke(Void())
        self.node.nagramiXCompositionDisposable.dispose()
        self.node.nagramiXPreviewReadyDisposables.dispose()
        self.node.camera?.stopCapture(invalidate: true)
        self.audioSessionDisposable?.dispose()
        self.audioSessionDisposable = nil
        if animated {
            self.node.animateOut(completion: {
                self.dismiss(animated: false)
            })
        } else {
            self.dismiss(animated: false)
        }
    }
        
    override public func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        self.validLayout = layout
        
        super.containerLayoutUpdated(layout, transition: transition)

        if !self.isDismissed {
            (self.displayNode as! Node).containerLayoutUpdated(layout: layout, transition: ComponentTransition(transition))
        }
    }
    
    public func makeSendMessageContextPreview() -> ChatSendMessageContextScreenMediaPreview? {
        return VideoMessageSendMessageContextPreview(node: self.node)
    }
}

private let nagramiXRecordingCompositionQueue = Queue(name: "NagramiX.RoundVideoComposition")

private func nagramiXRecordingComposition(with results: [VideoMessageCameraScreen.CaptureResult]) -> Signal<AVComposition, NoError> {
    return Signal { subscriber in
        // AVAsset.duration/track discovery and composition insertion can block
        // on the first file after process launch. Never do that work on main.
        let composition = nagramiXMakeRecordingComposition(with: results)
        subscriber.putNext(composition)
        subscriber.putCompletion()
        return EmptyDisposable
    }
    |> runOn(nagramiXRecordingCompositionQueue)
    |> deliverOnMainQueue
}

private func nagramiXMakeRecordingComposition(with results: [VideoMessageCameraScreen.CaptureResult]) -> AVComposition {
    let composition = AVMutableComposition()
    var currentTime = CMTime.zero
    
    for result in results {
        guard case let .video(video) = result else {
            continue
        }
        let asset = AVAsset(url: URL(fileURLWithPath: video.videoPath))
        let duration = asset.duration
        do {
            try composition.insertTimeRange(
                CMTimeRangeMake(start: .zero, duration: duration),
                of: asset,
                at: currentTime
            )
            currentTime = CMTimeAdd(currentTime, duration)
        } catch {
        }
    }
    return composition
}

private class BlurView: UIVisualEffectView {
    private func setup() {
        for subview in self.subviews {
            if subview.description.contains("VisualEffectSubview") {
                subview.isHidden = true
            }
        }
        
        if let sublayer = self.layer.sublayers?[0], let filters = sublayer.filters {
            sublayer.backgroundColor = nil
            sublayer.isOpaque = false
            let allowedKeys: [String] = [
                "gaussianBlur"
            ]
            sublayer.filters = filters.filter { filter in
                guard let filter = filter as? NSObject else {
                    return true
                }
                let filterName = String(describing: filter)
                if !allowedKeys.contains(filterName) {
                    return false
                }
                return true
            }
        }
    }
    
    override var effect: UIVisualEffect? {
        get {
            return super.effect
        }
        set {
            super.effect = newValue
            self.setup()
        }
    }
    
    override func didAddSubview(_ subview: UIView) {
        super.didAddSubview(subview)
        self.setup()
    }
}

private final class VideoMessageSendMessageContextPreview: UIView, ChatSendMessageContextScreenMediaPreview {
    var isReady: Signal<Bool, NoError> {
        return .single(true)
    }
    
    var view: UIView {
        return self
    }
    
    var globalClippingRect: CGRect? {
        return nil
    }
    
    var layoutType: ChatSendMessageContextScreenMediaPreviewLayoutType {
        return .videoMessage
    }
    
    private weak var previewContainerContentParentView: UIView?
    private let previewContainerContentView: UIView
    
    init(node: VideoMessageCameraScreen.Node) {
        self.previewContainerContentParentView = node.previewContainerView
        self.previewContainerContentView = node.previewContainerContentView
        
        super.init(frame: CGRect())
    }
    
    required init(coder: NSCoder) {
        preconditionFailure()
    }
    
    func animateIn(transition: ComponentTransition) {
        self.addSubview(self.previewContainerContentView)
        
        guard let previewContainerContentParentView = self.previewContainerContentParentView else {
            return
        }
        
        let fromFrame = previewContainerContentParentView.convert(CGRect(origin: CGPoint(), size: self.previewContainerContentView.bounds.size), to: self)
        let toFrame = self.previewContainerContentView.frame
        
        transition.animatePosition(view: self.previewContainerContentView, from: CGPoint(x: fromFrame.midX - toFrame.midX, y: fromFrame.midY - toFrame.midY), to: CGPoint(), additive: true)
    }
    
    func animateOut(transition: ComponentTransition) {
        guard let previewContainerContentParentView = self.previewContainerContentParentView else {
            return
        }
        
        let toFrame = previewContainerContentParentView.convert(CGRect(origin: CGPoint(), size: self.previewContainerContentView.bounds.size), to: self)
        
        let previewContainerContentView = self.previewContainerContentView
        transition.setPosition(view: self.previewContainerContentView, position: toFrame.center, completion: { [weak previewContainerContentParentView, weak previewContainerContentView] _ in
            guard let previewContainerContentParentView, let previewContainerContentView else {
                return
            }
            
            previewContainerContentView.frame = CGRect(origin: CGPoint(), size: previewContainerContentView.bounds.size)
            previewContainerContentParentView.addSubview(previewContainerContentView)
        })
    }
    
    func animateOutOnSend(transition: ComponentTransition) {
        guard let previewContainerContentParentView = self.previewContainerContentParentView else {
            return
        }
        
        if let snapshotView = self.previewContainerContentView.snapshotView(afterScreenUpdates: false) {
            self.addSubview(snapshotView)
            transition.setAlpha(view: snapshotView, alpha: 0.0)
        }
        
        self.previewContainerContentView.frame = CGRect(origin: CGPoint(), size: self.previewContainerContentView.bounds.size)
        previewContainerContentParentView.addSubview(self.previewContainerContentView)
    }
    
    func update(containerSize: CGSize, transition: ComponentTransition) -> CGSize {
        return self.previewContainerContentView.bounds.size
    }
}
