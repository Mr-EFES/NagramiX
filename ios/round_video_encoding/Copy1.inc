import Foundation
import AVFoundation
import CoreMedia
import SwiftSignalKit
import TelegramCore

/// Size-check custom video notes before exposing any bytes to the pending upload.
/// Ordinary videos retain their original exporter and progressive upload callbacks.
public final class NagramiXRoundVideoExport {
    private let makeExport: (MediaEditorVideoExport.Subject, MediaEditorVideoExport.Configuration, String) -> MediaEditorVideoExport
    private let subject: MediaEditorVideoExport.Subject
    private let configuration: MediaEditorVideoExport.Configuration
    private let outputPath: String
    private let queue = Queue(name: "NagramiX.RoundVideoExport")
    private let cancelled = Atomic<Bool>(value: false)
    private let statusPromise = Promise<MediaEditorVideoExport.ExportStatus>(.unknown)
    private let statusDisposable = MetaDisposable()
    private let preferencesDisposable = MetaDisposable()
    private var activeExport: MediaEditorVideoExport?
    private var cleanupAttempt: (() -> Void)?
    private var generation = 0
    private var attempts = 0
    private var targetVideoBitRate = 0
    private var lastProgress: Float = 0
    public var streamingFileGrowth: ((Int64, Int64) -> Void)?

    public init(subject: MediaEditorVideoExport.Subject, configuration: MediaEditorVideoExport.Configuration, outputPath: String, roundEncoding: Signal<[String: Any]?, NoError>, makeExport: @escaping (MediaEditorVideoExport.Subject, MediaEditorVideoExport.Configuration, String) -> MediaEditorVideoExport) {
        self.makeExport = makeExport
        self.subject = subject
        self.configuration = configuration
        self.outputPath = outputPath
        if configuration.nagramiXIsCustomRoundVideo, case let .video(_, isStory) = subject, !isStory {
            self.preferencesDisposable.set((roundEncoding
            |> take(1)
            |> deliverOn(self.queue)).start(next: { [weak self] encoding in
                guard let self, !self.cancelled.with({ $0 }) else { return }
                let policy = NagramiXRoundVideoEncodingPolicy(encoding: encoding)
                var configuration = configuration
                var compression = configuration.videoSettings[AVVideoCompressionPropertiesKey] as? [String: Any] ?? [:]
                let requested = (compression[AVVideoAverageBitRateKey] as? NSNumber)?.intValue ?? 1_200_000
                let audioRate = (configuration.audioSettings[AVEncoderBitRateKey] as? NSNumber)?.intValue ?? 64_000
                guard let rate = policy.videoBitRate(requested: requested, audioBitRate: audioRate) else {
                    self.statusPromise.set(.single(.failed(.invalid)))
                    return
                }
                self.targetVideoBitRate = rate
                compression[AVVideoAverageBitRateKey] = rate
                configuration.videoSettings[AVVideoCompressionPropertiesKey] = compression
                self.begin(configuration: configuration, policy: policy)
            }))
        } else {
            self.queue.async { [weak self] in self?.begin(configuration: configuration, policy: nil) }
        }
    }

    deinit {
        self.preferencesDisposable.dispose()
        self.statusDisposable.dispose()
        self.activeExport?.cancel()
        self.cleanupAttempt?()
    }

    public var status: Signal<MediaEditorVideoExport.ExportStatus, NoError> {
        return self.statusPromise.get()
    }

    public func cancel() {
        guard !self.cancelled.swap(true) else { return }
        self.queue.async { [weak self] in
            guard let self else { return }
            self.generation += 1
            self.preferencesDisposable.dispose()
            self.statusDisposable.dispose()
            self.activeExport?.cancel()
            self.activeExport = nil
            self.cleanupAttempt?()
            self.cleanupAttempt = nil
        }
    }

