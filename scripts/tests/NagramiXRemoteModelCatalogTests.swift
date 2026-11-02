import Foundation

func parse(_ provider: String, _ speech: Bool, _ object: [String: Any]) -> [String] {
    guard let result = NagramiXRemoteModelCatalog.parse(provider: provider, speech: speech, root: object) else { fatalError("Invalid fixture") }
    return result.models
}
let gemini: [String: Any] = ["models": [
    ["name": "models/gemini-3.1-flash-lite", "supportedGenerationMethods": ["generateContent"]],
    ["name": "models/gemini-tts", "supportedGenerationMethods": ["generateContent"]],
    ["name": "models/gemini-embedding", "supportedGenerationMethods": ["embedContent"]]
], "nextPageToken": "next"]
assert(parse("gemini", false, gemini) == ["gemini-3.1-flash-lite"])
assert(NagramiXRemoteModelCatalog.parse(provider: "gemini", speech: true, root: gemini)?.nextToken == "next")
let openai: [String: Any] = ["data": [["id": "gpt-transcribe"], ["id": "gpt-4o-mini"], ["id": "gpt-realtime-whisper"], ["id": "gpt-shutdown", "shutdown_date": "2000-01-01"]]]
assert(parse("chatgpt", true, openai) == ["gpt-transcribe"])
assert(parse("chatgpt", false, openai) == ["gpt-4o-mini"])
let cf: [String: Any] = ["success": true, "result": [["name": "@cf/openai/whisper"], ["name": "@cf/openai/whisper-large-v3-turbo"], ["name": "@cf/other/whisper"]]]
assert(parse("cloudflare", true, cf) == ["whisper", "whisper-large-v3-turbo"])
if let _ = NagramiXRemoteModelCatalog.parse(provider: "cloudflare", speech: true, root: ["success": false, "result": []]) { fatalError("Invalid Cloudflare response accepted") }
let deepseek: [String: Any] = ["data": [["id": "deepseek-flash", "input_modalities": ["text"], "output_modalities": ["text"]], ["id": "image", "input_modalities": ["image"]]]]
assert(parse("deepseek", false, deepseek) == ["deepseek-flash"])
print("Проверка обработки каталогов моделей пройдена")
