import Foundation
import NagramiXVosk

private func nagramiXVoskCancelled(_ context: UnsafeMutableRawPointer?) -> Int32 {
    guard let context else { return 1 }
    return Unmanaged<NagramiXTranscriptionCancellation>.fromOpaque(context).takeUnretainedValue().cancelled ? 1 : 0
}

enum NagramiXTranscriptionVosk {
    static func model(_ configuration: NagramiXTranscriptionConfiguration) -> NagramiXVoskModel? {
        func base(_ code: String) -> String {
            let value = code.replacingOccurrences(of:"_",with:"-").lowercased().split(separator:"-").first.map(String.init) ?? ""
            return value == "cn" ? "zh" : value
        }
        let language = base(configuration.language)
        guard language != "auto" else { return nil }
        let matching = NagramiXVoskModel.all.filter { base($0.lang) == language }
        if let id = configuration.voskModelID, let selected = matching.first(where: { $0.name == id }) { return selected }
        let mobile = matching.filter { $0.type == "small" }
        return mobile.first { NagramiXVoskModels.shared.installed($0) } ?? mobile.first
    }
    static func available(_ configuration: NagramiXTranscriptionConfiguration) -> Bool {
        guard let model = self.model(configuration) else { return false }
        return NagramiXVoskModels.shared.installed(model)
    }
    static func transcribe(media: NagramiXTranscriptionMedia, configuration: NagramiXTranscriptionConfiguration, cancellation: NagramiXTranscriptionCancellation,
                           completion: @escaping (Result<String, NagramiXTranscriptionFailure>) -> Void) {
        NagramiXLocalInferenceMemory.queue.async {
            let outcome: Result<String, NagramiXTranscriptionFailure> = autoreleasepool {
                do {
                    guard let model = self.model(configuration) else { throw NagramiXTranscriptionFailure.language }
                    let text = try NagramiXVoskModels.shared.withLease(model) { path -> String in
                        guard !cancellation.cancelled else { throw NagramiXTranscriptionFailure.cancelled }
                        let required = try NagramiXLocalInferenceMemory.vosk(at: path)
                        try NagramiXLocalInferenceMemory.require(required)
                        return try media.withPCM(cancellation: cancellation) { samples in
                            guard !cancellation.cancelled else { throw NagramiXTranscriptionFailure.cancelled }
                            try NagramiXLocalInferenceMemory.require(required)
                            var output: UnsafeMutablePointer<CChar>?
                            let code = nx_vosk_transcribe(path.path, samples.baseAddress, Int32(samples.count), nagramiXVoskCancelled, Unmanaged.passUnretained(cancellation).toOpaque(), &output)
                            defer { if let output { nx_vosk_free_text(output) } }
                            if cancellation.cancelled || code == 1 { throw NagramiXTranscriptionFailure.cancelled }
                            if code == 4 { throw NagramiXTranscriptionFailure.insufficientMemory }
                            guard code == 0, let output, let data = String(cString: output).data(using: .utf8), let records = try JSONSerialization.jsonObject(with: data) as? [[String: Any]] else { throw NagramiXTranscriptionFailure.unavailableMedia }
                            let text = records.compactMap { $0["text"] as? String }.filter { !$0.isEmpty }.joined(separator: " ").trimmingCharacters(in: .whitespacesAndNewlines)
                            guard !text.isEmpty else { throw NagramiXTranscriptionFailure.noSpeech }
                            guard text.utf16.count <= 100000 else { throw NagramiXTranscriptionFailure.tooLarge }
                            return text
                        }
                    }
                    return .success(text)
                } catch { return .failure(error as? NagramiXTranscriptionFailure ?? .unavailableMedia) }
            }
            completion(outcome)
        }
    }
}
