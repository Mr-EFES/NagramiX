import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

final class FreeTranslationHTTP: URLProtocol {
    static let lock = NSLock()
    static var requests: [URLRequest] = []
    static var handler: (URLRequest) -> (Int, Data, TimeInterval) = { _ in (500, Data(), 0) }
    private var stopped = false
    private let state = NSLock()
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        Self.lock.lock(); Self.requests.append(request); let response = Self.handler(request); Self.lock.unlock()
        DispatchQueue.global().asyncAfter(deadline: .now() + response.2) {
            self.state.lock(); defer { self.state.unlock() }
            guard !self.stopped else { return }
            self.client?.urlProtocol(self, didReceive: HTTPURLResponse(url: self.request.url!, statusCode: response.0, httpVersion: nil, headerFields: nil)!, cacheStoragePolicy: .notAllowed)
            self.client?.urlProtocol(self, didLoad: response.1); self.client?.urlProtocolDidFinishLoading(self)
        }
    }
    override func stopLoading() { state.lock(); stopped = true; state.unlock() }
    static func reset(_ handler: @escaping (URLRequest) -> (Int, Data, TimeInterval)) {
        lock.lock(); requests = []; self.handler = handler; lock.unlock()
    }
    static var count: Int { lock.lock(); defer { lock.unlock() }; return requests.count }
}

