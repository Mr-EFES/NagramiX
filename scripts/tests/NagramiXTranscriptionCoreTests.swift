import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

private var checks = 0
private func check(_ condition: @autoclosure () throws -> Bool, _ label: String) rethrows {
    checks += 1; if try !condition() { fatalError(label) }
}
private func failure(_ error: NagramiXTranscriptionFailure, _ body: () throws -> Void) {
    do { try body(); fatalError("Expected \(error)") } catch let found as NagramiXTranscriptionFailure { check(found == error, "Failure \(found) != \(error)") } catch { fatalError("Unexpected error") }
}
private func wait(_ semaphore: DispatchSemaphore) { check(semaphore.wait(timeout: .now() + 5) == .success, "Timed out") }

@main struct TranscriptionCoreTests {
    static func main() throws {
        let defaults = NagramiXTranscriptionConfiguration()
        check(!defaults.enabled && !defaults.automatic, "Fresh defaults OFF")
        check(NagramiXTranscriptionProvider.allCases.map(\.title) == ["Apple", "Whisper", "Groq", "Gemini", "ChatGPT", "Telegram"], "Real recognizers only")
        check(NagramiXTranscriptionProvider.allCases.filter(\.cloud) == [.groq,.gemini,.chatgpt], "Cloud boundary")
        check(NagramiXWhisperModel.allCases.allSatisfy { $0.sha256.count == 64 && $0.size > 50_000_000 && !$0.fileName.contains(".en") }, "Multilingual immutable models")
        var config = defaults; config.enabled = true
        let tag = config.cacheTag; config.automatic = true; config.revision = "changed"
        check(config.cacheTag == tag, "Switches do not spend paid quota again")
        config.language = "en-US"; check(config.cacheTag != tag, "Language invalidates cache")
        try check(try JSONDecoder().decode(NagramiXTranscriptionConfiguration.self, from: JSONEncoder().encode(config)) == config, "Settings persistence")
        let audio = Data([0,1,2,3])
        for provider in [NagramiXTranscriptionProvider.groq,.gemini,.chatgpt] {
            config.provider = provider; config.models = [:]; config.cloudAllowed = [:]
            failure(.cloudPermission) { _ = try NagramiXTranscriptionCloudCodec.request(configuration: config, key: "owned", audio: audio) }
            config.cloudAllowed[provider.rawValue] = true
            failure(.missingKey) { _ = try NagramiXTranscriptionCloudCodec.request(configuration: config, key: "", audio: audio) }
            failure(.authorization) { _ = try NagramiXTranscriptionCloudCodec.request(configuration: config, key: "key\r\nheader", audio: audio) }
            failure(.tooLarge) { _ = try NagramiXTranscriptionCloudCodec.request(configuration: config, key: "owned", audio: Data()) }
            let request = try NagramiXTranscriptionCloudCodec.request(configuration: config, key: "owned-SECRET", audio: audio)
            check(request.httpMethod == "POST" && request.url?.scheme == "https" && request.url?.query == nil, "Fixed POST endpoints")
            check(!request.url!.absoluteString.contains("SECRET"), "Key never in URL")
            if provider == .gemini {
                check(request.url!.host == "generativelanguage.googleapis.com", "Google fixed host")
                check(request.value(forHTTPHeaderField: "x-goog-api-key") == "owned-SECRET", "Own Google key")
                let body = try JSONSerialization.jsonObject(with: request.httpBody!) as! [String:Any]
                let contents = body["contents"] as! [[String:Any]]
                let parts = contents[0]["parts"] as! [[String:Any]]
                let inline = parts[0]["inlineData"] as! [String:Any]
                check(inline["mimeType"] as? String == "audio/m4a", "Official Gemini MIME")
                check(inline["data"] as? String == audio.base64EncodedString(), "Actual audio bytes")
                check(body["temperature"] == nil, "No fake ASR quality slider")
            } else {
                check(request.url!.host == (provider == .groq ? "api.groq.com" : "api.openai.com"), "Provider fixed host")
                check(request.value(forHTTPHeaderField: "Authorization") == "Bearer owned-SECRET", "Own provider key")
                let body = String(decoding: request.httpBody!, as: UTF8.self)
                check(body.contains(provider.defaultModel) && body.contains("audio.m4a"), "Dedicated audio model")
                check(body.contains("name=\"language\"") && body.contains("en\r\n"), "Base language")
            }
            config.language = "auto"
            let automatic = try NagramiXTranscriptionCloudCodec.request(configuration: config, key: "owned", audio: audio)
            check(!String(decoding: automatic.httpBody!, as: UTF8.self).contains("name=\"language\""), "Auto language")
            config.models[provider.rawValue] = "https://attacker/model"
            failure(.invalidResponse) { _ = try NagramiXTranscriptionCloudCodec.request(configuration: config, key: "owned", audio: audio) }
            config.models = [:]; config.language = "en\r\n"
            failure(.language) { _ = try NagramiXTranscriptionCloudCodec.request(configuration: config, key: "owned", audio: audio) }
            config.language = "en-US"
        }
        for status in [401,403] { failure(.authorization) { _ = try NagramiXTranscriptionCloudCodec.response(provider:.groq, status:status, data:Data()) } }
        for status in [402,429] { failure(.quota) { _ = try NagramiXTranscriptionCloudCodec.response(provider:.groq, status:status, data:Data()) } }
        failure(.tooLarge) { _ = try NagramiXTranscriptionCloudCodec.response(provider:.groq,status:413,data:Data()) }
        failure(.network) { _ = try NagramiXTranscriptionCloudCodec.response(provider:.groq,status:500,data:Data()) }
        for provider in [NagramiXTranscriptionProvider.groq,.chatgpt] {
            try check(try NagramiXTranscriptionCloudCodec.response(provider:provider,status:200,data:Data("{\"text\":\" Привет! \"}".utf8)) == "Привет!", "Verbatim text")
            failure(.noSpeech) { _ = try NagramiXTranscriptionCloudCodec.response(provider:provider,status:200,data:Data("{\"text\":\" \"}".utf8)) }
            failure(.invalidResponse) { _ = try NagramiXTranscriptionCloudCodec.response(provider:provider,status:200,data:Data("{\"result\":\"wrong\"}".utf8)) }
        }
        let gemini: [String:Any] = ["candidates":[["finishReason":"STOP","content":["parts":[["thought":true,"text":"Do not leak reasoning"],["text":"{\"text\":\"Дословно\"}"]]]]]]
        try check(try NagramiXTranscriptionCloudCodec.response(provider:.gemini,status:200,data:JSONSerialization.data(withJSONObject:gemini)) == "Дословно", "Gemini structured result excludes thoughts")
        failure(.invalidResponse) { _ = try NagramiXTranscriptionCloudCodec.response(provider:.gemini,status:200,data:Data("{\"candidates\":[{\"finishReason\":\"MAX_TOKENS\"}]}".utf8)) }
        let cancellation = NagramiXTranscriptionCancellation(); var count = 0
        cancellation.add { count += 1 }; cancellation.cancel(); cancellation.cancel(); cancellation.add { count += 1 }
        check(cancellation.cancelled && count == 2, "Idempotent cancellation / late registration")
        self.coordinator()
        print("PASS: \(checks) transcription policy / cloud / cancellation / queue checks")
    }
    static func coordinator() {
        NagramiXTranscriptionSettings.update { $0 = .init(); $0.enabled = true }
        let config = NagramiXTranscriptionSettings.current; let coordinator = NagramiXTranscriptionCoordinator()
        let started = DispatchSemaphore(value:0); let returned = DispatchSemaphore(value:0); let second = DispatchSemaphore(value:0)
        let lock = NSLock(); var finish: ((Result<String,NagramiXTranscriptionFailure>) -> Void)?; var workers = 0
        let first = coordinator.request(key:"same",configuration:config,automatic:false,work:{ token, done in
            lock.lock(); workers += 1; finish = done; lock.unlock(); started.signal()
            token.add { returned.signal() }
        },completion:{ _ in fatalError("Disposed listener called") })
        wait(started)
        let shared = coordinator.request(key:"same",configuration:config,automatic:false,work:{ _,_ in fatalError("Duplicate work") },completion:{ result in
            if case .success("done") = result { second.signal() } else { fatalError("Wrong shared result") }
        })
        first.cancel()
        // A serial barrier request ensures coalescing was enqueued before completion.
        let queued = coordinator.request(key:"next",configuration:config,automatic:false,work:{ _, done in started.signal(); done(.success("next")) },completion:{ _ in returned.signal() })
        lock.lock(); let callback = finish; lock.unlock(); callback?(.success("done"))
        wait(second); wait(started); wait(returned)
        lock.lock(); check(workers == 1,"Coalesced worker"); lock.unlock()
        shared.cancel(); queued.cancel()
        let cancelStart = DispatchSemaphore(value:0); let cancelAck = DispatchSemaphore(value:0); let nextStart = DispatchSemaphore(value:0)
        var physicalFinish: ((Result<String,NagramiXTranscriptionFailure>) -> Void)?
        let active = coordinator.request(key:"slow",configuration:config,automatic:false,work:{ token, done in
            physicalFinish = done; token.add { cancelAck.signal() }; cancelStart.signal()
        },completion:{ _ in fatalError("Canceled slow listener called") })
        wait(cancelStart)
        let next = coordinator.request(key:"after-slow",configuration:config,automatic:false,work:{ _,done in nextStart.signal(); done(.success("ok")) },completion:{ _ in })
        active.cancel(); wait(cancelAck)
        check(nextStart.wait(timeout:.now()+0.1) == .timedOut,"Do not overlap canceled decoder")
        physicalFinish?(.failure(.cancelled)); wait(nextStart); next.cancel()
        NagramiXTranscriptionSettings.update { $0.enabled = false }
    }
}
