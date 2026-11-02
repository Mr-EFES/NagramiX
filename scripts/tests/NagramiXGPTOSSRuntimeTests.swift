import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

let gptossRuntimeClock = GPTOSSTestClock()
let runtimeFreeClient = NagramiXTranslationCloudClient(session: GPTOSSHTTP.session(), now: gptossRuntimeClock.now)

@main struct GPTOSSRuntimeTests {
    static var count = 0
    static func check(_ value: @autoclosure () -> Bool, _ message: String) {
        count += 1
        if !value() { FileHandle.standardError.write(Data(("FAIL: " + message + "\n").utf8)); exit(1) }
    }
    static func main() {
        let context = AccountContext(), done = DispatchSemaphore(value: 0)
        GPTOSSHTTP.reset { req in
            check(req.url?.host == "text.pollinations.ai" && req.httpMethod == "POST", "actual runtime selects the free GPT-OSS endpoint")
            check(req.value(forHTTPHeaderField: "Authorization") == nil && req.url?.query == nil, "actual free runtime sends neither API key nor text in URL")
            let body = try! JSONSerialization.jsonObject(with: req.httpBody!) as! [String: Any]
            check(body["model"] as? String == "gpt-oss-20b" && body["temperature"] as? Double == 0.6, "runtime forwards pinned GPT-OSS and saved temperature")
            return (200, GPTOSSHTTP.response(["Привет", "Мир"]), [:], 0.01)
        }
        NagramiXTranslationSettings.update { $0.enabled = true; $0.provider = .gptoss; $0.temperatures = ["gptoss":0.6] }
        let config = NagramiXTranslationSettings.current
        var values: [String]?
        let disposable = nagramiXTranslateFragments(context: context, configuration: config, texts: ["Hello", "World"], source: "en", target: "ru", chatKey: nil).start(next: { values = $0 }, error: { _ in done.signal() }, completed: { done.signal() })
        check(done.wait(timeout: .now() + 4) == .success && values == ["Привет", "Мир"], "actual GPT-OSS runtime returns the complete translated batch")
        check(NagramiXTranslationKeys.reads == 0, "GPT-OSS runtime never reads another service's saved key")
        disposable.dispose()
        let off = DispatchSemaphore(value: 0)
        var error: NagramiXTranslationFailure?
        let waiting = nagramiXTranslateFragments(context: context, configuration: config, texts: ["Next"], source: "en", target: "ru", chatKey: nil).start(error: { error = $0; off.signal() })
        NagramiXTranslationSettings.update { $0.enabled = false }
        check(off.wait(timeout: .now() + 4) == .success && error == .cancelled, "OFF cancels a GPT-OSS job waiting for quota")
        check(GPTOSSHTTP.requests.count == 1 && NagramiXTranslationKeys.reads == 0, "OFF prevents the next free request without reading keys")
        waiting.dispose()
        print("PASS: \(count) actual GPT-OSS dispatch / key isolation / temperature / OFF checks")
    }
}
