import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

// Anonymous web interfaces, not the paid Cloud Translation APIs. No cookies,
// application key, account identifier or message text in URLs.
struct NagramiXTranslationWebPlan {
    struct Part {
        let input: Int
        let text: String
        let prefix: String
        let suffix: String
    }
    let parts: [Part]
    let requests: [URLRequest]
    let count: Int

    init(provider: NagramiXTranslationProvider, texts: [String], source: String, target: String) throws {
        guard provider.isFreeWeb, !texts.isEmpty, texts.count <= 64,
              texts.reduce(0, { $0 + $1.utf8.count }) <= 24000 else { throw NagramiXTranslationFailure.tooLarge }
        var parts: [Part] = []
        for (index, text) in texts.enumerated() {
            guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { throw NagramiXTranslationFailure.invalidText }
            // Split at grapheme boundaries; prefer a word boundary near the end.
            var remaining = text[...]
            while !remaining.isEmpty {
                var end = remaining.startIndex, size = 0, boundary: String.Index?
                while end < remaining.endIndex {
                    let next = remaining.index(after: end)
                    let character = remaining[end ..< next]
                    if size + character.utf8.count > 3500 { break }
                    size += character.utf8.count; end = next
                    if size >= 2000, character.allSatisfy({ $0.isWhitespace }) { boundary = end }
                }
                guard end != remaining.startIndex else { throw NagramiXTranslationFailure.tooLarge }
                if end != remaining.endIndex, let boundary { end = boundary }
                let chunk = String(remaining[..<end]); remaining = remaining[end...]
                let prefix = String(chunk.prefix(while: { $0.isWhitespace }))
                let suffix = String(chunk.dropFirst(prefix.count).reversed().prefix(while: { $0.isWhitespace }).reversed())
                let content = String(chunk.dropFirst(prefix.count).dropLast(suffix.count))
                if content.isEmpty {
                    // Whitespace belongs to the preceding part, never to a request.
                    guard let last = parts.popLast(), last.input == index else { throw NagramiXTranslationFailure.invalidText }
                    parts.append(Part(input: index, text: last.text, prefix: last.prefix, suffix: last.suffix + chunk))
                } else { parts.append(Part(input: index, text: content, prefix: prefix, suffix: suffix)) }
            }
        }
        guard parts.count <= 96 else { throw NagramiXTranslationFailure.tooLarge }
        self.parts = parts; self.count = texts.count
        self.requests = try parts.map { try NagramiXTranslationWebCodec.request(provider: provider, text: $0.text, source: source, target: target) }
    }
    func restore(_ values: [String]) throws -> [String] {
        guard values.count == self.parts.count else { throw NagramiXTranslationFailure.invalidResponse }
        var result = Array(repeating: "", count: self.count)
        for (part, value) in zip(self.parts, values) {
            guard !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { throw NagramiXTranslationFailure.invalidResponse }
            result[part.input] += part.prefix + value + part.suffix
        }
        return result
    }
}

