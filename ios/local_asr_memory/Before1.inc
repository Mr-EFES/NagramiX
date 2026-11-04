import Foundation
import os
import NagramiXVosk

private func nagramiXVoskCancelled(_ context: UnsafeMutableRawPointer?) -> Int32 {
    guard let context else { return 1 }
    return Unmanaged<NagramiXTranscriptionCancellation>.fromOpaque(context).takeUnretainedValue().cancelled ? 1 : 0
}

enum NagramiXTranscriptionVosk {
    private static let queue = DispatchQueue(label: "NagramiXTranscription.Vosk", qos: .utility)
    static func model(_ configuration: NagramiXTranscriptionConfiguration) -> NagramiXVoskModel? {
        func base(_ code: String) -> String {
            let value = code.replacingOccurrences(of:"_",with:"-").lowercased().split(separator:"-").first.map(String.init) ?? ""
            return value == "cn" ? "zh" : value
        }
        let language = base(configuration.language)
        guard language != "auto" else { return nil }
        let matching = NagramiXVoskModel.all.filter { base($0.lang) == language }
        if let id = configuration.voskModelID, let selected = matching.first(where: { $0.name == id }) { return selected }
        return matching.first { NagramiXVoskModels.shared.installed($0) } ?? matching.first { $0.type == "small" } ?? matching.first
    }
    static func available(_ configuration: NagramiXTranscriptionConfiguration) -> Bool {
        guard let model = self.model(configuration) else { return false }
        return NagramiXVoskModels.shared.installed(model)
    }
    static func transcribe(media: NagramiXTranscriptionMedia, configuration: NagramiXTranscriptionConfiguration, cancellation: NagramiXTranscriptionCancellation,
                           completion: @escaping (Result<String, NagramiXTranscriptionFailure>) -> Void) {
        self.queue.async {
            do {
                guard let model = self.model(configuration) else { throw NagramiXTranscriptionFailure.language }
                let text = try NagramiXVoskModels.shared.withLease(model) { path -> String in
                    guard !cancellation.cancelled else { throw NagramiXTranscriptionFailure.cancelled }
                    let required = UInt64(model.size) * 3 + 512 * 1024 * 1024
                    guard os_proc_available_memory() >= required else { throw NagramiXTranscriptionFailure.insufficientMemory }
                    let samples = try media.pcm(cancellation: cancellation)
                    guard os_proc_available_memory() >= required else { throw NagramiXTranscriptionFailure.insufficientMemory }
                    var output: UnsafeMutablePointer<CChar>?
                    let code = samples.withUnsafeBufferPointer { buffer in
                        nx_vosk_transcribe(path.path, buffer.baseAddress, Int32(buffer.count), nagramiXVoskCancelled, Unmanaged.passUnretained(cancellation).toOpaque(), &output)
                    }
                    defer { if let output { nx_vosk_free_text(output) } }
                    if cancellation.cancelled || code == 1 { throw NagramiXTranscriptionFailure.cancelled }
                    if code == 4 { throw NagramiXTranscriptionFailure.insufficientMemory }
                    guard code == 0, let output, let data = String(cString: output).data(using: .utf8), let records = try JSONSerialization.jsonObject(with: data) as? [[String: Any]] else { throw NagramiXTranscriptionFailure.unavailableMedia }
                    let text = records.compactMap { $0["text"] as? String }.filter { !$0.isEmpty }.joined(separator: " ").trimmingCharacters(in: .whitespacesAndNewlines)
                    guard !text.isEmpty else { throw NagramiXTranscriptionFailure.noSpeech }
                    guard text.utf16.count <= 100000 else { throw NagramiXTranscriptionFailure.tooLarge }
                    return text
                }
                completion(.success(text))
            } catch { completion(.failure(error as? NagramiXTranscriptionFailure ?? .unavailableMedia)) }
        }
    }
}
