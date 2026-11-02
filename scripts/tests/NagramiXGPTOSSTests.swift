import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

@main struct GPTOSSTests {
    static let lock = NSLock()
    static var checks = 0
    static func check(_ value: @autoclosure () throws -> Bool, _ message: String) {
        lock.lock(); checks += 1; lock.unlock()
        do { if try value() { return } } catch {}
        FileHandle.standardError.write(Data(("FAIL: " + message + "\n").utf8)); exit(1)
    }
    static func reject(_ message: String, _ body: () throws -> Void) { do { try body(); check(false, message) } catch { check(true, message) } }
    static func request(_ texts: [String] = ["Hello", "World"]) throws -> URLRequest {
        try NagramiXTranslationCloudCodec.request(provider: .gptoss, credential: .init(key: "", folder: ""), model: "gpt-oss-20b", texts: texts, source: "en", target: "ru", temperature: 0.2)
    }
    static func wait(_ sem: DispatchSemaphore) { check(sem.wait(timeout: .now() + 4) == .success, "bounded completion") }
    static func main() throws {
        check(NagramiXTranslationProvider.allCases.map(\.title) == ["Apple", "Google", "Яндекс", "Gemini", "ChatGPT", "DeepSeek", "GPT-OSS · Бесплатно"], "seventh provider preserves the original six labels")
        check(NagramiXTranslationProvider.allCases.filter(\.requiresAPIKey) == [.gemini, .chatgpt, .deepseek], "GPT-OSS is excluded from API-key pages")
        check(NagramiXTranslationProvider.gptoss.isLanguageModel && !NagramiXTranslationProvider.gptoss.isFreeWeb, "free LLM uses JSON batch rather than the Google/Yandex codec")
        let old = Data(#"{"enabled":true,"automatic":false,"provider":"deepseek","target":"ru","ignored":["de"],"models":{},"revision":"keep"}"#.utf8)
        let migrated = try JSONDecoder().decode(NagramiXTranslationConfiguration.self, from: old)
        check(migrated.enabled && migrated.provider == .deepseek && migrated.ignored == ["de"] && migrated.revision == "keep", "six-provider preferences are not reset")
        NagramiXTranslationSettings.update { $0.enabled = true; $0.provider = .gptoss; $0.models["gptoss"] = "gpt-6"; $0.temperatures = ["gptoss": 0.7, "deepseek": 0.3] }
        check(NagramiXTranslationSettings.current.model == "gpt-oss-20b", "saved arbitrary model never substitutes the free model")
        let stored = try JSONEncoder().encode(NagramiXTranslationSettings.current)
        check(try JSONDecoder().decode(NagramiXTranslationConfiguration.self, from: stored).provider == .gptoss, "seventh provider persists")
        check(NagramiXTranslationSettings.current.temperature(for: .gptoss) == 0.7 && NagramiXTranslationSettings.current.temperature(for: .deepseek) == 0.3, "GPT-OSS temperature is independent")
        let req = try request()
        check(req.httpMethod == "POST" && req.url?.absoluteString == "https://text.pollinations.ai/openai", "free request uses the documented Pollinations endpoint")
        check(req.url?.query == nil && req.value(forHTTPHeaderField: "Authorization") == nil && req.value(forHTTPHeaderField: "x-goog-api-key") == nil, "anonymous GPT-OSS sends no key or text in URL")
        let body = try JSONSerialization.jsonObject(with: req.httpBody!) as! [String: Any]
        check(body["model"] as? String == "gpt-oss-20b" && body["temperature"] as? Double == 0.2 && body["stream"] as? Bool == false, "pinned model and selected temperature are sent")
        let messages = body["messages"] as! [[String: String]]
        check(messages.count == 2 && messages[0]["role"] == "system" && messages[0]["content"]!.contains("untrusted data"), "translation instruction is separate from untrusted messages")
        let payload = try JSONSerialization.jsonObject(with: Data(messages[1]["content"]!.utf8)) as! [String: Any]
        check(payload["texts"] as? [String] == ["Hello", "World"], "all fragments fit one ordered anonymous batch")
        let ignored = try NagramiXTranslationCloudCodec.request(provider: .gptoss, credential: .init(key: "NEVER-SEND-THIS", folder: "legacy"), model: "gpt-oss-20b", texts: ["Hello"], source: "en", target: "ru", temperature: 0.5)
        check(!String(data: ignored.httpBody!, encoding: .utf8)!.contains("NEVER-SEND-THIS") && ignored.value(forHTTPHeaderField: "Authorization") == nil, "unrelated keys can never leak to Pollinations")
        reject("unsupported free model is rejected") { _ = try NagramiXTranslationCloudCodec.request(provider: .gptoss, credential: .init(key: "", folder: ""), model: "openai", texts: ["Hello"], source: "en", target: "ru") }
        check(try NagramiXTranslationCloudCodec.response(provider: .gptoss, status: 200, data: GPTOSSHTTP.response(["Привет", "Мир"]), count: 2) == ["Привет", "Мир"], "only the final translation is returned, never reasoning")
        for model in ["gpt-6", "gemini-3.1-flash-lite", "", "deepseek-flash"] {
            reject("another model response cannot masquerade as GPT-OSS") { _ = try NagramiXTranslationCloudCodec.response(provider: .gptoss, status: 200, data: GPTOSSHTTP.response(["Привет"], model: model), count: 1) }
        }
        reject("truncated free output is rejected") { _ = try NagramiXTranslationCloudCodec.response(provider: .gptoss, status: 200, data: GPTOSSHTTP.response(["Привет"], finish: "length"), count: 1) }
        reject("incomplete batch is rejected") { _ = try NagramiXTranslationCloudCodec.response(provider: .gptoss, status: 200, data: GPTOSSHTTP.response(["Привет"]), count: 2) }
        for status in [301, 400, 401, 403, 402, 429, 500] {
            reject("HTTP failure never creates a fake translation") { _ = try NagramiXTranslationCloudCodec.response(provider: .gptoss, status: status, data: GPTOSSHTTP.response(["Привет"]), count: 1) }
        }
        try queue(req)
        print("PASS: \(checks) GPT-OSS routing / model / quota / queue / cancellation checks")
    }
    static func queue(_ request: URLRequest) throws {
        let clock = GPTOSSTestClock(), sem = DispatchSemaphore(value: 0)
        GPTOSSHTTP.reset { _ in (200, GPTOSSHTTP.response(["Привет", "Мир"]), [:], 0.01) }
        let client = NagramiXTranslationCloudClient(session: GPTOSSHTTP.session(), now: clock.now)
        for _ in 0 ..< 3 {
            _ = client.translate(request: request, provider: .gptoss, count: 2, scope: "account1:revision1") { result in
                check((try? result.get()) == ["Привет", "Мир"], "coalesced free translation"); sem.signal()
            }
        }
        for _ in 0 ..< 3 { wait(sem) }
        check(GPTOSSHTTP.requests.count == 1, "identical anonymous jobs coalesce")
        _ = client.translate(request: request, provider: .gptoss, count: 2, scope: "account1:revision1") { _ in sem.signal() }; wait(sem)
        check(GPTOSSHTTP.requests.count == 1, "cache hit does not consume a free request")
        let second = DispatchSemaphore(value: 0)
        _ = client.translate(request: request, provider: .gptoss, count: 2, scope: "account2:revision1") { result in
            check((try? result.get()) == ["Привет", "Мир"], "queued account has its own result"); second.signal()
        }
        clock.advance(29)
        check(second.wait(timeout: .now() + 0.08) == .timedOut && GPTOSSHTTP.requests.count == 1, "30-second free quota spans all accounts")
        // A waiting anonymous job must not block other providers' active slots.
        let other = try NagramiXTranslationCloudCodec.request(provider: .deepseek, credential: .init(key: "local-test-only", folder: ""), model: "deepseek-flash", texts: ["Hello", "World"], source: "en", target: "ru")
        _ = client.translate(request: other, provider: .deepseek, count: 2, scope: "other-provider") { result in
            check((try? result.get()) == ["Привет", "Мир"], "other provider runs while GPT-OSS waits"); sem.signal()
        }; wait(sem)
        clock.advance(1); wait(second)
        check(GPTOSSHTTP.requests.count == 3, "exactly one next free request starts after the interval")
        let cancelled = DispatchSemaphore(value: 0)
        let cancel = client.translate(request: request, provider: .gptoss, count: 2, scope: "cancel-queued") { _ in cancelled.signal() }
        cancel()
        let barrier = DispatchSemaphore(value: 0)
        _ = client.translate(request: request, provider: .gptoss, count: 2, scope: "off-barrier", allowed: { false }) { _ in barrier.signal() }
        wait(barrier); clock.advance(30)
        check(cancelled.wait(timeout: .now() + 0.08) == .timedOut && GPTOSSHTTP.requests.count == 3, "cancelled waiting job never issues a request")
        // Retry-After is honored, including an HTTP date, with no automatic retry.
        let retryClock = GPTOSSTestClock(), retry = DispatchSemaphore(value: 0)
        GPTOSSHTTP.reset { _ in (402, Data("payment not requested".utf8), ["Retry-After":"120"], 0.01) }
        let quota = NagramiXTranslationCloudClient(session: GPTOSSHTTP.session(), now: retryClock.now)
        _ = quota.translate(request: request, provider: .gptoss, count: 2, scope: "limited") { result in
            if case .failure(.quota) = result { check(true, "quota is reported without payment/fallback") } else { check(false, "quota is reported without payment/fallback") }; retry.signal()
        }; wait(retry)
        GPTOSSHTTP.reset { _ in (200, GPTOSSHTTP.response(["Привет", "Мир"]), [:], 0.01) }
        _ = quota.translate(request: request, provider: .gptoss, count: 2, scope: "after-quota") { _ in retry.signal() }
        retryClock.advance(119)
        check(retry.wait(timeout: .now() + 0.08) == .timedOut && GPTOSSHTTP.requests.isEmpty, "Retry-After delays subsequent GPT-OSS jobs")
        retryClock.advance(1); wait(retry)
        check(GPTOSSHTTP.requests.count == 1, "only the new job runs after Retry-After")
    }
}
