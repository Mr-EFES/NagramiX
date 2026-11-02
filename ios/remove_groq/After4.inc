import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

// The provider catalogs do not share a capability schema. Only entries that can
// use our existing request formats are offered; the stored selection is untouched
// if catalog access fails.
enum NagramiXRemoteCatalogError: Error { case missingKey, invalidAccount, authorization, network, invalidResponse, noModels }

private final class NagramiXCatalogRedirectGuard: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) { completionHandler(nil) }
}

enum NagramiXRemoteModelCatalog {
    static func fetch(provider: String, speech: Bool, key: String, account: String = "", completion: @escaping (Result<[String], NagramiXRemoteCatalogError>) -> Void) {
        let key = key.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !key.isEmpty, key.utf8.count <= 4096, !key.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }) else { completion(.failure(.missingKey)); return }
        if provider == "grok" {
            // xAI's documented file-transcription endpoint currently exposes one model;
            // the separate language-model catalog is not a speech-model catalog.
            completion(.success(["grok-voice-transcribe-2.0"])); return
        }
        if provider == "cloudflare", account.range(of: "\\A[0-9a-fA-F]{32}\\z", options: .regularExpression) == nil { completion(.failure(.invalidAccount)); return }
        page(provider: provider, speech: speech, key: key, account: account, pageToken: nil, pageNumber: 1, accumulated: [], completion: completion)
    }

    private static func page(provider: String, speech: Bool, key: String, account: String, pageToken: String?, pageNumber: Int, accumulated: [String], completion: @escaping (Result<[String], NagramiXRemoteCatalogError>) -> Void) {
        let address: String
        switch provider {
        case "gemini": address = "https://generativelanguage.googleapis.com/v1beta/models"
        case "chatgpt": address = "https://api.openai.com/v1/models"
        case "deepseek": address = "https://api.deepseek.com/models"
        case "cloudflare": address = "https://api.cloudflare.com/client/v4/accounts/\(account)/ai/models/search"
        default: completion(.failure(.invalidResponse)); return
        }
        guard var components = URLComponents(string: address) else { completion(.failure(.invalidResponse)); return }
        if provider == "gemini" {
            var query = [URLQueryItem(name: "pageSize", value: "1000")]
            if let pageToken { query.append(URLQueryItem(name: "pageToken", value: pageToken)) }
            components.queryItems = query
        } else if provider == "cloudflare" {
            components.queryItems = [URLQueryItem(name: "search", value: "whisper"), URLQueryItem(name: "per_page", value: "100"), URLQueryItem(name: "page", value: String(pageNumber))]
        }
        guard let url = components.url else { completion(.failure(.invalidResponse)); return }
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 20)
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(provider == "gemini" ? key : "Bearer " + key, forHTTPHeaderField: provider == "gemini" ? "x-goog-api-key" : "Authorization")
        let session = URLSession(configuration: .ephemeral, delegate: NagramiXCatalogRedirectGuard(), delegateQueue: nil)
        session.dataTask(with: request) { data, response, error in
            defer { session.finishTasksAndInvalidate() }
            guard error == nil, let http = response as? HTTPURLResponse else { completion(.failure(.network)); return }
            guard http.statusCode == 200 else { completion(.failure(http.statusCode == 401 || http.statusCode == 403 ? .authorization : .network)); return }
            guard let data, data.count <= 2_000_000,
                  let root = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
                  let parsed = parse(provider: provider, speech: speech, root: root) else { completion(.failure(.invalidResponse)); return }
            let all = accumulated + parsed.models
            if let next = parsed.nextToken, !next.isEmpty {
                guard pageNumber < 20 else { completion(.failure(.invalidResponse)); return }
                page(provider: provider, speech: speech, key: key, account: account, pageToken: next, pageNumber: pageNumber + 1, accumulated: all, completion: completion); return
            }
            if provider == "cloudflare", parsed.count == 100 {
                guard pageNumber < 20 else { completion(.failure(.invalidResponse)); return }
                page(provider: provider, speech: speech, key: key, account: account, pageToken: nil, pageNumber: pageNumber + 1, accumulated: all, completion: completion); return
            }
            let models = Array(Set(all)).sorted { $0.localizedStandardCompare($1) == .orderedAscending }
            completion(models.isEmpty ? .failure(.noModels) : .success(models))
        }.resume()
    }

    static func parse(provider: String, speech: Bool, root: [String: Any]) -> (models: [String], nextToken: String?, count: Int)? {
        let rows: [[String: Any]]
        if provider == "gemini" { guard let list = root["models"] as? [[String: Any]] else { return nil }; rows = list }
        else if provider == "cloudflare" { guard root["success"] as? Bool == true, let list = root["result"] as? [[String: Any]] else { return nil }; rows = list }
        else { guard let list = root["data"] as? [[String: Any]] else { return nil }; rows = list }
        let now = ISO8601DateFormatter().string(from: Date()).prefix(10)
        let items = rows.compactMap { row -> String? in
            var id = (row[provider == "gemini" || provider == "cloudflare" ? "name" : "id"] as? String) ?? ""
            if provider == "gemini" {
                guard id.hasPrefix("models/"), let methods = row["supportedGenerationMethods"] as? [String], methods.contains("generateContent") else { return nil }
                id = String(id.dropFirst("models/".count))
                guard id.hasPrefix("gemini-"), !["-tts", "-image", "-live", "-robotics", "-computer", "-embedding"].contains(where: { id.contains($0) }) else { return nil }
            } else if provider == "cloudflare" {
                guard ["@cf/openai/whisper", "@cf/openai/whisper-large-v3-turbo"].contains(id) else { return nil }
                id = String(id.dropFirst("@cf/openai/".count))
            } else if provider == "chatgpt" {
                if let date = row["shutdown_date"] as? String, date <= String(now) { return nil }
                if speech { guard ["gpt-transcribe", "gpt-4o-transcribe", "gpt-4o-mini-transcribe", "gpt-4o-mini-transcribe-2025-12-15", "whisper-1"].contains(id) else { return nil } }
                else { guard (id.hasPrefix("gpt-") || id.hasPrefix("o1") || id.hasPrefix("o3") || id.hasPrefix("o4")), !["audio", "transcribe", "realtime", "tts", "image", "search", "embedding", "moderation", "instruct"].contains(where: { id.contains($0) }) else { return nil } }
            } else if provider == "deepseek" {
                if let inputs = row["input_modalities"] as? [String], !inputs.contains("text") { return nil }
                if let outputs = row["output_modalities"] as? [String], !outputs.contains("text") { return nil }
            }
            guard id.range(of: "\\A[A-Za-z0-9._:-]{1,128}\\z", options: .regularExpression) != nil else { return nil }
            return id
        }
        return (items, provider == "gemini" ? root["nextPageToken"] as? String : nil, rows.count)
    }
    static func message(_ error: NagramiXRemoteCatalogError) -> String {
        switch error {
        case .missingKey: return "Введите API-ключ, чтобы загрузить модели."
        case .invalidAccount: return "Введите корректный Account ID CloudFlare."
        case .authorization: return "Не удалось получить модели. Проверьте ключ и права доступа."
        case .network: return "Не удалось получить модели. Проверьте подключение и повторите попытку."
        case .invalidResponse: return "Не удалось прочитать список моделей. Попробуйте ещё раз."
        case .noModels: return "Нет доступных совместимых моделей для этого аккаунта."
        }
    }
}
