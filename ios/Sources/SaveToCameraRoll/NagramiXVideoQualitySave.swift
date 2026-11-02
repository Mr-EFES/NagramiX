import Foundation
import AVFoundation
import Photos
import SwiftSignalKit
import TelegramCore
import AccountContext
import DeviceAccess

@available(iOS 15.0, *)
private func nagramiXExportVideo(asset: AVAsset, track: AVAssetTrack, duration: CMTime, size: CGSize, transform: CGAffineTransform, frameDuration: CMTime, output: URL, passthrough: Bool, sessionState: Atomic<AVAssetExportSession?>, cancelled: Atomic<Bool>, progress: @escaping (Float) -> Void) async throws {
    guard !cancelled.with({ $0 }) else { throw CancellationError() }
    guard let session = AVAssetExportSession(asset: asset, presetName: passthrough ? AVAssetExportPresetPassthrough : AVAssetExportPresetHighestQuality), session.supportedFileTypes.contains(.mp4) else {
        throw NagramiXGalleryVideoSaveError.conversion
    }
    session.outputURL = output
    session.outputFileType = .mp4
    session.shouldOptimizeForNetworkUse = true
    if !passthrough {
        let layer = AVMutableVideoCompositionLayerInstruction(assetTrack: track)
        layer.setTransform(transform, at: .zero)
        let instruction = AVMutableVideoCompositionInstruction()
        instruction.timeRange = CMTimeRange(start: .zero, duration: duration)
        instruction.layerInstructions = [layer]
        let composition = AVMutableVideoComposition()
        composition.renderSize = size
        composition.frameDuration = frameDuration
        composition.instructions = [instruction]
        session.videoComposition = composition
    }
    _ = sessionState.swap(session)
    let timer = SwiftSignalKit.Timer(timeout: 0.15, repeat: true, completion: { [weak session] in
        if let session, !cancelled.with({ $0 }) { progress(0.45 + 0.45 * session.progress) }
    }, queue: .mainQueue())
    timer.start()
    defer { timer.invalidate(); _ = sessionState.swap(nil) }
    await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
        session.exportAsynchronously { continuation.resume() }
        // Cancellation may precede publishing the session into sessionState.
        if cancelled.with({ $0 }) { session.cancelExport() }
    }
    guard !cancelled.with({ $0 }) else { throw CancellationError() }
    guard session.status == .completed else { throw NagramiXGalleryVideoSaveError.conversion }
}

