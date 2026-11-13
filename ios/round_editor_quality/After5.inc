import Foundation
import NagramiXCore
import NagramiXMediaSettings
import MediaCropComponent
import UIKit
import AVFoundation
import Display
import SwiftSignalKit
import TelegramCore
import ComponentFlow
import TelegramPresentationData
import MediaEditor
import MediaEditorScreen
import MediaScrubberComponent
import ChatMediaSend

// Capture export settings once for this editor item; deferred export uses its JSON snapshot.
func chatMediaEditorRoundVideoValues(_ values: MediaEditorValues, settings: NagramiXRoundVideoSettings) -> MediaEditorValues {
    guard values.qualityPreset == .videoMessage, values.nagramiXRoundTuning == nil, settings.enabled else { return values }
    return values.withUpdatedNagramiXRoundTuning([settings.quality.rawValue, settings.frameRate.rawValue, settings.codec.rawValue, settings.bitRate])
}

let chatMediaEditorPreferredVideoPresetKey = "TG_preferredVideoPreset_v0"

public func chatMediaEditorVideoQualityPreset(storedLegacyPreset: Int?) -> MediaQualityPreset {
    guard let storedLegacyPreset else {
        return .compressedMedium
    }
    return MediaQualityPreset(legacyPresetRawValue: UInt32(clamping: storedLegacyPreset))
}

func chatMediaEditorPreferredVideoQualityPreset() -> MediaQualityPreset {
    let storedValue = (UserDefaults.standard.object(forKey: chatMediaEditorPreferredVideoPresetKey) as? NSNumber)?.intValue
    return chatMediaEditorVideoQualityPreset(storedLegacyPreset: storedValue)
}

public func chatMediaEditorCanResumePlayback(isSending: Bool, isInvalidated: Bool, isDismissing: Bool) -> Bool {
    return !isSending && !isInvalidated && !isDismissing
}

private let chatMediaEditorScrubberMinDuration: Double = 1.0
private let chatMediaEditorScrubberPositionTrackingSource = "scrubberPosition"
private let chatMediaEditorScrubberTrimTrackingSource = "scrubberTrim"

extension ChatMediaEditorScreen.Node {
    var canResumePlayback: Bool {
        return chatMediaEditorCanResumePlayback(isSending: self.isSending, isInvalidated: self.isInvalidated, isDismissing: self.controller?.isDismissing ?? true)
    }

