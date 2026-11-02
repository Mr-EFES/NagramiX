import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

@main struct TranslationCoreTests {
    static var checks = 0
    static func check(_ condition: @autoclosure () throws -> Bool, _ message: String) {
        self.checks += 1
        do {
            if try condition() { return }
        } catch {}
        FileHandle.standardError.write(Data(("FAIL: " + message + "\n").utf8)); exit(1)
    }
    static func rejects(_ message: String, _ operation: () throws -> Void) {
        do { try operation(); self.check(false, message) } catch { self.check(true, message) }
    }
    static func json(_ value: Any) -> Data { try! JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]) }

    static func main() throws {
        check(NagramiXTranslationProvider.allCases.map(\.title) == ["Apple", "Google", "Яндекс", "Gemini", "ChatGPT", "DeepSeek"], "six approved provider labels")
        check(!NagramiXTranslationSettings.current.enabled && !NagramiXTranslationSettings.current.automatic, "opt-in defaults")
        check(NagramiXTranslationSettings.current.provider == .apple && NagramiXTranslationSettings.current.revision == "initial", "stable local default without a key")
        NagramiXTranslationSettings.update { $0.enabled = true; $0.automatic = true; $0.provider = .deepseek; $0.target = "de" }
        let revision = NagramiXTranslationSettings.current.revision
        NagramiXTranslationSettings.update { $0.provider = .deepseek }
        check(NagramiXTranslationSettings.current.revision == revision, "no-op update does not invalidate cache")
        NagramiXTranslationSettings.credentialsChanged()
        check(NagramiXTranslationSettings.current.revision != revision, "key changes invalidate previous provider cache")
        let a = NagramiXTranslationSettings.chatKey(account: 1, peer: 42, thread: nil)
        let b = NagramiXTranslationSettings.chatKey(account: 2, peer: 42, thread: nil)
        let c = NagramiXTranslationSettings.chatKey(account: 1, peer: 42, thread: 0)
        let d = NagramiXTranslationSettings.chatKey(account: 1, peer: 42, thread: 12)
        check(Set([a,b,c,d]).count == 4, "account, peer and nil/zero/topic scopes are distinct")
        NagramiXTranslationSettings.updateChat(a) { $0.enabled = false; $0.hidden = true; $0.target = "ja" }
        check(NagramiXTranslationSettings.chat(a).enabled == false && NagramiXTranslationSettings.chat(a).hidden, "explicit chat OFF and hidden persist")
        check(NagramiXTranslationSettings.chat(b).enabled == nil && NagramiXTranslationSettings.chat(c).target == nil, "chat choices never leak into another account/topic")
        NagramiXTranslationSettings.revealPanels()
        check(!NagramiXTranslationSettings.chat(a).hidden && NagramiXTranslationSettings.chat(a).enabled == false, "revealing a panel does not enable translation")
        NagramiXTranslationSettings.update { $0.enabled = false }
        check(NagramiXTranslationSettings.current.target == "de" && NagramiXTranslationSettings.chat(a).target == "ja", "master OFF retains choices")
        let saved = try JSONEncoder().encode(NagramiXTranslationSettings.current)
        check(try JSONDecoder().decode(NagramiXTranslationConfiguration.self, from: saved) == NagramiXTranslationSettings.current, "configuration JSON roundtrip")
        for code in ["ru", "ru-RU", "ru-raw", "RU_ru"] {
            check(NagramiXTranslationLanguage.accepted([("ru", 0.99)], interface: code, ignored: []) == nil, "app language suppresses translate action")
            check(NagramiXTranslationLanguage.accepted([("en", 0.99)], interface: code, ignored: []) == "en", "foreign language allows translate action")
        }
        check(NagramiXTranslationLanguage.accepted([("en", 0.99)], interface: "en-GB", ignored: []) == nil, "English UI suppresses English regardless of device locale")
        for hypotheses in [[("en",0.5)], [("en",0.7),("fr",0.6)], [("und",1.0)], [("en",Double.nan)], []] {
            check(NagramiXTranslationLanguage.accepted(hypotheses, interface: "ru", ignored: []) == nil, "uncertain/ambiguous recognition stays hidden")
        }
        check(NagramiXTranslationLanguage.accepted([("en",1.0)], interface: "ru", ignored: ["en-US"]) == nil, "ignored language variants normalized")
        check(NagramiXTranslationLanguage.base("nb-NO") == "no", "Norwegian normalization")
        check(NagramiXTranslationLanguage.badge("en-US") == "ENG" && NagramiXTranslationLanguage.badge("auto") == "АВТО", "source badge does not invent English for mixed text")
        check(NagramiXTranslationLanguage.title("ru", interface: "ru") == "Русский", "capitalized target language")
        for text in ["🙂🔥", "12345", "https://example.com/hello", "www.example.com", "t.me/example", "example.com/a", "user@example.com", "@example #hello", "   "] {
            check(NagramiXTranslationLanguage.recognitionText(text).isEmpty, "emoji/number/link/handle-only message has no translate action: " + text)
        }
        check(NagramiXTranslationLanguage.recognitionText("Read this https://example.com").contains("Read this"), "real prose remains recognizable")
        try self.textPlans()
        try self.codecs()
        try self.client()
        print("PASS: \(self.checks) translation persistence/policy/UTF16/format/provider/HTTP/cache/cancel checks; Apple ML, Keychain, UIKit and live paid APIs are boundaries")
    }
    static func textPlans() throws {
        let source = "🙂 Hello bold world https://example.com @alex"
        let ns = source as NSString
        let bold = ns.range(of: "bold world"), link = ns.range(of: "https://example.com"), mention = ns.range(of: "@alex")
        let spans = [NagramiXTranslationSpan(range: bold.location ..< NSMaxRange(bold), protected: false),
                     NagramiXTranslationSpan(range: link.location ..< NSMaxRange(link), protected: true),
                     NagramiXTranslationSpan(range: mention.location ..< NSMaxRange(mention), protected: true)]
        let plan = try NagramiXTranslationTextPlan(text: source, spans: spans)
        check(plan.texts.count == 2 && !plan.texts.joined().contains("example.com") && !plan.texts.joined().contains("@alex"), "protected fragments never sent to cloud")
        let (text, ranges) = try plan.restore(["🙂 Привет", "жирный текст"])
        check(text == "🙂 Привет жирный текст https://example.com @alex", "translated content retains whitespace, emoji and protected bytes")
        check((text as NSString).substring(with: NSRange(location: ranges[0].lowerBound, length: ranges[0].count)) == "жирный текст", "UTF16 bold range follows changed target length")
        check((text as NSString).substring(with: NSRange(location: ranges[1].lowerBound, length: ranges[1].count)) == "https://example.com", "URL range remains exact")
        for end in [1, 3, 4] {
            rejects("surrogate or out-of-bounds entity rejected") { _ = try NagramiXTranslationTextPlan(text: "🙂", spans: [NagramiXTranslationSpan(range: 0 ..< end, protected: false)]) }
        }
        rejects("negative entity range rejected") { _ = try NagramiXTranslationTextPlan(text: "Hello", spans: [NagramiXTranslationSpan(range: -1 ..< 3, protected: false)]) }
        rejects("truncated translation cannot overwrite original") { _ = try plan.restore(["one"]) }
        rejects("empty result cannot overwrite original") { _ = try plan.restore(["", "two"]) }
        for phrase in ["Hello", "你好世界", "مرحبا بكم", "Καλημέρα", "👩🏽‍💻 Hello\nworld", "e\u{301}clair"] {
            let length = phrase.utf16.count
            let value = try NagramiXTranslationTextPlan(text: phrase, spans: [NagramiXTranslationSpan(range: 0 ..< length, protected: false)])
            let restored = try value.restore(["Перевод"])
            check(restored.0 == "Перевод" && restored.1 == [0 ..< 7], "formatting reindexed for Unicode scripts")
        }
        let code = try NagramiXTranslationTextPlan(text: "hello()", spans: [NagramiXTranslationSpan(range: 0 ..< 7, protected: true)])
        let restoredCode = try code.restore([]).0
        check(code.texts.isEmpty && restoredCode == "hello()", "protected code is kept local")
        let bare = try NagramiXTranslationTextPlan(text: "Read t.me/example and @alex", spans: [])
        check(bare.texts == ["Read", "and"], "bare links and handles protected without server entities")
        let restoredBare = try bare.restore(["Читайте", "и"])
        check(restoredBare.0 == "Читайте t.me/example и @alex", "bare links survive reconstruction byte for byte")
        let nested = try NagramiXTranslationTextPlan(text: "Hello world", spans: [.init(range: 0 ..< 11, protected: false), .init(range: 6 ..< 11, protected: false)])
        let changed = try nested.restore(["Привет", "мир"])
        check(changed.0 == "Привет мир" && changed.1 == [0 ..< 10, 7 ..< 10], "nested styles retain their boundaries")
        rejects("oversized input rejected") { _ = try NagramiXTranslationTextPlan(text: String(repeating: "x", count: 32769), spans: []) }
    }
    static func codecs() throws {
        let credential = NagramiXTranslationCredential(key: "test-owned-key", folder: "test-folder")
        for provider in NagramiXTranslationProvider.allCases.filter({ $0 != .apple }) {
            let request = try NagramiXTranslationCloudCodec.request(provider: provider, credential: credential, model: provider.defaultModel, texts: ["Hello", "World"], source: "en", target: "ru")
            check(request.httpMethod == "POST" && request.url?.scheme == "https", "official HTTPS POST: " + provider.rawValue)
            let hosts: [NagramiXTranslationProvider:String] = [.google:"translation.googleapis.com", .yandex:"translate.api.cloud.yandex.net", .gemini:"generativelanguage.googleapis.com", .chatgpt:"api.openai.com", .deepseek:"api.deepseek.com"]
            check(request.url?.host == hosts[provider], "selected provider gets its own endpoint and key")
            check(request.url?.query == nil && !request.url!.absoluteString.contains(credential.key), "token/text never placed in URL")
            let header = provider == .google || provider == .gemini ? request.value(forHTTPHeaderField: "x-goog-api-key") : request.value(forHTTPHeaderField: "Authorization")
            check(header?.contains(credential.key) == true, "user's exact API key selected")
            check(String(data: request.httpBody!, encoding: .utf8)?.contains(credential.key) == false, "key absent from prompt/body")
            let body = try JSONSerialization.jsonObject(with: request.httpBody!) as! [String: Any]
            switch provider {
            case .google: check(body["format"] as? String == "text" && body["q"] as? [String] == ["Hello","World"], "Google documented text batch")
            case .yandex: check(body["folderId"] as? String == "test-folder" && body["targetLanguageCode"] as? String == "ru", "Yandex key and folder routed")
            case .gemini: check(body["systemInstruction"] != nil && request.url!.absoluteString.contains(provider.defaultModel), "Gemini model and instructions separate from user data")
            case .chatgpt: check(body["store"] as? Bool == false && body["model"] as? String == provider.defaultModel, "OpenAI storage disabled and selected model used")
            case .deepseek: check((body["thinking"] as? [String:String])?["type"] == "disabled", "DeepSeek uses bounded non-thinking translation")
            default: break
            }
            for status in [301, 400, 401, 402, 403, 429, 500] {
                rejects("HTTP failure rejected: \(status)") { _ = try NagramiXTranslationCloudCodec.response(provider: provider, status: status, data: json([:]), count: 2) }
            }
            rejects("missing key is not treated as free cloud API") { _ = try NagramiXTranslationCloudCodec.request(provider: provider, credential: .init(key: "", folder: ""), model: provider.defaultModel, texts: ["Hello"], source: "en", target: "ru") }
            rejects("header injection rejected") { _ = try NagramiXTranslationCloudCodec.request(provider: provider, credential: .init(key: "token\r\nOther: injected", folder: "x"), model: provider.defaultModel, texts: ["Hello"], source: "en", target: "ru") }
        }
        let google = json(["data":["translations":[["translatedText":"Tom &amp; Jerry &#39; &#x1F642; &amp;amp;"]]]])
        check(try NagramiXTranslationCloudCodec.response(provider: .google, status: 200, data: google, count: 1) == ["Tom & Jerry ' 🙂 &amp;"], "Google entities decoded once with Unicode support")
        check(try NagramiXTranslationCloudCodec.response(provider: .yandex, status: 200, data: json(["translations":[["text":"Привет"]]]), count: 1) == ["Привет"], "Yandex response parsed")
        let payload = String(data: json(["translations":["Привет","Мир"]]), encoding: .utf8)!
        for provider in [NagramiXTranslationProvider.chatgpt,.deepseek] {
            let response = json(["choices":[["finish_reason":"stop","message":["content":payload]]]])
            check(try NagramiXTranslationCloudCodec.response(provider: provider, status: 200, data: response, count: 2) == ["Привет","Мир"], "LLM JSON parsed in source order")
            rejects("truncated LLM output rejected") { _ = try NagramiXTranslationCloudCodec.response(provider: provider, status: 200, data: json(["choices":[["finish_reason":"length","message":["content":payload]]]]), count: 2) }
            rejects("missing translation element rejected") { _ = try NagramiXTranslationCloudCodec.response(provider: provider, status: 200, data: response, count: 3) }
        }
        let gemini = json(["candidates":[["finishReason":"STOP","content":["parts":[["text":"private thought", "thought":true], ["text":payload]]]]]])
        check(try NagramiXTranslationCloudCodec.response(provider: .gemini, status: 200, data: gemini, count: 2) == ["Привет","Мир"], "Gemini ignores thought parts")
        rejects("arbitrary model path rejected") { _ = try NagramiXTranslationCloudCodec.request(provider: .gemini, credential: credential, model: "../../evil?key=x", texts: ["Hello"], source: "en", target: "ru") }
    }
    static func client() throws {
        let configuration = URLSessionConfiguration.ephemeral; configuration.protocolClasses = [TranslationMockURLProtocol.self]
        let session = URLSession(configuration: configuration)
        let client = NagramiXTranslationCloudClient(session: session)
        let request = try NagramiXTranslationCloudCodec.request(provider: .google, credential: .init(key: "test-key", folder: ""), model: "", texts: ["Hello"], source: "en", target: "ru")
        let group = DispatchGroup()
        for _ in 0 ..< 8 {
            group.enter()
            _ = client.translate(request: request, provider: .google, count: 1, scope: "account-1:revision-1") { result in
                if case let .success(value) = result { check(value == ["Привет"], "coalesced subscribers get complete response") }
                else { check(false, "mock request failed") }
                group.leave()
            }
        }
        check(group.wait(timeout: .now() + 5) == .success, "coalesced HTTP completion")
        check(TranslationMockURLProtocol.requestCount == 1, "identical work coalesces into one request")
        group.enter()
        _ = client.translate(request: request, provider: .google, count: 1, scope: "account-1:revision-1") { _ in group.leave() }
        check(group.wait(timeout: .now() + 5) == .success && TranslationMockURLProtocol.requestCount == 1, "memory cache avoids repeated cloud charge")
        for scope in ["account-2:revision-1", "account-1:revision-2"] {
            group.enter(); _ = client.translate(request: request, provider: .google, count: 1, scope: scope) { _ in group.leave() }
        }
        check(group.wait(timeout: .now() + 5) == .success && TranslationMockURLProtocol.requestCount == 3, "cache isolated by account and credential revision")
        group.enter()
        _ = client.translate(request: request, provider: .google, count: 1, scope: "not-allowed", allowed: { false }) { result in
            if case .failure(.cancelled) = result { check(true, "revoked request rejected before transmission") }
            else { check(false, "revoked request must not translate") }
            group.leave()
        }
        check(group.wait(timeout: .now() + 5) == .success && TranslationMockURLProtocol.requestCount == 3, "revoked work makes no network request")
        let cancelled = DispatchSemaphore(value: 0)
        let cancel = client.translate(request: request, provider: .google, count: 1, scope: "cancelled-scope") { _ in cancelled.signal() }
        cancel()
        check(cancelled.wait(timeout: .now() + 0.3) == .timedOut, "canceled request cannot deliver stale result")
        session.invalidateAndCancel()
    }
}

final class TranslationMockURLProtocol: URLProtocol {
    private static let lock = NSLock()
    private static var count = 0
    static var requestCount: Int { self.lock.lock(); defer { self.lock.unlock() }; return self.count }
    private var stopped = false
    private let lock = NSLock()
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        Self.lock.lock(); Self.count += 1; Self.lock.unlock()
        DispatchQueue.global().asyncAfter(deadline: .now() + 0.06) {
            self.lock.lock(); defer { self.lock.unlock() }
            guard !self.stopped else { return }
            let data = TranslationCoreTests.json(["data":["translations":[["translatedText":"Привет"]]]])
            self.client?.urlProtocol(self, didReceive: HTTPURLResponse(url: self.request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, cacheStoragePolicy: .notAllowed)
            self.client?.urlProtocol(self, didLoad: data); self.client?.urlProtocolDidFinishLoading(self)
        }
    }
    override func stopLoading() { self.lock.lock(); self.stopped = true; self.lock.unlock() }
}