@available(iOS 15.0, *)
private func nagramiXPrepareAndSaveVideo(context: AccountContext, path: String, quality: Int, sessionState: Atomic<AVAssetExportSession?>, cancelled: Atomic<Bool>, progress: @escaping (Float) -> Void) async throws {
    guard !cancelled.with({ $0 }) else { throw CancellationError() }
    let input = EngineTempBox.shared.tempFile(fileName: "input.mp4")
    let output = EngineTempBox.shared.tempFile(fileName: "video-\(quality)p.mp4")
    // The task awaits export and Photos completion. Cancellation never deletes
    // a file still being read by either native operation.
    defer { EngineTempBox.shared.dispose(input); EngineTempBox.shared.dispose(output) }
    do {
        do { try FileManager.default.linkItem(atPath: path, toPath: input.path) }
        catch { try FileManager.default.copyItem(atPath: path, toPath: input.path) }
    } catch { throw NagramiXGalleryVideoSaveError.download }
    guard !cancelled.with({ $0 }) else { throw CancellationError() }
    let asset = AVURLAsset(url: URL(fileURLWithPath: input.path))
    guard let track = try await asset.loadTracks(withMediaType: .video).first else { throw NagramiXGalleryVideoSaveError.conversion }
    let naturalSize = try await track.load(.naturalSize)
    let preferredTransform = try await track.load(.preferredTransform)
    let duration = try await asset.load(.duration)
    let frameTime = try await track.load(.minFrameDuration)
    let displayRect = CGRect(origin: .zero, size: naturalSize).applying(preferredTransform)
    guard let dimensions = NagramiXVideoSavePolicy.targetSize(width: Double(abs(displayRect.width)), height: Double(abs(displayRect.height)), quality: quality), min(abs(displayRect.width), abs(displayRect.height)) + 2 >= CGFloat(quality), duration.isNumeric, duration.seconds.isFinite, duration.seconds > 0 else { throw NagramiXGalleryVideoSaveError.conversion }
    let target = CGSize(width: CGFloat(dimensions.width), height: CGFloat(dimensions.height))
    let transform = preferredTransform
        .concatenating(CGAffineTransform(translationX: -displayRect.minX, y: -displayRect.minY))
        .concatenating(CGAffineTransform(scaleX: target.width / abs(displayRect.width), y: target.height / abs(displayRect.height)))
    let frameDuration = frameTime.isNumeric && frameTime.seconds > 0 ? frameTime : CMTime(value: 1, timescale: 30)
    let sameSize = abs(abs(displayRect.width) - target.width) < 0.5 && abs(abs(displayRect.height) - target.height) < 0.5
    let outputURL = URL(fileURLWithPath: output.path)
    if sameSize {
        do {
            try await nagramiXExportVideo(asset: asset, track: track, duration: duration, size: target, transform: transform, frameDuration: frameDuration, output: outputURL, passthrough: true, sessionState: sessionState, cancelled: cancelled, progress: progress)
        } catch {
            guard !cancelled.with({ $0 }) else { throw CancellationError() }
            try? FileManager.default.removeItem(at: outputURL)
            try await nagramiXExportVideo(asset: asset, track: track, duration: duration, size: target, transform: transform, frameDuration: frameDuration, output: outputURL, passthrough: false, sessionState: sessionState, cancelled: cancelled, progress: progress)
        }
    } else {
        try await nagramiXExportVideo(asset: asset, track: track, duration: duration, size: target, transform: transform, frameDuration: frameDuration, output: outputURL, passthrough: false, sessionState: sessionState, cancelled: cancelled, progress: progress)
    }
    guard !cancelled.with({ $0 }) else { throw CancellationError() }
    let exported = AVURLAsset(url: outputURL)
    guard let exportedTrack = try await exported.loadTracks(withMediaType: .video).first else { throw NagramiXGalleryVideoSaveError.conversion }
    let exportedSize = try await exportedTrack.load(.naturalSize)
    let exportedTransform = try await exportedTrack.load(.preferredTransform)
    let exportedDisplay = CGRect(origin: .zero, size: exportedSize).applying(exportedTransform)
    let exportedDuration = try await exported.load(.duration)
    let attributes = try FileManager.default.attributesOfItem(atPath: output.path)
    guard ((attributes[.size] as? NSNumber)?.int64Value ?? 0) > 0,
          abs(abs(exportedDisplay.width) - target.width) <= 2, abs(abs(exportedDisplay.height) - target.height) <= 2,
          exportedDuration.isNumeric, abs(exportedDuration.seconds - duration.seconds) <= max(0.25, frameDuration.seconds * 2) else { throw NagramiXGalleryVideoSaveError.conversion }
    if !(try await asset.loadTracks(withMediaType: .audio)).isEmpty {
        guard !(try await exported.loadTracks(withMediaType: .audio)).isEmpty else { throw NagramiXGalleryVideoSaveError.conversion }
    }
    let authorized = await withCheckedContinuation { (continuation: CheckedContinuation<Bool, Never>) in
        Queue.mainQueue().async {
            guard !cancelled.with({ $0 }) else { continuation.resume(returning: false); return }
            DeviceAccess.authorizeAccess(to: .mediaLibrary(.save), presentationData: context.sharedContext.currentPresentationData.with { $0 }, present: { controller, arguments in
                context.sharedContext.presentGlobalController(controller, arguments)
            }, openSettings: context.sharedContext.applicationBindings.openSettings, { continuation.resume(returning: $0) })
        }
    }
    guard !cancelled.with({ $0 }) else { throw CancellationError() }
    guard authorized else { throw NagramiXGalleryVideoSaveError.permissionDenied }
    progress(0.95)
    let saved = await withCheckedContinuation { (continuation: CheckedContinuation<Bool, Never>) in
        PHPhotoLibrary.shared().performChanges({
            PHAssetCreationRequest.forAsset().addResource(with: .video, fileURL: outputURL, options: nil)
        }, completionHandler: { success, _ in continuation.resume(returning: success) })
    }
    guard !cancelled.with({ $0 }) else { throw CancellationError() }
    guard saved else { throw NagramiXGalleryVideoSaveError.library }
}