    func setupVideo() {
        self.previewTapRecognizer.addTarget(self, action: #selector(self.previewTapped))
        self.previewContainerView.addGestureRecognizer(self.previewTapRecognizer)
        self.nagramiXRoundGestureDelegate.node = self
        self.nagramiXRoundPan.maximumNumberOfTouches = 1
        self.nagramiXRoundPan.addTarget(self, action: #selector(self.nagramiXRoundVideoPanned(_:)))
        self.nagramiXRoundPinch.addTarget(self, action: #selector(self.nagramiXRoundVideoPinched(_:)))
        self.nagramiXRoundPan.delegate = self.nagramiXRoundGestureDelegate
        self.nagramiXRoundPinch.delegate = self.nagramiXRoundGestureDelegate
        self.previewContainerView.addGestureRecognizer(self.nagramiXRoundPan)
        self.previewContainerView.addGestureRecognizer(self.nagramiXRoundPinch)
        self.pagerView.scrollView.panGestureRecognizer.require(toFail: self.nagramiXRoundPan)
        self.pagerView.swipeDownRecognizer.require(toFail: self.nagramiXRoundPan)
        self.previewTapRecognizer.require(toFail: self.nagramiXRoundPan)
        self.previewTapRecognizer.require(toFail: self.nagramiXRoundPinch)
        for label in [self.nagramiXRoundTitle, self.nagramiXRoundHint, self.nagramiXRoundDuration] {
            label.textAlignment = .center
            label.textColor = .white
            label.font = Font.regular(14.0)
            label.isUserInteractionEnabled = false
            self.view.addSubview(label)
        }
        self.nagramiXRoundTitle.font = Font.semibold(17.0)
        self.nagramiXRoundHint.textColor = UIColor(white: 1.0, alpha: 0.65)
    }

    private func startPlayerStateUpdates(framesCount: Int) {
        let disposable = MetaDisposable()
        self.playerStateDisposable = disposable
        disposable.set((self.mediaEditor.playerState(framesCount: framesCount)
        |> deliverOnMainQueue).startStrict(next: { [weak self] playerState in
            guard let self else {
                return
            }
            if self.playerState != playerState {
                self.playerState = playerState
                if playerState?.isPlaying == true {
                    self.hasStartedPlayback = true
                }
                if let layout = self.validLayout {
                    self.updateScrubber(layout: layout, safeInsets: self.editorSafeInsets(layout: layout), transition: .immediate)
                    self.updateCoverScrubber(layout: layout, safeInsets: self.editorSafeInsets(layout: layout), transition: .immediate)
                    self.updateMuteButton(layout: layout, safeInsets: self.editorSafeInsets(layout: layout), transition: .animated(duration: 0.2, curve: .easeInOut))
                }
                self.updatePlayButton(transition: .animated(duration: 0.2, curve: .easeInOut))
            }
        }))
    }

    @objc private func previewTapped() {
        guard self.subject.isVideo, self.activeTool == nil, !self.isSending, !self.isInvalidated else {
            return
        }
        self.mediaEditor.togglePlayback()
    }

    func updateScrubber(layout: ContainerViewLayout, safeInsets: UIEdgeInsets, transition: ComponentTransition) {
        guard self.subject.isVideo else {
            return
        }
        let toolbarMinY = chatMediaEditorBottomPanelFrame(size: layout.size, safeInsets: safeInsets, toolbarHeight: chatMediaEditorToolbarHeight).minY
        let toolbarSide = self.toolbarSide(layout: layout)
        let headerFrame = chatMediaEditorVideoHeaderFrame(size: layout.size, toolbarMinY: toolbarMinY, captionBaseHeight: self.captionPanelView?.baseHeight() ?? 0.0, safeInsets: safeInsets, toolbarSide: toolbarSide, reservedCorners: layout.reservedCorners)
        let availableWidth = chatMediaEditorScrubberFrame(size: layout.size, safeInsets: safeInsets, headerFrame: headerFrame, scrubberHeight: 0.0, toolbarSide: toolbarSide).width
        let framesCount = chatMediaEditorScrubberFramesCount(trackWidth: availableWidth, mediaSize: self.subject.dimensions.cgSize)
        if !self.isInvalidated && (self.playerStateDisposable == nil || self.playerStateFramesCount != framesCount) {
            self.playerStateDisposable?.dispose()
            self.playerStateFramesCount = framesCount
            self.startPlayerStateUpdates(framesCount: framesCount)
        }
        guard let playerState = self.playerState, let mainTrack = playerState.tracks.first(where: { $0.id == 0 }) else {
            return
        }
        let mediaEditor = self.mediaEditor
        let scrubberSize = self.scrubber.update(
            transition: transition,
            component: AnyComponent(MediaScrubberComponent(
                context: self.context,
                style: .editor,
                theme: defaultDarkColorPresentationTheme,
                generationTimestamp: playerState.generationTimestamp,
                position: playerState.position,
                minDuration: self.nagramiXIsRoundVideo ? min(chatMediaEditorScrubberMinDuration, mainTrack.duration) : chatMediaEditorScrubberMinDuration,
                maxDuration: self.nagramiXIsRoundVideo ? min(60.0, mainTrack.duration) : max(chatMediaEditorScrubberMinDuration, mainTrack.duration),
                isPlaying: playerState.isPlaying,
                tracks: [MediaScrubberComponent.Track(mainTrack)],
                isCollage: false,
                allowsTrimming: !self.isFilePreview,
                positionUpdated: { [weak self, weak mediaEditor] position, apply in
                    self?.setScrubberTracking(!apply, source: chatMediaEditorScrubberPositionTrackingSource)
                    mediaEditor?.seek(position, andPlay: apply)
                },
                trackTrimUpdated: { [weak self, weak mediaEditor] _, start, end, updatedEnd, apply in
                    self?.setScrubberTracking(!apply, source: chatMediaEditorScrubberTrimTrackingSource)
                    guard let mediaEditor else {
                        return
                    }
                    guard start.isFinite, end.isFinite, start >= 0.0, end > start else { return }
                    let range: Range<Double>
                    if self?.nagramiXIsRoundVideo == true {
                        guard let bounded = nagramiXRoundVideoTrimRange(duration: self?.subject.duration ?? 0.0, range: start ..< end) else { return }
                        range = bounded
                    } else { range = start ..< end }
                    mediaEditor.setVideoTrimRange(range, apply: apply)
                    if let self, let layout = self.validLayout { self.nagramiXUpdateRoundVideoPresentation(layout: layout) }
                    if apply {
                        mediaEditor.seek(range.lowerBound, completion: { [weak self, weak mediaEditor] in
                            guard let self else {
                                return
                            }
                            guard self.canResumePlayback else {
                                self.updatePlayButton(transition: .animated(duration: 0.2, curve: .easeInOut))
                                return
                            }
                            mediaEditor?.play()
                        })
                    } else {
                        mediaEditor.seek(updatedEnd ? range.upperBound : range.lowerBound, andPlay: false)
                    }
                },
                trackOffsetUpdated: { _, _, _ in
                },
                trackLongPressed: { _, _ in
                }
            )),
            environment: {},
            containerSize: CGSize(width: availableWidth, height: layout.size.height)
        )
        guard let scrubberView = self.scrubber.view else {
            return
        }
        let scrubberFrame = chatMediaEditorScrubberFrame(size: layout.size, safeInsets: safeInsets, headerFrame: headerFrame, scrubberHeight: scrubberSize.height, toolbarSide: toolbarSide)
        let isToolActive = self.activeTool != nil || self.isInterfaceHiddenBySwipe || self.isEditingCaption || (layout.inputHeight ?? 0.0) > 0.0
        if scrubberView.superview == nil {
            self.view.insertSubview(scrubberView, aboveSubview: self.pagerView)
            scrubberView.frame = scrubberFrame
        } else {
            transition.setFrame(view: scrubberView, frame: scrubberFrame)
        }
        transition.setAlpha(view: scrubberView, alpha: isToolActive ? 0.0 : 1.0)
        scrubberView.isUserInteractionEnabled = !isToolActive
        self.nagramiXUpdateRoundVideoPresentation(layout: layout)
    }

    var isScrubberTracking: Bool {
        let sources = self.interactionTracking.sources
        return sources.contains(chatMediaEditorScrubberPositionTrackingSource) || sources.contains(chatMediaEditorScrubberTrimTrackingSource)
    }

    private func setScrubberTracking(_ tracking: Bool, source: String) {
        self.setInteractionTracking(tracking, source: source)
        if tracking {
            self.updatePlayButton(transition: .animated(duration: 0.2, curve: .easeInOut))
        }
    }

    func releaseScrubberTracking() {
        self.setInteractionTracking(false, source: chatMediaEditorScrubberPositionTrackingSource)
        self.setInteractionTracking(false, source: chatMediaEditorScrubberTrimTrackingSource)
        self.updatePlayButton(transition: .immediate)
    }

    func sendVideo(path: String, duration: Double, values: MediaEditorValues, caption: NSAttributedString, stickers: [TelegramMediaFile], completion: @escaping (ChatMediaEditorResult) -> Void) {
        self.mediaEditor.stop()

        let firstFrameTime = CMTime(seconds: values.videoTrimRange?.lowerBound ?? 0.0, preferredTimescale: CMTimeScale(60))
        let generator = AVAssetImageGenerator(asset: AVURLAsset(url: URL(fileURLWithPath: path)))
        generator.appliesPreferredTrackTransform = true
        generator.requestedTimeToleranceBefore = .zero
        generator.requestedTimeToleranceAfter = .zero
        generator.generateCGImagesAsynchronously(forTimes: [NSValue(time: firstFrameTime)], completionHandler: { [weak self] _, cgImage, _, _, _ in
            let _ = generator
            let firstFrame = cgImage.flatMap { UIImage(cgImage: $0) }
            Queue.mainQueue().async {
                guard let self, let controller = self.controller, !controller.isDismissing, !self.isInvalidated else {
                    return
                }
                if let firstFrame {
                    self.mediaEditor.replaceSource(firstFrame, additionalImage: nil, time: firstFrameTime, mirror: false)
                }
                let input: MediaEditorCompositionInput = self.mediaEditor.resultTexture().map { .editorResult($0) } ?? .image(firstFrame ?? UIImage())
                makeChatEditorImageComposition(accountContext: self.context, input: input, values: values, time: firstFrameTime, maxOutputSide: chatMediaEditorImageMaxSide(forceHd: chatMediaEditorSendsForceHd), completion: { [weak self] thumbnail in
                    guard let self, let controller = self.controller, !controller.isDismissing, !self.isInvalidated else {
                        return
                    }
                    let result = ChatMediaEditorResult(
                        media: .video(path: path, values: values, duration: duration),
                        thumbnail: thumbnail,
                        caption: caption,
                        stickers: stickers,
                        isAnimation: self.pageModel.currentItem.isAnimation
                    )
                    completion(result)
                })
            }
        })
    }
}

// Round mode reuses MediaEditorValues.videoMessage, the native crop geometry,
// the existing trim scrubber, and the standard chat-media sender.
final class NagramiXRoundVideoGestureDelegate: NSObject, UIGestureRecognizerDelegate {
    weak var node: ChatMediaEditorScreen.Node?

    func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        return self.node?.nagramiXCanEditRoundVideo == true
    }

    func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldRecognizeSimultaneouslyWith otherGestureRecognizer: UIGestureRecognizer) -> Bool {
        guard let node else { return false }
        return (gestureRecognizer === node.nagramiXRoundPan && otherGestureRecognizer === node.nagramiXRoundPinch)
            || (gestureRecognizer === node.nagramiXRoundPinch && otherGestureRecognizer === node.nagramiXRoundPan)
    }
}

func nagramiXRoundVideoTime(_ seconds: Double) -> String {
    let total = Int64(min(Double(Int32.max), max(0.0, seconds.isFinite ? seconds : 0.0)))
    return String(format: "%02lld:%02lld", total / 60, total % 60)
}

/// The native cover-fit accounts for orientation, rotation, mirroring and
/// perspective. Clamp placement before deriving the crop, so no black border
/// can enter the square encoded file or the circular preview.
func nagramiXRoundVideoCrop(state: MediaCropState, frame: CGRect, translation: CGPoint, scale: CGFloat) -> MediaCropState {
    guard frame.width.isFinite, frame.height.isFinite, frame.minX.isFinite, frame.minY.isFinite,
          frame.width > 0.0, frame.height > 0.0, translation.x.isFinite, translation.y.isFinite,
          scale.isFinite, scale > 0.0 else { return state }
    var placement = mediaCropContentPlacement(cropRect: state.cropRect, state: state, frame: frame)
    placement.center.x += translation.x
    placement.center.y += translation.y
    let boundedScale = max(0.1, min(10.0, scale))
    placement.scale = min(mediaCropMinimumZoomScale(frameSize: frame.size, state: state) * 32.0, placement.scale * boundedScale)
    placement = mediaCropCoverFit(placement, frame: frame, state: state, allowScale: true)
    var result = state
    result.cropRect = mediaCropRect(frame: frame, placement: placement, state: state)
    result.lockedAspectRatio = 1.0
    return result
}

extension ChatMediaEditorScreen.Node {
    var nagramiXShowsRoundVideoTool: Bool {
        return self.subject.isVideo && !self.isFilePreview && !self.pageModel.currentItem.isAnimation
            && (NagramiXTabSettings.roundVideoEditorEnabled || self.nagramiXIsRoundVideo)
    }

