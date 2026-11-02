import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

let runtimeFreeSession: URLSession = {
    let config = URLSessionConfiguration.ephemeral; config.protocolClasses = [FreeTranslationHTTP.self]
    return URLSession(configuration: config)
}()
let runtimeFreeClient = NagramiXTranslationCloudClient(session: runtimeFreeSession)

@main struct FreeTranslationRuntimeTests {
    static var count = 0
    static func check(_ value: @autoclosure () -> Bool, _ message: String) {
        count += 1
        if !value() { FileHandle.standardError.write(Data(("FAIL: " + message + "\n").utf8)); exit(1) }
    }
    static func main() {
        let context = AccountContext()
        FreeTranslationHTTP.reset { request in
            check(request.value(forHTTPHeaderField: "Authorization") == nil, "anonymous runtime never sends the legacy Cloud key")
            if request.url?.host == "translate.yandex.com" { return (200, Data(#"{"SID":"cba.654.fed.987"}"#.utf8), 0.01) }
            if request.url?.host == "translate.yandex.net" { return (200, Data(#"{"code":200,"text":["Перевод"]}"#.utf8), 0.01) }
            return (200, Data(#"[[["Перевод","Hello"]]]"#.utf8), 0.01)
        }
        for provider in [NagramiXTranslationProvider.google, .yandex] {
            NagramiXTranslationSettings.update { $0.enabled = true; $0.provider = provider }
            let config = NagramiXTranslationSettings.current, done = DispatchSemaphore(value: 0)
            var result: [String]?
            let disposable = nagramiXTranslateFragments(context: context, configuration: config, texts: ["Hello", "World"], source: "en", target: "ru", chatKey: nil).start(next: { result = $0 }, completed: { done.signal() })
            check(done.wait(timeout: .now() + 5) == .success, "free provider finishes through actual runtime")
            check(result == ["Перевод", "Перевод"], "actual runtime preserves fragment order")
            check(NagramiXTranslationKeys.reads == 0, "Google and Yandex do not even read previously saved keys")
            disposable.dispose()
        }
        FreeTranslationHTTP.reset { request in
            let body = try! JSONSerialization.jsonObject(with: request.httpBody!) as! [String: Any]
            let provider = NagramiXTranslationSettings.current.provider
            let temperature = provider == .gemini ? (body["generationConfig"] as! [String: Any])["temperature"] as? Double : body["temperature"] as? Double
            check(temperature == 0.7, "actual runtime forwards the selected temperature")
            check((request.value(forHTTPHeaderField: provider == .gemini ? "x-goog-api-key" : "Authorization") ?? "").contains("legacy-owned-key"), "actual runtime uses user's selected LLM key")
            if provider == .gemini { return (200, Data(#"{"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":"{\"translations\":[\"Перевод\"]}"}]}}]}"#.utf8), 0.01) }
            return (200, Data(#"{"choices":[{"finish_reason":"stop","message":{"content":"{\"translations\":[\"Перевод\"]}"}}]}"#.utf8), 0.01)
        }
        for provider in [NagramiXTranslationProvider.gemini, .chatgpt, .deepseek] {
            NagramiXTranslationSettings.update { $0.provider = provider; $0.temperatures = [provider.rawValue: 0.7] }
            let config = NagramiXTranslationSettings.current, done = DispatchSemaphore(value: 0)
            var result: [String]?
            let disposable = nagramiXTranslateFragments(context: context, configuration: config, texts: ["Hello"], source: "en", target: "ru", chatKey: nil).start(next: { result = $0 }, error: { _ in done.signal() }, completed: { done.signal() })
            check(done.wait(timeout: .now() + 5) == .success, "LLM finishes through actual runtime")
            check(result == ["Перевод"], "LLM actual response returns to runtime")
            disposable.dispose()
        }
        check(NagramiXTranslationKeys.reads == 3, "only the three neural APIs read a key")
        let arrived = DispatchSemaphore(value: 0)
        FreeTranslationHTTP.reset { _ in arrived.signal(); return (200, Data(#"[[["Перевод","Hello"]]]"#.utf8), 0.2) }
        NagramiXTranslationSettings.update { $0.provider = .google }
        let config = NagramiXTranslationSettings.current, done = DispatchSemaphore(value: 0)
        var failed: NagramiXTranslationFailure?
        let disposable = nagramiXTranslateFragments(context: context, configuration: config, texts: ["Cancel", "Next"], source: "en", target: "ru", chatKey: nil).start(error: { failed = $0; done.signal() })
        check(arrived.wait(timeout: .now() + 5) == .success, "anonymous first fragment starts")
        NagramiXTranslationSettings.update { $0.enabled = false }
        check(done.wait(timeout: .now() + 5) == .success && failed == .cancelled, "master OFF cancels actual anonymous pipeline")
        check(FreeTranslationHTTP.count == 1, "master OFF prevents following anonymous fragments")
        disposable.dispose()
        print("PASS: \(count) actual free/LLM runtime routing and cancellation checks")
    }
}