private func nagramiXSaveVideoAttempt(context: AccountContext, userLocation: MediaResourceUserLocation, source: FileMediaReference, quality: Int) -> Signal<Float, NagramiXGalleryVideoSaveError> {
    guard #available(iOS 15.0, *), quality >= 2, quality <= 32768 else { return .fail(.conversion) }
    return Signal { subscriber in
        let cancelled = Atomic<Bool>(value: false)
        let started = Atomic<Bool>(value: false)
        let session = Atomic<AVAssetExportSession?>(value: nil)
        let task = Atomic<Task<Void, Never>?>(value: nil)
        let disposables = DisposableSet()
        let mediaBox = context.account.postbox.mediaBox
        let resource = source.media.resource
        disposables.add(mediaBox.keepResource(id: resource.id).start())
        disposables.add((mediaBox.resourceStatus(resource)
        |> deliverOnMainQueue).start(next: { status in
            guard !cancelled.with({ $0 }), !started.with({ $0 }) else { return }
            switch status {
            case let .Fetching(_, fraction): subscriber.putNext(Float(fraction) * 0.45)
            case .Local: subscriber.putNext(0.45)
            default: break
            }
        }))
        disposables.add((mediaBox.resourceData(resource)
        |> filter { $0.complete }
        |> take(1)).start(next: { data in
            guard !cancelled.with({ $0 }), !started.swap(true) else { return }
            guard data.offset == 0, data.size > 0 else { subscriber.putError(.download); return }
            let operation = Task {
                do {
                    try await nagramiXPrepareAndSaveVideo(context: context, path: data.path, quality: quality, sessionState: session, cancelled: cancelled, progress: { value in
                        if !cancelled.with({ $0 }) { subscriber.putNext(value) }
                    })
                    guard !cancelled.with({ $0 }) else { return }
                    subscriber.putNext(1.0)
                    subscriber.putCompletion()
                } catch {
                    if !cancelled.with({ $0 }) { subscriber.putError((error as? NagramiXGalleryVideoSaveError) ?? .conversion) }
                }
            }
            _ = task.swap(operation)
            if cancelled.with({ $0 }) { operation.cancel() }
        }))
        if !started.with({ $0 }) {
            disposables.add(fetchedMediaResource(mediaBox: mediaBox, userLocation: userLocation, userContentType: MediaResourceUserContentType(file: source.media), reference: source.resourceReference(resource), reportResultStatus: true).start(error: { _ in
                if !cancelled.with({ $0 }), !started.with({ $0 }) { subscriber.putError(.download) }
            }))
        }
        return ActionDisposable {
            _ = cancelled.swap(true)
            task.with { $0 }?.cancel()
            session.with { $0 }?.cancelExport()
            disposables.dispose()
        }
    }
}

public func nagramiXSaveGalleryVideoQuality(context: AccountContext, userLocation: MediaResourceUserLocation, source: FileMediaReference, original: FileMediaReference, quality: Int) -> Signal<Float, NagramiXGalleryVideoSaveError> {
    let first = nagramiXSaveVideoAttempt(context: context, userLocation: userLocation, source: source, quality: quality)
    let result: Signal<Float, NagramiXGalleryVideoSaveError>
    if source.media.fileId != original.media.fileId {
        result = first |> `catch` { error -> Signal<Float, NagramiXGalleryVideoSaveError> in
            guard NagramiXVideoSavePolicy.mayRetryFromOriginal(error) else { return .fail(error) }
            return nagramiXSaveVideoAttempt(context: context, userLocation: userLocation, source: original, quality: quality)
        }
    } else { result = first }
    // Retrying from the original must not make the visible progress go backwards.
    return Signal { subscriber in
        let previous = Atomic<Float>(value: 0.0)
        return result.start(next: { value in
            guard value.isFinite else { return }
            let bounded = max(0.0, min(1.0, value))
            let next = previous.modify { max($0, bounded) }
            subscriber.putNext(next)
        }, error: subscriber.putError, completed: subscriber.putCompletion)
    }
}