enum NagramiXTranslationWebCodec {
    static let yandexPage = URL(string: "https://translate.yandex.com/")!
    static func form(_ values: [(String, String)]) -> Data {
        let allowed = CharacterSet.alphanumerics.intersection(CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")).union(CharacterSet(charactersIn: "-._~"))
        return Data(values.map { key, value in
            (key.addingPercentEncoding(withAllowedCharacters: allowed) ?? "") + "=" + (value.addingPercentEncoding(withAllowedCharacters: allowed) ?? "")
        }.joined(separator: "&").utf8)
    }
    static func request(provider: NagramiXTranslationProvider, text: String, source: String, target: String) throws -> URLRequest {
        func valid(_ code: String) -> Bool { code.range(of: "^[A-Za-z]{2,3}(?:-[A-Za-z]{2,8})?$", options: .regularExpression) != nil }
        guard valid(target), source == "auto" || valid(source), !text.isEmpty, text.utf8.count <= 3500 else { throw NagramiXTranslationFailure.invalidText }
        var url: URLComponents
        switch provider {
        case .google:
            url = URLComponents(string: "https://translate.googleapis.com/translate_a/single")!
            url.queryItems = [URLQueryItem(name: "client", value: "gtx"), URLQueryItem(name: "sl", value: source), URLQueryItem(name: "tl", value: target), URLQueryItem(name: "dt", value: "t")]
        case .yandex:
            url = URLComponents(string: "https://translate.yandex.net/api/v1/tr.json/translate")!
            url.queryItems = [URLQueryItem(name: "srv", value: "tr-text"), URLQueryItem(name: "lang", value: source == "auto" ? target : source + "-" + target), URLQueryItem(name: "reason", value: "auto"), URLQueryItem(name: "format", value: "text")]
        default: throw NagramiXTranslationFailure.invalidText
        }
        guard let endpoint = url.url else { throw NagramiXTranslationFailure.invalidText }
        var request = URLRequest(url: endpoint, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 30)
        request.httpMethod = "POST"
        request.httpBody = self.form([(provider == .google ? "q" : "text", text)])
        request.setValue("application/x-www-form-urlencoded; charset=utf-8", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("Mozilla/5.0", forHTTPHeaderField: "User-Agent")
        if provider == .yandex {
            request.setValue("https://translate.yandex.com", forHTTPHeaderField: "Origin")
            request.setValue(self.yandexPage.absoluteString, forHTTPHeaderField: "Referer")
        }
        return request
    }
    static func session(data: Data, status: Int) throws -> String {
        guard status == 200 else { throw NagramiXTranslationFailure.webUnavailable }
        guard data.count <= 2_000_000, let html = String(data: data, encoding: .utf8) else { throw NagramiXTranslationFailure.invalidResponse }
        let pattern = "[\"']SID[\"']\\s*:\\s*[\"']([A-Za-z0-9]+(?:\\.[A-Za-z0-9]+){2,3})[\"']"
        guard let regex = try? NSRegularExpression(pattern: pattern), let match = regex.firstMatch(in: html, range: NSRange(location: 0, length: html.utf16.count)),
              let range = Range(match.range(at: 1), in: html), html[range].count <= 160 else { throw NagramiXTranslationFailure.webUnavailable }
        // The public website decodes its session ID by reversing each component.
        return html[range].split(separator: ".").map { String($0.reversed()) }.joined(separator: ".")
    }
    static func withSession(_ request: URLRequest, session: String, serial: Int) throws -> URLRequest {
        guard request.url?.host == "translate.yandex.net", var url = URLComponents(url: request.url!, resolvingAgainstBaseURL: false) else { throw NagramiXTranslationFailure.invalidText }
        var result = request
        url.queryItems = (url.queryItems ?? []).filter { $0.name != "id" } + [URLQueryItem(name: "id", value: session + "-\(serial)-0")]
        guard let endpoint = url.url else { throw NagramiXTranslationFailure.invalidText }
        result.url = endpoint; return result
    }
    static func response(provider: NagramiXTranslationProvider, status: Int, data: Data) throws -> String {
        if status == 429 || status == 402 { throw NagramiXTranslationFailure.quota }
        guard status == 200 else { throw NagramiXTranslationFailure.webUnavailable }
        guard data.count <= 2_000_000 else { throw NagramiXTranslationFailure.invalidResponse }
        let json: Any
        do { json = try JSONSerialization.jsonObject(with: data) } catch { throw NagramiXTranslationFailure.webUnavailable }
        let result: String
        switch provider {
        case .google:
            guard let root = json as? [Any], let blocks = root.first as? [Any], !blocks.isEmpty else { throw NagramiXTranslationFailure.invalidResponse }
            var values: [String] = []
            for block in blocks {
                guard let block = block as? [Any], let value = block.first as? String else { throw NagramiXTranslationFailure.invalidResponse }
                values.append(value)
            }
            result = values.joined()
        case .yandex:
            guard let root = json as? [String: Any] else { throw NagramiXTranslationFailure.invalidResponse }
            if [402, 404, 429].contains(root["code"] as? Int ?? 0) { throw NagramiXTranslationFailure.quota }
            guard root["code"] as? Int == 200, let values = root["text"] as? [String], values.count == 1 else { throw NagramiXTranslationFailure.webUnavailable }
            result = values[0]
        default: throw NagramiXTranslationFailure.invalidResponse
        }
        guard !result.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, result.utf16.count <= 65536 else { throw NagramiXTranslationFailure.invalidResponse }
        return result
    }
}
