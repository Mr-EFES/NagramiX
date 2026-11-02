import Foundation
import NagramiXWhisper
import os

private final class NagramiXWhisperLease {
    private let lock = NSLock()
    private var pointer: OpaquePointer? = nx_whisper_create()
    func run(_ body: (OpaquePointer) throws -> String) throws -> String {
        self.lock.lock(); let pointer = self.pointer; self.lock.unlock()
        guard let pointer else { throw NagramiXTranscriptionFailure.unavailable }
        return try body(pointer)
    }
    func cancel() { self.lock.lock(); if let pointer { nx_whisper_cancel(pointer) }; self.lock.unlock() }
    func finish() { self.lock.lock(); if let pointer { nx_whisper_destroy(pointer); self.pointer = nil }; self.lock.unlock() }
    deinit { self.finish() }
}

enum NagramiXTranscriptionWhisper {
    private static let queue = DispatchQueue(label: "NagramiXTranscription.Whisper", qos: .utility)
    static func transcribe(media: NagramiXTranscriptionMedia, configuration: NagramiXTranscriptionConfiguration,
                           cancellation: NagramiXTranscriptionCancellation, completion: @escaping (Result<String, NagramiXTranscriptionFailure>) -> Void) {
        self.queue.async {
            do {
                let text = try NagramiXWhisperModels.shared.withLease(configuration.whisper) { url -> String in
                    guard !cancellation.cancelled else { throw NagramiXTranscriptionFailure.cancelled }
                    // Large models can exceed the process memory budget even on devices
                    // with ample physical RAM. Check both before and after decoding audio.
                    let required = UInt64(configuration.whisper.size) * 2 + 512 * 1024 * 1024
                    guard os_proc_available_memory() >= required else { throw NagramiXTranscriptionFailure.insufficientMemory }
                    let samples = try media.pcm(cancellation: cancellation)
                    guard os_proc_available_memory() >= required else { throw NagramiXTranscriptionFailure.insufficientMemory }
                    let lease = NagramiXWhisperLease(); defer { lease.finish() }
                    cancellation.add { lease.cancel() }
                    return try lease.run { pointer in
                        var output: UnsafeMutablePointer<CChar>?
                        let language = configuration.language == "auto" ? "auto" : String(configuration.language.replacingOccurrences(of: "_", with: "-").split(separator: "-").first ?? "ru")
                        let result = samples.withUnsafeBufferPointer { buffer in
                            nx_whisper_transcribe(pointer, url.path, buffer.baseAddress, Int32(buffer.count), language, Int32(max(1, min(4, ProcessInfo.processInfo.activeProcessorCount - 1))), &output)
                        }
                        defer { if let output { nx_whisper_free_text(output) } }
                        if result == 1 || cancellation.cancelled { throw NagramiXTranscriptionFailure.cancelled }
                        if result == 3 { throw NagramiXTranscriptionFailure.noSpeech }
                        guard result == 0, let output else { throw NagramiXTranscriptionFailure.unavailableMedia }
                        let text = String(cString: output).trimmingCharacters(in: .whitespacesAndNewlines)
                        guard !text.isEmpty, text.utf16.count <= 100_000 else { throw NagramiXTranscriptionFailure.noSpeech }
                        return text
                    }
                }
                completion(.success(text))
            } catch { completion(.failure(error as? NagramiXTranscriptionFailure ?? .unavailableMedia)) }
        }
    }
}