    var nagramiXIsRoundVideo: Bool {
        return self.subject.isVideo && self.mediaEditor.values.qualityPreset == .videoMessage
    }

    var nagramiXCanEditRoundVideo: Bool {
        return self.nagramiXIsRoundVideo && self.activeTool == nil && !self.isSending
            && !self.isInvalidated && !self.isEditingCaption && !self.isInterfaceHiddenBySwipe
    }

    func nagramiXToggleRoundVideo() {
        guard self.subject.isVideo, !self.pageModel.currentItem.isAnimation, !self.isFilePreview,
              self.activeTool == nil, !self.isSending, !self.isInvalidated,
              self.nagramiXIsRoundVideo || NagramiXTabSettings.roundVideoEditorEnabled else { return }
        let current = self.captureCurrentValues()
        guard let range = nagramiXRoundVideoTrimRange(duration: self.subject.duration, range: current.videoTrimRange) else { return }
        let id = self.pageModel.currentItem.uniqueId
        let wasPlaying = self.mediaEditor.isPlaying
        self.toolStartValues = current
        self.resetCurrentPageZoom()
        self.mediaEditor.stop()
        if self.nagramiXIsRoundVideo {
            let entry = self.pageModel.store.entry(for: id)
            let before = entry?.nagramiXBeforeRoundVideo
            let originalQuality: MediaQualityPreset? = before != nil ? before?.qualityPreset : chatMediaEditorPreferredVideoQualityPreset()
            var restored = current.withUpdatedQualityPreset(originalQuality).withUpdatedNagramiXRoundTuning(before?.nagramiXRoundTuning)
            if let before {
                restored = restored.withUpdatedCrop(rect: before.cropRect, rotation: before.cropRotation, orientation: before.cropOrientation, mirroring: before.cropMirroring, perspective: before.cropPerspective)
                    .withUpdatedVideoTrimRange(before.videoTrimRange)
            }
            let restoredRange = restored.videoTrimRange ?? (0.0 ..< self.subject.duration)
            self.mediaEditor.values = restored
            self.mediaEditor.setVideoTrimRange(restoredRange, apply: true)
            self.mediaEditor.values = restored
            self.cropLockedAspectRatio = entry?.nagramiXBeforeRoundAspectRatio
            self.pageModel.store.update(id) { entry in
                entry.nagramiXBeforeRoundVideo = nil
                entry.nagramiXBeforeRoundAspectRatio = nil
            }
            self.mediaEditor.seek(restoredRange.lowerBound, andPlay: wasPlaying)
        } else {
            let oldAspect = self.cropLockedAspectRatio
            self.pageModel.store.update(id) { entry in
                entry.nagramiXBeforeRoundVideo = current
                entry.nagramiXBeforeRoundAspectRatio = oldAspect
            }
            let state = mediaCropApplyingLockedRatio(1.0, to: chatMediaEditorCropState(values: current))
            self.mediaEditor.values = chatMediaEditorRoundVideoValues(
                chatMediaEditorValues(current, applying: state).withUpdatedQualityPreset(.videoMessage).withUpdatedNagramiXRoundTuning(nil),
                settings: .current
            )
            self.cropLockedAspectRatio = 1.0
            self.mediaEditor.setVideoTrimRange(range, apply: true)
            self.mediaEditor.seek(range.lowerBound, andPlay: wasPlaying)
        }
        self.selectionEditCommitted()
        self.saveCurrentItemEdits()
        self.requestLayout(transition: .animated(duration: 0.2, curve: .easeInOut))
    }

