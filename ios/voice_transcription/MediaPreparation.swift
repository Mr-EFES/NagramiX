import Foundation
import AVFoundation
import UniversalMediaPlayer

final class NagramiXTranscriptionMedia {
    let directory: URL
    var audio: URL { self.directory.appendingPathComponent("audio.m4a") }
    init() throws {
        self.directory = FileManager.default.temporaryDirectory.appendingPathComponent("nagramix-asr-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: self.directory, withIntermediateDirectories: true, attributes: [.protectionKey: FileProtectionType.completeUntilFirstUserAuthentication])
    }
    deinit { try? FileManager.default.removeItem(at: self.directory) }
    static func prepare(path: String, cancellation: NagramiXTranscriptionCancellation,
                        completion: @escaping (Result<NagramiXTranscriptionMedia, NagramiXTranscriptionFailure>) -> Void) {
        let job = NagramiXAudioPreparation(path: path, cancellation: cancellation, completion: completion)
        job.queue.async { job.start() }
    }
    func pcm(cancellation: NagramiXTranscriptionCancellation) throws -> [Float] {
        let asset = AVURLAsset(url: self.audio)
        guard let track = asset.tracks(withMediaType: .audio).first else { throw NagramiXTranscriptionFailure.unavailableMedia }
        let reader = try AVAssetReader(asset: asset)
        let output = AVAssetReaderTrackOutput(track: track, outputSettings: [AVFormatIDKey: kAudioFormatLinearPCM, AVSampleRateKey: 16000, AVNumberOfChannelsKey: 1, AVLinearPCMBitDepthKey: 32, AVLinearPCMIsFloatKey: true, AVLinearPCMIsNonInterleaved: false, AVLinearPCMIsBigEndianKey: false])
        guard reader.canAdd(output) else { throw NagramiXTranscriptionFailure.unavailableMedia }
        reader.add(output); guard reader.startReading() else { throw NagramiXTranscriptionFailure.unavailableMedia }
        defer { reader.cancelReading() }
        var samples: [Float] = []
        while let buffer = output.copyNextSampleBuffer() {
            guard !cancellation.cancelled else { throw NagramiXTranscriptionFailure.cancelled }
            guard let block = CMSampleBufferGetDataBuffer(buffer) else { throw NagramiXTranscriptionFailure.unavailableMedia }
            let bytes = CMBlockBufferGetDataLength(block)
            if bytes == 0 { continue }
            guard bytes <= 16000 * 900 * 4, bytes % MemoryLayout<Float>.size == 0, samples.count + bytes / 4 <= 16000 * 900 else { throw NagramiXTranscriptionFailure.tooLarge }
            var chunk = [Float](repeating: 0, count: bytes / 4)
            let status = chunk.withUnsafeMutableBytes { CMBlockBufferCopyDataBytes(block, atOffset: 0, dataLength: bytes, destination: $0.baseAddress!) }
            guard status == kCMBlockBufferNoErr else { throw NagramiXTranscriptionFailure.unavailableMedia }
            samples.append(contentsOf: chunk)
        }
        guard reader.status == .completed, !samples.isEmpty else { throw NagramiXTranscriptionFailure.unavailableMedia }
        return samples
    }
}

// All AVAssetWriter, decoder and timer state belongs to this serial queue.
private final class NagramiXAudioPreparation {
    let queue = DispatchQueue(label: "NagramiXTranscription.AudioPreparation", qos: .utility)
    private let path: String
    private let cancellation: NagramiXTranscriptionCancellation
    private let completion: (Result<NagramiXTranscriptionMedia, NagramiXTranscriptionFailure>) -> Void
    private var lease: NagramiXTranscriptionMedia?
    private var source: SoftwareAudioSource?
    private var writer: AVAssetWriter?
    private var input: AVAssetWriterInput?
    private var timer: DispatchSourceTimer?
    private var duration: Double = 0
    private let deadline = Date().addingTimeInterval(180)
    private var finished = false
    init(path: String, cancellation: NagramiXTranscriptionCancellation, completion: @escaping (Result<NagramiXTranscriptionMedia, NagramiXTranscriptionFailure>) -> Void) {
        self.path = path; self.cancellation = cancellation; self.completion = completion
    }
    func start() {
        do {
            guard !self.cancellation.cancelled else { throw NagramiXTranscriptionFailure.cancelled }
            let bytes = (try FileManager.default.attributesOfItem(atPath: self.path)[.size] as? NSNumber)?.int64Value ?? 0
            guard bytes > 0, bytes <= 100_000_000 else { throw NagramiXTranscriptionFailure.tooLarge }
            let lease = try NagramiXTranscriptionMedia(); self.lease = lease
            let sourceURL = lease.directory.appendingPathComponent("source")
            try FileManager.default.copyItem(at: URL(fileURLWithPath: self.path), to: sourceURL)
            guard !self.cancellation.cancelled else { throw NagramiXTranscriptionFailure.cancelled }
            let source = SoftwareAudioSource(path: sourceURL.path); self.source = source
            guard source.hasStream else { throw NagramiXTranscriptionFailure.unavailableMedia }
            let writer = try AVAssetWriter(outputURL: lease.audio, fileType: .m4a); self.writer = writer
            let input = AVAssetWriterInput(mediaType: .audio, outputSettings: [AVFormatIDKey: kAudioFormatMPEG4AAC, AVSampleRateKey: 48000, AVNumberOfChannelsKey: 1, AVEncoderBitRateKey: 64000]); self.input = input
            input.expectsMediaDataInRealTime = false
            guard writer.canAdd(input) else { throw NagramiXTranscriptionFailure.unavailableMedia }
            writer.add(input); guard writer.startWriting() else { throw NagramiXTranscriptionFailure.storage }
            writer.startSession(atSourceTime: .zero)
            let timer = DispatchSource.makeTimerSource(queue: self.queue); self.timer = timer
            timer.schedule(deadline: .now() + 0.25, repeating: 0.25)
            timer.setEventHandler { self.check() }; timer.resume()
            input.requestMediaDataWhenReady(on: self.queue) { self.feed() }
        } catch { self.finish(error as? NagramiXTranscriptionFailure ?? .storage) }
    }
    private func check() {
        if self.cancellation.cancelled { self.finish(.cancelled) }
        else if Date() > self.deadline || self.writer?.status == .failed { self.finish(.unavailableMedia) }
    }
    private func feed() {
        guard let input = self.input, let source = self.source else { self.finish(.unavailableMedia); return }
        while !self.finished && input.isReadyForMoreMediaData {
            self.check(); if self.finished { return }
            guard let sample = source.readSampleBuffer() else { self.finish(self.duration > 0 ? nil : .noSpeech); return }
            let duration = CMSampleBufferGetDuration(sample)
            let seconds = CMTimeGetSeconds(duration)
            let samples = CMSampleBufferGetNumSamples(sample)
            guard seconds.isFinite, seconds > 0, samples > 0, samples <= Int(Int32.max) else { self.finish(.unavailableMedia); return }
            guard self.duration + seconds <= 900 else { self.finish(.tooLarge); return }
            // Opus may start with negative decoder PTS. Write a continuous PCM
            // timeline from zero rather than rejecting or dropping that frame.
            var timing = CMSampleTimingInfo(duration: CMTimeMultiplyByRatio(duration, multiplier: 1, divisor: Int32(samples)), presentationTimeStamp: CMTime(seconds: self.duration, preferredTimescale: 48000), decodeTimeStamp: .invalid)
            var timed: CMSampleBuffer?
            guard CMSampleBufferCreateCopyWithNewTiming(allocator: nil, sampleBuffer: sample, sampleTimingEntryCount: 1, sampleTimingArray: &timing, sampleBufferOut: &timed) == noErr, let timed else { self.finish(.unavailableMedia); return }
            self.duration += seconds
            guard input.append(timed) else { self.finish(.unavailableMedia); return }
        }
    }
    private func finish(_ error: NagramiXTranscriptionFailure?) {
        guard !self.finished else { return }; self.finished = true
        self.timer?.cancel(); self.timer?.setEventHandler {}; self.timer = nil
        self.input?.stopRequestingMediaData(); self.source = nil
        if let error { if self.writer?.status == .writing { self.writer?.cancelWriting() }; self.completion(.failure(error)); return }
        guard let writer = self.writer, let lease = self.lease else { self.completion(.failure(.unavailableMedia)); return }
        self.input?.markAsFinished()
        writer.finishWriting {
            let size = (try? FileManager.default.attributesOfItem(atPath: lease.audio.path)[.size] as? NSNumber)?.int64Value ?? 0
            if self.cancellation.cancelled { self.completion(.failure(.cancelled)) }
            else if writer.status != .completed || size == 0 { self.completion(.failure(.unavailableMedia)) }
            else if size > 25_000_000 { self.completion(.failure(.tooLarge)) }
            else { self.completion(.success(lease)) }
        }
    }
}
