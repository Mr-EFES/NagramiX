import Foundation
import Speech
import AVFoundation

#if compiler(>=6.2)
@available(iOS 26.0, *)
enum NagramiXTranscriptionAnalyzer {
    private static func match(_ language: String, locales: [Locale]) -> Locale? {
        guard language != "auto" else { return nil }
        let requested = language.replacingOccurrences(of: "_", with: "-").lowercased()
        return locales.first { $0.identifier.replacingOccurrences(of: "_", with: "-").lowercased() == requested }
    }
    static func install(language: String, completion: @escaping (Result<String, NagramiXTranscriptionFailure>) -> Void) {
        Task {
            do {
                guard SpeechTranscriber.isAvailable, let locale = self.match(language, locales: await SpeechTranscriber.supportedLocales) else { throw NagramiXTranscriptionFailure.unavailable }
                let module = SpeechTranscriber(locale: locale, preset: .transcription)
                if let request = try await AssetInventory.assetInstallationRequest(supporting: [module]) { try await request.downloadAndInstall() }
                completion(.success("Язык Apple загружен. Распознавание выполняется на устройстве."))
            } catch { completion(.failure(error as? NagramiXTranscriptionFailure ?? .network)) }
        }
    }
    static func transcribe(url: URL, language: String, automatic: Bool, cancellation: NagramiXTranscriptionCancellation,
                           completion: @escaping (Result<String, NagramiXTranscriptionFailure>) -> Void) {
        let task = Task {
            guard !cancellation.cancelled else { completion(.failure(.cancelled)); return }
            guard SpeechTranscriber.isAvailable, let locale = self.match(language, locales: await SpeechTranscriber.installedLocales) else {
                NagramiXTranscriptionApple.legacy(url: url, language: language, automatic: automatic, cancellation: cancellation, completion: completion)
                return
            }
            do {
                let text = try await withThrowingTaskGroup(of: String.self) { group in
                    group.addTask { try await self.recognize(url: url, locale: locale) }
                    group.addTask { try await Task.sleep(nanoseconds: 180_000_000_000); throw NagramiXTranscriptionFailure.unavailable }
                    defer { group.cancelAll() }
                    guard let result = try await group.next() else { throw NagramiXTranscriptionFailure.noSpeech }
                    return result
                }
                completion(cancellation.cancelled ? .failure(.cancelled) : .success(text))
            } catch { completion(.failure(cancellation.cancelled ? .cancelled : (error as? NagramiXTranscriptionFailure ?? .unavailable))) }
        }
        cancellation.add { task.cancel() }
    }
    private static func recognize(url: URL, locale: Locale) async throws -> String {
        try Task.checkCancellation()
        let module = SpeechTranscriber(locale: locale, preset: .transcription)
        let analyzer = SpeechAnalyzer(modules: [module])
        return try await withTaskCancellationHandler(operation: {
            let file = try AVAudioFile(forReading: url)
            try await analyzer.start(inputAudioFile: file, finishAfterFile: true)
            var text = ""
            for try await result in module.results {
                try Task.checkCancellation()
                if result.isFinal { text += String(result.text.characters) }
                guard text.utf16.count <= 100_000 else { throw NagramiXTranscriptionFailure.invalidResponse }
            }
            let value = text.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !value.isEmpty else { throw NagramiXTranscriptionFailure.noSpeech }
            return value
        }, onCancel: { Task { await analyzer.cancelAndFinishNow() } })
    }
}
#endif