    func nagramiXUpdateRoundVideoPresentation(layout: ContainerViewLayout) {
        let round = self.nagramiXIsRoundVideo
        let editing = self.nagramiXCanEditRoundVideo
        self.nagramiXRoundPan.isEnabled = editing
        self.nagramiXRoundPinch.isEnabled = editing
        self.previewContainerView.layer.cornerCurve = .circular
        self.previewContainerView.layer.cornerRadius = round && !self.isCropping ? min(self.previewContainerView.bounds.width, self.previewContainerView.bounds.height) / 2.0 : 0.0
        for label in [self.nagramiXRoundTitle, self.nagramiXRoundHint, self.nagramiXRoundDuration] { label.isHidden = !editing }
        guard editing else {
            self.previewContainerView.accessibilityHint = nil
            return
        }
        let strings = self.context.sharedContext.currentPresentationData.with { $0 }.strings
        let safe = self.editorSafeInsets(layout: layout)
        let preview = self.previewContainerView.frame
        let x = safe.left + 16.0
        let width = max(0.0, layout.size.width - x - safe.right - 16.0)
        self.nagramiXRoundTitle.text = strings.nagramiXRoundVideoTitle
        self.nagramiXRoundTitle.numberOfLines = 0
        let titleHeight = ceil(self.nagramiXRoundTitle.sizeThatFits(CGSize(width: width, height: CGFloat.greatestFiniteMagnitude)).height)
        self.nagramiXRoundTitle.frame = CGRect(x: x, y: preview.minY - titleHeight - 10.0, width: width, height: titleHeight)
        self.nagramiXRoundTitle.isHidden = self.nagramiXRoundTitle.frame.minY < safe.top + 34.0
        self.nagramiXRoundHint.text = strings.nagramiXRoundVideoCropHint
        self.previewContainerView.accessibilityHint = strings.nagramiXRoundVideoCropHint
        self.nagramiXRoundHint.numberOfLines = 0
        let hintHeight = ceil(self.nagramiXRoundHint.sizeThatFits(CGSize(width: width, height: CGFloat.greatestFiniteMagnitude)).height)
        self.nagramiXRoundHint.frame = CGRect(x: x, y: preview.maxY + 8.0, width: width, height: hintHeight)
        let scrubberTop = self.scrubber.view?.frame.minY ?? layout.size.height
        self.nagramiXRoundHint.isHidden = self.nagramiXRoundHint.frame.maxY > scrubberTop - 30.0
        if let range = self.mediaEditor.values.videoTrimRange, let scrubber = self.scrubber.view {
            let duration = strings.MessageTimer_ShortSeconds(Int32(min(60.0, ceil(range.upperBound - range.lowerBound))))
            self.nagramiXRoundDuration.text = "\(nagramiXRoundVideoTime(range.lowerBound)) — \(nagramiXRoundVideoTime(range.upperBound)) · \(duration)"
            self.nagramiXRoundDuration.frame = CGRect(x: x, y: scrubber.frame.minY - 28.0, width: width, height: 24.0)
            self.nagramiXRoundDuration.isHidden = scrubber.frame.minY - 28.0 < preview.maxY + 2.0
        } else { self.nagramiXRoundDuration.isHidden = true }
    }

