import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

@main
struct CloudflareTests {
    static func check(_ condition: @autoclosure () -> Bool, _ message: String) { if !condition() { fatalError(message) } }
    static func main() throws {
        var configuration = NagramiXTranscriptionConfiguration()
        configuration.provider = .cloudflare
        configuration.cloudAllowed["cloudflare"] = true
        let credential = NagramiXCloudflareTranscriptionCredential(token: "test-token", account: String(repeating: "a", count: 32))
        let key = String(data: try JSONEncoder().encode(credential), encoding: .utf8)!
        let audio = Data([1, 2, 3, 4])
        let request = try NagramiXTranscriptionCloudCodec.request(configuration: configuration, key: key, audio: audio)
        check(request.httpMethod == "POST", "POST only")
        check(request.url?.host == "api.cloudflare.com", "fixed host")
        check(request.url?.query == nil, "no audio/token in query")
        check(request.value(forHTTPHeaderField: "Authorization") == "Bearer test-token", "token not credential JSON")
        let body = try JSONSerialization.jsonObject(with: request.httpBody!) as! [String: Any]
        check(body["audio"] as? String == audio.base64EncodedString(), "audio body")
        check(body["task"] as? String == "transcribe", "no translation")
        check(body["language"] as? String == "ru", "language hint")
        let data = Data("{\"success\":true,\"result\":{\"text\":\"Привет\"}}".utf8)
        let text = try NagramiXTranscriptionCloudCodec.response(provider: .cloudflare, status: 200, data: data)
        check(text == "Привет", "Cloudflare envelope")
        for account in ["", "../../other", "https://other.test", String(repeating: "z", count: 32)] {
            check(!NagramiXCloudflareTranscriptionCredential(token: "x", account: account).valid, "reject invalid account")
        }
        check(!NagramiXCloudflareTranscriptionCredential(token: "x\r\nHeader: yes", account: credential.account).valid, "reject header injection")
        for status in [401,403,429,500] {
            do { _ = try NagramiXTranscriptionCloudCodec.response(provider: .cloudflare, status: status, data: data); fatalError("HTTP error accepted") }
            catch let error as NagramiXTranscriptionFailure {
                check(error == (status == 429 ? .quota : (status == 500 ? .network : .authorization)), "HTTP mapping")
            }
        }
        configuration.cloudAllowed["cloudflare"] = false
        do { _ = try NagramiXTranscriptionCloudCodec.request(configuration: configuration, key: key, audio: audio); fatalError("unauthorized upload") }
        catch let error as NagramiXTranscriptionFailure { check(error == .cloudPermission, "permission boundary") }
        print("PASS: Cloudflare codec and account credential boundaries")
    }
}
