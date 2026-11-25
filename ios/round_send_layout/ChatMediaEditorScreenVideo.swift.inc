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

// Gallery conversion has an attachment-local profile, independent of camera defaults.
func chatMediaEditorRoundVideoTuning(_ tuning: [Int]?) -> [Int] {
    let standard = [480, 30, 0, 1_000_000]
    guard let tuning, (tuning.count == 3 || tuning.count == 4), [480, 512, 640].contains(tuning[0]),
          [30, 60].contains(tuning[1]), [0, 1].contains(tuning[2]) else { return standard }
    let rate = tuning.count == 4 ? tuning[3] : (tuning[0] == 480 ? 1_000_000 : tuning[0] == 512 ? 1_200_000 : 1_300_000)
    guard (1_000_000...2_000_000).contains(rate), rate % 100_000 == 0 else { return standard }
    return [tuning[0], tuning[1], tuning[2], min(1_300_000, rate)]
}

func chatMediaEditorRoundVideoValues(_ values: MediaEditorValues) -> MediaEditorValues {
    guard values.qualityPreset == .videoMessage else { return values }
    let tuning = chatMediaEditorRoundVideoTuning(values.nagramiXRoundTuning)
    guard values.nagramiXRoundTuning != tuning else { return values }
    return values.withUpdatedNagramiXRoundTuning(tuning)
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
            label.numberOfLines = 0
            label.isUserInteractionEnabled = false
            self.view.addSubview(label)
        }
        NotificationCenter.default.addObserver(self, selector: #selector(self.nagramiXRoundTextSizeChanged(_:)), name: UIContentSizeCategory.didChangeNotification, object: nil)
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
                    self?.nagramiXRoundTrimChanged()
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

// Coordinates are in the editor's page space. The track stays anchored to the caption panel.
struct NagramiXRoundSendRows {
    let preview: CGRect
    let title: CGRect
    let hint: CGRect
    let time: CGRect
    let cover: CGRect
    let controlsY: CGFloat

    init(track: CGRect, top: CGFloat, previewLimit: CGSize, textWidth: CGFloat, timeWidth: CGFloat, titleHeight: CGFloat, hintHeight: CGFloat, timeHeight: CGFloat, coverSize: CGSize) {
        func centered(_ width: CGFloat, _ height: CGFloat, at y: CGFloat) -> CGRect {
            return CGRect(x: track.midX - width / 2.0, y: y, width: width, height: height)
        }
        let cover = centered(coverSize.width, coverSize.height, at: track.minY - 4.0 - coverSize.height)
        let controlsBottom = coverSize.height > 0.0 ? cover.minY - 4.0 : track.minY - 4.0
        let controlsHeight = max(chatMediaEditorMuteButtonSize, timeHeight)
        self.cover = cover
        self.controlsY = controlsBottom - controlsHeight / 2.0
        self.time = centered(timeWidth, timeHeight, at: self.controlsY - timeHeight / 2.0)

        let previewBandBottom = controlsBottom - controlsHeight - 6.0
        let available = max(0.0, previewBandBottom - top)
        // On short landscape displays prioritize the time, cover action and usable preview.
        let hintSpace = available >= 80.0 + hintHeight + 8.0 ? hintHeight + 8.0 : 0.0
        let titleSpace = available >= 80.0 + hintSpace + titleHeight + 8.0 ? titleHeight + 8.0 : 0.0
        let bandHeight = max(0.0, available - titleSpace - hintSpace)
        let side = min(previewLimit.width, previewLimit.height, bandHeight)
        let preview = centered(side, side, at: top + titleSpace + floor((bandHeight - side) / 2.0))
        self.preview = preview
        self.hint = hintSpace == 0.0 ? .zero : centered(textWidth, hintHeight, at: preview.maxY + 8.0)
        self.title = titleSpace == 0.0 ? .zero : centered(textWidth, titleHeight, at: preview.minY - titleSpace)
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
                chatMediaEditorValues(current, applying: state).withUpdatedQualityPreset(.videoMessage).withUpdatedNagramiXRoundTuning(nil)
            )
            self.cropLockedAspectRatio = 1.0
            self.mediaEditor.setVideoTrimRange(range, apply: true)
            self.mediaEditor.seek(range.lowerBound, andPlay: wasPlaying)
        }
        self.selectionEditCommitted()
        self.saveCurrentItemEdits()
        self.requestLayout(transition: .animated(duration: 0.2, curve: .easeInOut))
    }

    @objc func nagramiXRoundTextSizeChanged(_ notification: Notification) {
        if self.nagramiXIsRoundVideo { self.requestLayout(transition: .immediate) }
    }

    func nagramiXMeasureRoundSendRows(layout: ContainerViewLayout) -> NagramiXRoundSendRows? {
        guard self.nagramiXCanEditRoundVideo, (layout.inputHeight ?? 0.0) == 0.0 else { return nil }
        let safe = self.editorSafeInsets(layout: layout)
        let toolbar = chatMediaEditorBottomPanelFrame(size: layout.size, safeInsets: safe, toolbarHeight: chatMediaEditorToolbarHeight)
        let side = self.toolbarSide(layout: layout)
        let caption = self.captionPanelView?.baseHeight() ?? 0.0
        let header = chatMediaEditorVideoHeaderFrame(size: layout.size, toolbarMinY: toolbar.minY, captionBaseHeight: caption, safeInsets: safe, toolbarSide: side, reservedCorners: layout.reservedCorners)
        let track = chatMediaEditorScrubberFrame(size: layout.size, safeInsets: safe, headerFrame: header, scrubberHeight: chatMediaEditorCoverScrubberTrackHeight, toolbarSide: side)
        let width = max(1.0, track.width - 12.0)
        let timeWidth = max(1.0, track.width - 2.0 * chatMediaEditorCounterButtonSize.width)
        let strings = self.context.sharedContext.currentPresentationData.with { $0 }.strings
        let traits = self.view.traitCollection
        self.nagramiXRoundTitle.font = UIFontMetrics(forTextStyle: .headline).scaledFont(for: Font.semibold(17.0), compatibleWith: traits)
        let body = UIFontMetrics(forTextStyle: .subheadline).scaledFont(for: Font.regular(14.0), compatibleWith: traits)
        self.nagramiXRoundHint.font = body
        self.nagramiXRoundDuration.font = body
        self.nagramiXRoundTitle.text = strings.nagramiXRoundVideoTitle
        self.nagramiXRoundHint.text = strings.nagramiXRoundVideoCropHint
        self.nagramiXSetRoundTimeText()
        func height(_ label: UILabel, _ width: CGFloat) -> CGFloat {
            return ceil(label.sizeThatFits(CGSize(width: width, height: .greatestFiniteMagnitude)).height)
        }
        let coverSize: CGSize
        if self.isCoverButtonVisible {
            let font = ChatMediaEditorCoverButton.nagramiXRoundFont(self.view.traitCollection)
            let hasThumbnail = self.coverModel?.coverImage(for: self.pageModel.currentItem.uniqueId) != nil
            coverSize = ChatMediaEditorCoverButton.nagramiXRoundSize(title: strings.Media_EditCover, font: font, hasThumbnail: hasThumbnail, maxWidth: width)
        } else {
            coverSize = .zero
        }
        let limit = chatMediaEditorRestingPreviewFrame(size: layout.size, safeInsets: safe, mediaSize: self.previewMediaSize, captionPanelHeight: caption + chatMediaEditorCaptionPanelSpacing, toolbarSide: side, reservedCorners: layout.reservedCorners)
        let top = max(safe.top + 40.0, self.recipientLabel.bounds.height + safe.top + 12.0)
        return NagramiXRoundSendRows(track: track, top: top, previewLimit: limit.size, textWidth: width, timeWidth: timeWidth, titleHeight: height(self.nagramiXRoundTitle, width), hintHeight: height(self.nagramiXRoundHint, width), timeHeight: self.nagramiXRoundDuration.text == nil ? 0.0 : height(self.nagramiXRoundDuration, timeWidth), coverSize: coverSize)
    }

    private func nagramiXSetRoundTimeText() {
        guard let range = self.mediaEditor.values.videoTrimRange else {
            self.nagramiXRoundDuration.text = nil
            return
        }
        let strings = self.context.sharedContext.currentPresentationData.with { $0 }.strings
        let duration = strings.MessageTimer_ShortSeconds(Int32(min(60.0, ceil(range.upperBound - range.lowerBound))))
        self.nagramiXRoundDuration.text = "\(nagramiXRoundVideoTime(range.lowerBound)) — \(nagramiXRoundVideoTime(range.upperBound)) · \(duration)"
    }

    private func nagramiXRoundTrimChanged() {
        guard let rows = self.nagramiXRoundSendRows else { return }
        self.nagramiXSetRoundTimeText()
        let height = ceil(self.nagramiXRoundDuration.sizeThatFits(CGSize(width: rows.time.width, height: .greatestFiniteMagnitude)).height)
        if height != rows.time.height { self.requestLayout(transition: .immediate) }
    }

    func nagramiXUpdateRoundVideoPresentation(transition: ContainedViewLayoutTransition) {
        let round = self.nagramiXIsRoundVideo
        let editing = self.nagramiXCanEditRoundVideo
        self.nagramiXRoundPan.isEnabled = editing
        self.nagramiXRoundPinch.isEnabled = editing
        self.previewContainerView.layer.cornerCurve = .circular
        self.previewContainerView.layer.cornerRadius = round && !self.isCropping ? min(self.previewContainerView.bounds.width, self.previewContainerView.bounds.height) / 2.0 : 0.0
        let rows = self.nagramiXRoundSendRows
        self.previewContainerView.accessibilityHint = rows == nil ? nil : self.nagramiXRoundHint.text
        for (label, frame) in [(self.nagramiXRoundTitle, rows?.title), (self.nagramiXRoundHint, rows?.hint), (self.nagramiXRoundDuration, rows?.time)] {
            label.isHidden = frame?.isEmpty ?? true
            if let frame, !frame.isEmpty { transition.updateFrame(view: label, frame: frame) }
        }
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
