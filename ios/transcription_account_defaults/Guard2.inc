import Foundation
import Speech

// The legacy fallback also requires on-device recognition; no server fallback.
enum NagramiXTranscriptionApple {
    static var authorized: Bool {
        #if compiler(>=6.2)
        if #available(iOS 26.0, *), SpeechTranscriber.isAvailable { return true }
        #endif
        return SFSpeechRecognizer.authorizationStatus() == .authorized
    }
    static func available(_ language: String) -> Bool {
        guard language != "auto" else { return false }
        #if compiler(>=6.2)
        if #available(iOS 26.0, *), SpeechTranscriber.isAvailable { return true }
        #endif
        return SFSpeechRecognizer(locale: Locale(identifier: language))?.supportsOnDeviceRecognition == true
    }
    static func transcribe(url: URL, language: String, automatic: Bool, cancellation: NagramiXTranscriptionCancellation,
                           completion: @escaping (Result<String, NagramiXTranscriptionFailure>) -> Void) {
        #if compiler(>=6.2)
        if #available(iOS 26.0, *) {
            NagramiXTranscriptionAnalyzer.transcribe(url: url, language: language, automatic: automatic, cancellation: cancellation, completion: completion)
            return
        }
        #endif
        self.legacy(url: url, language: language, automatic: automatic, cancellation: cancellation, completion: completion)
    }
    static func legacy(url: URL, language: String, automatic: Bool, cancellation: NagramiXTranscriptionCancellation,
                       completion: @escaping (Result<String, NagramiXTranscriptionFailure>) -> Void) {
        DispatchQueue.main.async {
            let job = NagramiXLegacySpeechJob(url: url, language: language, cancellation: cancellation, completion: completion)
            cancellation.add { DispatchQueue.main.async { job.finish(.failure(.cancelled)) } }
            if SFSpeechRecognizer.authorizationStatus() == .notDetermined && !automatic {
                SFSpeechRecognizer.requestAuthorization { _ in DispatchQueue.main.async { job.start() } }
            } else { job.start() }
        }
    }
}
private final class NagramiXLegacySpeechJob {
    private let url: URL
    private let language: String
    private let cancellation: NagramiXTranscriptionCancellation
    private let completion: (Result<String, NagramiXTranscriptionFailure>) -> Void
    private var recognizer: SFSpeechRecognizer?
    private var task: SFSpeechRecognitionTask?
    private var timeout: DispatchWorkItem?
    private var finished = false
    init(url: URL, language: String, cancellation: NagramiXTranscriptionCancellation, completion: @escaping (Result<String, NagramiXTranscriptionFailure>) -> Void) {
        self.url = url; self.language = language; self.cancellation = cancellation; self.completion = completion
    }
    func start() {
        guard !self.finished else { return }
        guard !self.cancellation.cancelled else { self.finish(.failure(.cancelled)); return }
        guard self.language != "auto", let recognizer = SFSpeechRecognizer(locale: Locale(identifier: self.language)), recognizer.supportsOnDeviceRecognition, recognizer.isAvailable else { self.finish(.failure(.unavailable)); return }
        guard SFSpeechRecognizer.authorizationStatus() == .authorized else { self.finish(.failure(.permission)); return }
        self.recognizer = recognizer
        let request = SFSpeechURLRecognitionRequest(url: self.url)
        request.requiresOnDeviceRecognition = true; request.shouldReportPartialResults = false; request.taskHint = .dictation
        self.task = recognizer.recognitionTask(with: request) { [weak self] result, error in
            DispatchQueue.main.async {
                guard let self else { return }
                if let result, result.isFinal {
                    let text = result.bestTranscription.formattedString.trimmingCharacters(in: .whitespacesAndNewlines)
                    self.finish(text.isEmpty ? .failure(.noSpeech) : .success(text))
                } else if error != nil { self.finish(.failure(.unavailable)) }
            }
        }
        let timeout = DispatchWorkItem { [weak self] in self?.finish(.failure(.unavailable)) }
        self.timeout = timeout; DispatchQueue.main.asyncAfter(deadline: .now() + 120, execute: timeout)
    }
    func finish(_ result: Result<String, NagramiXTranscriptionFailure>) {
        guard !self.finished else { return }; self.finished = true
        self.timeout?.cancel(); self.timeout = nil; self.task?.cancel(); self.task = nil; self.recognizer = nil
        self.completion(self.cancellation.cancelled ? .failure(.cancelled) : result)
    }
}