    @objc func nagramiXRoundVideoPanned(_ gesture: UIPanGestureRecognizer) {
        let translation = gesture.translation(in: self.previewContainerView)
        gesture.setTranslation(.zero, in: self.previewContainerView)
        self.nagramiXApplyRoundGesture(gesture, translation: translation, scale: 1.0)
    }

    @objc func nagramiXRoundVideoPinched(_ gesture: UIPinchGestureRecognizer) {
        let scale = gesture.scale
        gesture.scale = 1.0
        self.nagramiXApplyRoundGesture(gesture, translation: .zero, scale: scale)
    }

    func nagramiXApplyRoundGesture(_ gesture: UIGestureRecognizer, translation: CGPoint, scale: CGFloat) {
        let key = ObjectIdentifier(gesture)
        switch gesture.state {
        case .began, .changed:
            guard self.nagramiXCanEditRoundVideo else { return }
            if self.nagramiXRoundGestures.isEmpty {
                self.nagramiXRoundGestureValues = self.mediaEditor.values
                self.nagramiXRoundGestureItemId = self.pageModel.currentItem.uniqueId
                self.nagramiXRoundGestureCancelled = false
                self.setInteractionTracking(true, source: "nagramixRoundCrop")
            }
            self.nagramiXRoundGestures.insert(key)
            guard self.nagramiXRoundGestureItemId == self.pageModel.currentItem.uniqueId else { return }
            let state = nagramiXRoundVideoCrop(state: self.committedCropState, frame: self.previewContainerView.bounds, translation: translation, scale: scale)
            let values = chatMediaEditorValues(self.mediaEditor.values, applying: state)
            self.mediaEditor.setCrop(rect: values.cropRect, rotation: values.cropRotation, orientation: values.cropOrientation, mirroring: values.cropMirroring, perspective: values.cropPerspective)
            self.requestLayout(transition: .immediate)
        case .ended, .cancelled, .failed:
            if gesture.state != .ended { self.nagramiXRoundGestureCancelled = true }
            self.nagramiXRoundGestures.remove(key)
            guard self.nagramiXRoundGestures.isEmpty else { return }
            if self.nagramiXRoundGestureItemId == self.pageModel.currentItem.uniqueId, !self.isSending, !self.isInvalidated {
                if self.nagramiXRoundGestureCancelled, let values = self.nagramiXRoundGestureValues { self.mediaEditor.values = values }
                self.toolStartValues = self.nagramiXRoundGestureValues
                self.selectionEditCommitted()
                self.saveCurrentItemEdits()
            }
            self.nagramiXRoundGestureValues = nil
            self.nagramiXRoundGestureItemId = nil
            self.setInteractionTracking(false, source: "nagramixRoundCrop")
            self.requestLayout(transition: .immediate)
        default:
            break
        }
    }
}