    private func begin(configuration: MediaEditorVideoExport.Configuration, policy: NagramiXRoundVideoEncodingPolicy?) {
        guard !self.cancelled.with({ $0 }) else { return }
        self.statusDisposable.set(nil)
        self.activeExport = nil
        self.cleanupAttempt?()
        self.cleanupAttempt = nil
        self.generation += 1
        self.attempts += 1
        let generation = self.generation
        let path: String
        if policy != nil {
            let file = EngineTempBox.shared.tempFile(fileName: "round-video.mp4")
            path = file.path
            self.cleanupAttempt = { EngineTempBox.shared.dispose(file) }
        } else {
            path = self.outputPath
        }
        let exporter = self.makeExport(self.subject, configuration, path)
        self.activeExport = exporter
        if policy == nil {
            exporter.streamingFileGrowth = { [weak self] size, header in
                guard let self, !self.cancelled.with({ $0 }) else { return }
                self.streamingFileGrowth?(size, header)
            }
        }
        self.statusDisposable.set((exporter.status |> deliverOn(self.queue)).start(next: { [weak self] status in
            guard let self, !self.cancelled.with({ $0 }), self.generation == generation else { return }
            guard let policy else {
                self.statusPromise.set(.single(status))
                return
            }
            switch status {
            case .completed:
                guard let size = (try? FileManager.default.attributesOfItem(atPath: path)[.size] as? NSNumber)?.int64Value, size > 0 else {
                    self.statusPromise.set(.single(.failed(.writing(nil))))
                    return
                }
                let encodedDuration = AVURLAsset(url: URL(fileURLWithPath: path)).duration.seconds
                let audioRate = (configuration.audioSettings[AVEncoderBitRateKey] as? NSNumber)?.intValue ?? 64_000
                guard let byteCeiling = policy.maximumEncodedSize(videoBitRate: self.targetVideoBitRate, audioBitRate: audioRate, duration: encodedDuration) else {
                    self.statusPromise.set(.single(.failed(.invalid)))
                    return
                }
                if !policy.contains(size: size) || size > byteCeiling {
                    let rate = ((configuration.videoSettings[AVVideoCompressionPropertiesKey] as? [String: Any])?[AVVideoAverageBitRateKey] as? NSNumber)?.intValue ?? 0
                    guard self.attempts < NagramiXRoundVideoEncodingPolicy.maximumAttempts,
                          let nextRate = policy.retryBitRate(current: rate, actualSize: size, maximumSize: byteCeiling) else {
                        self.statusPromise.set(.single(.failed(.writing(nil))))
                        return
                    }
                    var next = configuration
                    var compression = next.videoSettings[AVVideoCompressionPropertiesKey] as? [String: Any] ?? [:]
                    compression[AVVideoAverageBitRateKey] = nextRate
                    next.videoSettings[AVVideoCompressionPropertiesKey] = compression
                    Logger.shared.log("NagramiX", "Round size retry: bytes=\(size); maxBytes=\(policy.maximumSize); targetBps=\(nextRate); attempt=\(self.attempts + 1)")
                    self.queue.justDispatch { [weak self] in self?.begin(configuration: next, policy: policy) }
                    return
                }
                guard self.matchesVideo(path: path, configuration: configuration) else {
                    self.statusPromise.set(.single(.failed(.invalid)))
                    return
                }
                guard !self.cancelled.with({ $0 }) else { return }
                do {
                    if FileManager.default.fileExists(atPath: self.outputPath) { try FileManager.default.removeItem(atPath: self.outputPath) }
                    try FileManager.default.moveItem(atPath: path, toPath: self.outputPath)
                } catch {
                    self.statusPromise.set(.single(.failed(.writing(error))))
                    return
                }
                self.cleanupAttempt?()
                self.cleanupAttempt = nil
                guard !self.cancelled.with({ $0 }) else {
                    try? FileManager.default.removeItem(atPath: self.outputPath)
                    return
                }
                Logger.shared.log("NagramiX", "Round validated: bytes=\(size); maxBytes=\(policy.maximumSize); fps=\(configuration.frameRate); attempts=\(self.attempts)")
                self.statusPromise.set(.single(.completed))
            case let .progress(value):
                if value.isFinite {
                    self.lastProgress = max(self.lastProgress, min(0.95, max(0, value) * 0.95))
                    self.statusPromise.set(.single(.progress(self.lastProgress)))
                }
            case .failed where configuration.useStreamingWriter && self.attempts < NagramiXRoundVideoEncodingPolicy.maximumAttempts:
                // A hardware streaming-property refusal retries the AV writer with the same codec/FPS.
                var next = configuration
                next.useStreamingWriter = false
                self.queue.justDispatch { [weak self] in self?.begin(configuration: next, policy: policy) }
            default:
                self.statusPromise.set(.single(status))
            }
        }))
    }

    private func matchesVideo(path: String, configuration: MediaEditorVideoExport.Configuration) -> Bool {
        let asset = AVURLAsset(url: URL(fileURLWithPath: path))
        guard let track = asset.tracks(withMediaType: .video).first,
              let firstDescription = track.formatDescriptions.first else { return false }
        let description = firstDescription as! CMFormatDescription
        let dimensions = CMVideoFormatDescriptionGetDimensions(description)
        guard dimensions.width == Int32(configuration.videoSettings[AVVideoWidthKey] as? Int ?? 0),
              dimensions.height == Int32(configuration.videoSettings[AVVideoHeightKey] as? Int ?? 0),
              track.nominalFrameRate.isFinite, abs(track.nominalFrameRate - configuration.frameRate) <= 1.0 else { return false }
        let expected = (configuration.videoSettings[AVVideoCodecKey] as? AVVideoCodecType)?.rawValue
            ?? configuration.videoSettings[AVVideoCodecKey] as? String
        let codec = CMFormatDescriptionGetMediaSubType(description)
        return expected == AVVideoCodecType.h264.rawValue ? codec == kCMVideoCodecType_H264
            : expected == AVVideoCodecType.hevc.rawValue && (codec == kCMVideoCodecType_HEVC || codec == 0x68657631)
    }
}

/// Resample only custom video notes. The composer still applies the track's rotation/crop once.
func nagramiXRoundVideoReaderOutput(track: AVAssetTrack, outputSettings: [String: Any], duration: CMTime, frameRate: Float) -> AVAssetReaderVideoCompositionOutput {
    let composition = AVMutableVideoComposition()
    composition.renderSize = track.naturalSize
    composition.frameDuration = CMTime(value: 1, timescale: CMTimeScale(frameRate))
    composition.sourceTrackIDForFrameTiming = kCMPersistentTrackID_Invalid
    let instruction = AVMutableVideoCompositionInstruction()
    instruction.timeRange = CMTimeRange(start: .zero, duration: duration)
    let layer = AVMutableVideoCompositionLayerInstruction(assetTrack: track)
    layer.setTransform(.identity, at: .zero)
    instruction.layerInstructions = [layer]
    composition.instructions = [instruction]
    let output = AVAssetReaderVideoCompositionOutput(videoTracks: [track], videoSettings: outputSettings)
    output.videoComposition = composition
    return output
}