@main struct FreeTranslationTests {
    static var checks = 0
    static func check(_ value: @autoclosure () throws -> Bool, _ message: String) {
        checks += 1
        do { if try value() { return } } catch {}
        FileHandle.standardError.write(Data(("FAIL: " + message + "\n").utf8)); exit(1)
    }
    static func rejects(_ message: String, _ body: () throws -> Void) { do { try body(); check(false, message) } catch { check(true, message) } }
    static func json(_ value: Any) -> Data { try! JSONSerialization.data(withJSONObject: value) }
    static func session() -> URLSession {
        let configuration = URLSessionConfiguration.ephemeral; configuration.protocolClasses = [FreeTranslationHTTP.self]
        return URLSession(configuration: configuration)
    }
    static func wait(_ sem: DispatchSemaphore) { check(sem.wait(timeout: .now() + 5) == .success, "bounded HTTP completion") }
    static func main() throws {
        let legacy = Data(#"{"enabled":true,"automatic":true,"provider":"deepseek","target":"de","ignored":["ru"],"models":{"deepseek":"deepseek-flash"},"revision":"old"}"#.utf8)
        let migrated = try JSONDecoder().decode(NagramiXTranslationConfiguration.self, from: legacy)
        check(migrated.enabled && migrated.automatic && migrated.revision == "old" && migrated.models["deepseek"] == "deepseek-flash", "v1 settings survive temperature migration")
        check(migrated.temperature(for: .deepseek) == 0.2 && migrated.temperature(for: .gemini) == 1, "model-specific defaults")
        NagramiXTranslationSettings.update { $0.enabled = true; $0.temperatures = ["deepseek": 0.63, "gemini": 1.2] }
        let revision = NagramiXTranslationSettings.current.revision
        check(NagramiXTranslationSettings.current.temperature(for: .deepseek) == 0.6 && NagramiXTranslationSettings.current.temperature(for: .gemini) == 1.2, "independent snapped temperatures")
        NagramiXTranslationSettings.update { $0.temperatures?["deepseek"] = 0.4 }
        check(NagramiXTranslationSettings.current.revision != revision, "temperature changes invalidate cached/in-flight translations")
        check(NagramiXTranslationProvider.allCases.map(\.title) == ["Apple", "Google", "Яндекс", "Gemini", "ChatGPT", "DeepSeek"], "approved labels preserved")
        for provider in [NagramiXTranslationProvider.google, .yandex] {
            check(provider.isFreeWeb && !provider.isLanguageModel, "free provider route")
            let plan = try NagramiXTranslationWebPlan(provider: provider, texts: [" Hello & + Мир 🙂 ", "World"], source: "en", target: "ru")
            let request = plan.requests[0]
            check(request.httpMethod == "POST" && request.url?.scheme == "https", "free HTTPS POST")
            check(request.value(forHTTPHeaderField: "Authorization") == nil && request.value(forHTTPHeaderField: "x-goog-api-key") == nil, "free requests contain no API key")
            check(!request.url!.absoluteString.contains("Hello") && !request.url!.absoluteString.contains("%D0"), "message text never enters URL")
            check(String(data: request.httpBody!, encoding: .utf8)!.contains("%26%20%2B%20"), "form escapes plus ampersand Unicode")
            check(try plan.restore(["Привет", "Мир"]) == [" Привет ", "Мир"], "batch order and edge whitespace preserved")
            rejects("old Cloud credentials cannot activate a paid Google/Yandex route") {
                _ = try NagramiXTranslationCloudCodec.request(provider: provider, credential: .init(key: "old-paid-key", folder: "old-folder"), model: "", texts: ["Hello"], source: "en", target: "ru")
            }
            rejects("language cannot inject request parameters") { _ = try NagramiXTranslationWebPlan(provider: provider, texts: ["Hello"], source: "en&key=bad", target: "ru") }
            rejects("empty text rejected") { _ = try NagramiXTranslationWebPlan(provider: provider, texts: ["  "], source: "en", target: "ru") }
        }
        let longText = String(repeating: "Hello 👨‍👩‍👧‍👦 world! ", count: 260)
        let longPlan = try NagramiXTranslationWebPlan(provider: .google, texts: [longText], source: "en", target: "ru")
        check(longPlan.parts.count > 1 && longPlan.parts.allSatisfy { $0.text.utf8.count <= 3500 }, "long text split within web limits")
        check(try longPlan.restore(longPlan.parts.map(\.text)) == [longText], "splitting preserves graphemes and exact whitespace")
        check(try NagramiXTranslationWebCodec.response(provider: .google, status: 200, data: json([[["Привет ", "Hello"], ["мир", "world"]]])) == "Привет мир", "Google joins every translated sentence")
        check(try NagramiXTranslationWebCodec.response(provider: .yandex, status: 200, data: json(["code":200, "text":["Здравствуйте"]])) == "Здравствуйте", "Yandex anonymous response")
        check(try NagramiXTranslationWebCodec.session(data: Data(#"<script>config={"SID":"cba.654.fed.987"}</script>"#.utf8), status: 200) == "abc.456.def.789", "current four-part Yandex session decoded")
        rejects("CAPTCHA page never treated as a translation") { _ = try NagramiXTranslationWebCodec.session(data: Data("<html>CAPTCHA</html>".utf8), status: 200) }
        for provider in [NagramiXTranslationProvider.google, .yandex] {
            for status in [301, 400, 401, 403, 402, 429, 500] {
                rejects("web status failure \(status)") { _ = try NagramiXTranslationWebCodec.response(provider: provider, status: status, data: Data("{}".utf8)) }
            }
            for data in [Data("<html>captcha</html>".utf8), Data("[]".utf8), json(["code":200,"text":[]]), json(["code":200,"text":[""]])] {
                rejects("malformed/empty web response preserves original") { _ = try NagramiXTranslationWebCodec.response(provider: provider, status: 200, data: data) }
            }
        }
        for provider in [NagramiXTranslationProvider.gemini, .chatgpt, .deepseek] {
            for value in [0.0, 0.2, 1.0, 2.0] {
                let request = try NagramiXTranslationCloudCodec.request(provider: provider, credential: .init(key: "owned-key", folder: ""), model: provider.defaultModel, texts: ["Hello"], source: "en", target: "ru", temperature: value)
                let body = try JSONSerialization.jsonObject(with: request.httpBody!) as! [String: Any]
                let actual = provider == .gemini ? (body["generationConfig"] as? [String: Any])?["temperature"] as? Double : body["temperature"] as? Double
                check(actual == value, "selected temperature reaches selected LLM")
                check((request.value(forHTTPHeaderField: provider == .gemini ? "x-goog-api-key" : "Authorization") ?? "").contains("owned-key"), "own key routes to selected LLM")
                if provider == .chatgpt { check(body["reasoning_effort"] as? String == "none", "ChatGPT sampling-compatible non-thinking mode") }
            }
            rejects("LLM requires own key even when quota is free") { _ = try NagramiXTranslationCloudCodec.request(provider: provider, credential: .init(key: "", folder: ""), model: provider.defaultModel, texts: ["Hello"], source: "en", target: "ru") }
            for value in [Double.nan, -.infinity, -0.1, 2.1] {
                rejects("invalid temperature rejected") { _ = try NagramiXTranslationCloudCodec.request(provider: provider, credential: .init(key: "owned-key", folder: ""), model: provider.defaultModel, texts: ["Hello"], source: "en", target: "ru", temperature: value) }
            }
        }
        let oldModel = try NagramiXTranslationCloudCodec.request(provider: .chatgpt, credential: .init(key: "owned-key", folder: ""), model: "gpt-5-mini", texts: ["Hello"], source: "en", target: "ru", temperature: 0.2)
        let oldBody = try JSONSerialization.jsonObject(with: oldModel.httpBody!) as! [String: Any]
        check(oldBody["temperature"] == nil && oldBody["reasoning_effort"] == nil, "legacy models never receive unsupported sampling")
        try clients()
        print("PASS: \(checks) free web / temperature / migration / cancellation checks")
    }
    static func clients() throws {
        FreeTranslationHTTP.reset { req in
            if req.url?.host == "translate.yandex.com" { return (200, Data(#"{"SID":"cba.654.fed.987"}"#.utf8), 0.01) }
            if req.url?.host == "translate.yandex.net" {
                check(req.url!.absoluteString.contains("id=abc.456.def.789-"), "bootstrap session is used for the following request")
                return (200, json(["code":200,"text":["Перевод"]]), 0.01)
            }
            return (200, json([[["Перевод", "Hello"]]]), 0.01)
        }
        let client = NagramiXTranslationCloudClient(session: session())
        for provider in [NagramiXTranslationProvider.google, .yandex] {
            let plan = try NagramiXTranslationWebPlan(provider: provider, texts: ["Hello", "World"], source: "en", target: "ru")
            let before = FreeTranslationHTTP.count, sem = DispatchSemaphore(value: 0)
            for _ in 0 ..< 4 {
                _ = client.translate(request: plan.requests[0], provider: provider, count: 2, scope: "batch:" + provider.rawValue, webPlan: plan) { result in
                    check((try? result.get()) == ["Перевод", "Перевод"], "coalesced subscribers receive complete ordered batch"); sem.signal()
                }
            }
            for _ in 0 ..< 4 { wait(sem) }
            check(FreeTranslationHTTP.count - before == (provider == .yandex ? 3 : 2), "one anonymous batch per coalesced job")
            _ = client.translate(request: plan.requests[0], provider: provider, count: 2, scope: "batch:" + provider.rawValue, webPlan: plan) { _ in sem.signal() }
            wait(sem)
            check(FreeTranslationHTTP.count - before == (provider == .yandex ? 3 : 2), "completed free translation uses memory cache")
        }
        FreeTranslationHTTP.reset { _ in (429, Data(), 0.01) }
        let quotaClient = NagramiXTranslationCloudClient(session: session())
        let plan = try NagramiXTranslationWebPlan(provider: .google, texts: ["Hello", "World"], source: "en", target: "ru"), sem = DispatchSemaphore(value: 0)
        for scope in ["quota-1", "quota-2"] {
            _ = quotaClient.translate(request: plan.requests[0], provider: .google, count: 2, scope: scope, webPlan: plan) { result in
                if case .failure(.quota) = result { check(true, "quota reported without paid fallback") } else { check(false, "quota reported without paid fallback") }; sem.signal()
            }
            wait(sem)
        }
        check(FreeTranslationHTTP.count == 1, "rate limit prevents immediate repeat network requests")
        FreeTranslationHTTP.reset { _ in (200, json([[["Перевод", "Hello"]]]), 0.1) }
        let cancelClient = NagramiXTranslationCloudClient(session: session())
        let canceled = DispatchSemaphore(value: 0)
        let cancel = cancelClient.translate(request: plan.requests[0], provider: .google, count: 2, scope: "cancel", webPlan: plan) { _ in canceled.signal() }
        cancel()
        check(canceled.wait(timeout: .now() + 0.25) == .timedOut, "disposed anonymous subscriber never receives late completion")
        _ = cancelClient.translate(request: plan.requests[0], provider: .google, count: 2, scope: "disabled", allowed: { false }, webPlan: plan) { result in
            if case .failure(.cancelled) = result { check(true, "OFF does not issue a request") } else { check(false, "OFF does not issue a request") }; sem.signal()
        }
        wait(sem)
    }
}
