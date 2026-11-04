import Foundation

private var checks = 0
private func check(_ value: @autoclosure () -> Bool, _ text: String) {
    checks += 1
    precondition(value(), text)
}
private func wait(_ semaphore: DispatchSemaphore) {
    check(semaphore.wait(timeout: .now() + 5) == .success, "Callback timeout")
}

@main struct TemporaryTranscriptionTests {
    static func main() throws {
        let context = AccountContext()
        let archive = NagramiXMessageArchive()
        NagramiXMessageArchive.registered = archive
        let defaults = UserDefaults.standard
        let keys = ["nagramix.messages.saveTemporaryMessages", "nagramix.messages.replayViewOnce"]
        defer { keys.forEach { defaults.removeObject(forKey: $0) }; NagramiXTranscriptionSettings.update { $0.enabled = false } }
        func enabled(_ value: Bool) { keys.forEach { defaults.set(value, forKey: $0) } }
        func configure(_ provider: NagramiXTranscriptionProvider = .apple, automatic: Bool = false) {
            NagramiXTranscriptionSettings.update {
                $0 = .init(); $0.enabled = true; $0.provider = provider; $0.automatic = automatic
                $0.cloudAllowed[provider.rawValue] = provider.cloud
            }
        }
        var serial: Int32 = 20
        func message(retained: Bool = false) -> Message {
            serial += 1
            let result = Message(MessageId(peerId: PeerId(value: 9), id: serial), TelegramMediaFile("voice-\(serial)"))
            if retained { result.attributes = [NagramiXArchivedMessageAttribute(isTemporary: true)] }
            else { result.minAutoremoveOrClearTimeout = viewOnceTimeout; result.containsSecretMedia = true; result.isSelfExpiring = true }
            return result
        }
        configure()
        for first in [false, true] {
            for second in [false, true] {
                defaults.set(first, forKey: keys[0]); defaults.set(second, forKey: keys[1])
                for retained in [false, true] {
                    let value = message(retained: retained)
                    check(NagramiXTranscriptionRuntime.handles(value) == (first || second), "Temporary switch OR, including retained row without TTL")
                    check(displayButton(value, premium: false) == (first || second), "Custom recognizer button without Premium")
                }
            }
        }
        enabled(true)
        let live = message()
        NagramiXTranscriptionSettings.update { $0.enabled = false }
        check(displayButton(live, premium: true), "Native Premium works without custom ASR master")
        check(!displayButton(live, premium: false), "View-once does not bypass Premium quota gate")
        check(!displayButton(message(retained: true), premium: true), "No server request button on an archive-only row")
        let completed = message(retained: true)
        completed.attributes.append(AudioTranscriptionMessageAttribute(id: 44, text: "Already recognized", isPending: false, didRate: false, error: nil))
        check(displayButton(completed, premium: false), "Existing retained text can be opened without a new Premium request")
        let nativeDecision = NativeTranscriptionDecision().decision(completed)
        check(!nativeDecision.request && nativeDecision.expand, "Actual native decision expands completed text without requesting the server")
        enabled(false)
        check(!displayButton(live, premium: true), "OFF keeps native view-once exclusion")
        check(!displayButton(completed, premium: true), "OFF hides retained transcription button as well")
        enabled(true); configure()
        check(!displayButton(live, premium: true, preview: true), "No transcription in preview")
        for failed in [MessageFlags.Sending, .Failed] {
            let value = message(); value.flags.insert(failed)
            check(NagramiXTranscriptionRuntime.file(value) == nil, "Pending/failed messages excluded")
        }
        let circle = message(); (circle.media[0] as! TelegramMediaFile).isInstantVideo = true
        check(NagramiXTranscriptionRuntime.file(circle) == nil, "No expansion to temporary round video")
        let scheduled = Message(MessageId(peerId: PeerId(value: 9), namespace: 1, id: 1), TelegramMediaFile("scheduled"))
        check(NagramiXTranscriptionRuntime.file(scheduled) == nil, "Scheduled excluded")
        let secret = Message(MessageId(peerId: PeerId(namespace: 2, value: 9), id: 1), TelegramMediaFile("secret"))
        check(NagramiXTranscriptionRuntime.file(secret) == nil, "Secret chat excluded")
        let codes = Message(MessageId(peerId: PeerId(value: 777000), id: 1), TelegramMediaFile("codes"))
        codes.minAutoremoveOrClearTimeout = viewOnceTimeout; codes.containsSecretMedia = true
        check(NagramiXTranscriptionRuntime.file(codes) == nil, "Verification-code chat excluded")
        let ordinary = Message(MessageId(peerId: PeerId(value: 9), id: 2), TelegramMediaFile("ordinary"))
        check(NagramiXTranscriptionRuntime.handles(ordinary), "Ordinary voice unchanged")
        ordinary.protected = true
        check(!NagramiXTranscriptionRuntime.handles(ordinary), "Ordinary protected media unchanged")

        try Data([1, 2, 3]).write(to: URL(fileURLWithPath: "/tmp/nagramix-asr-boundary-audio.m4a"))
        defer { try? FileManager.default.removeItem(atPath: "/tmp/nagramix-asr-boundary-audio.m4a") }
        func perform(_ value: Message, provider: NagramiXTranscriptionProvider = .apple, automatic: Bool = false,
                     mutation: () -> Void = {}, expected: NagramiXTranscriptionFailure? = nil) {
            configure(provider, automatic: automatic)
            let done = DispatchSemaphore(value: 0)
            var outcome: Result<String, NagramiXTranscriptionFailure>?
            let work = NagramiXTranscriptionRuntime.transcribe(context: context, messageId: value.id, automatic: automatic).start(next: { outcome = $0; done.signal() })
            wait(AudioBoundary.started)
            check(AudioBoundary.provider == provider, "Exact selected provider, no silent replacement")
            mutation()
            AudioBoundary.finish(.success("Recognized speech"))
            wait(done); work.dispose()
            if let expected {
                if case let .failure(error) = outcome { check(error == expected, "Expected failure") }
                else { preconditionFailure("Expected failure: \(expected)") }
            } else {
                if case .success("Recognized speech") = outcome { checks += 1 }
                else { preconditionFailure("Expected transcript") }
            }
        }
        let retained = message(retained: true)
        archive.put(retained)
        perform(retained)
        let resolved = archive.transcriptionMessage(id: retained.id, liveMessage: nil)!
        check(NagramiXTranscriptionRuntime.cached(resolved) == "Recognized speech", "Retained transcript and cache stamp rendered")
        check(context.account.postbox.store.messages[retained.id] == nil, "Retained result never recreates Postbox message")
        check(archive.persisted == 1, "Retained result persisted")
        check(context.engine.resources.fetches == 0, "Manual retained ASR reads local bytes without fetching a deleted server message")
        let preparations = NagramiXTranscriptionMedia.preparations
        let cacheDone = DispatchSemaphore(value: 0)
        let cacheJob = NagramiXTranscriptionRuntime.transcribe(context: context, messageId: retained.id).start(next: { _ in cacheDone.signal() })
        wait(cacheDone); cacheJob.dispose()
        check(NagramiXTranscriptionMedia.preparations == preparations, "Returning to chat reuses result")

        let mirrored = message()
        context.account.postbox.store.messages[mirrored.id] = mirrored
        archive.put(mirrored)
        perform(mirrored)
        let saved = archive.transcriptionMessage(id: mirrored.id, liveMessage: nil)!
        check((saved.media[0] as! TelegramMediaFile).resource.id != (mirrored.media[0] as! TelegramMediaFile).resource.id, "Fixture changes resource from cloud to archive")
        check(NagramiXTranscriptionRuntime.cached(saved) == "Recognized speech", "Stable file identity survives local retention")
        check(mirrored.minAutoremoveOrClearTimeout == viewOnceTimeout && mirrored.containsSecretMedia, "Original TTL and secret flags unchanged")
        check(saved.minAutoremoveOrClearTimeout == nil, "No real timer added to retained copy")
        let outgoing = message(); outgoing.flags = []
        context.account.postbox.store.messages[outgoing.id] = outgoing; archive.put(outgoing)
        perform(outgoing)
        check(NagramiXTranscriptionRuntime.cached(outgoing) == "Recognized speech", "Own delivered view-once voice can be transcribed manually")

        for provider in [NagramiXTranscriptionProvider.whisper, .vosk, .cloudflare, .gemini, .chatgpt, .grok] {
            let value = message(retained: true); archive.put(value); perform(value, provider: provider)
            check(NagramiXTranscriptionRuntime.cached(archive.transcriptionMessage(id: value.id, liveMessage: nil)!) != nil, "Provider result stored on retained voice")
        }
        let automatic = message(retained: true); archive.put(automatic)
        let fetches = context.engine.resources.fetches
        perform(automatic, automatic: true)
        check(context.engine.resources.fetches == fetches, "Automatic retained ASR never downloads audio")

        let cleared = message(retained: true); archive.put(cleared)
        perform(cleared, mutation: { archive.clearAll() }, expected: .cancelled)
        check(archive.transcriptionMessage(id: cleared.id, liveMessage: nil) == nil, "Late work cannot undo full archive clear")
        let switched = message(retained: true); archive.put(switched)
        perform(switched, mutation: { enabled(false) }, expected: .cancelled)
        enabled(true)
        check(NagramiXTranscriptionRuntime.cached(archive.transcriptionMessage(id: switched.id, liveMessage: nil)!) == nil, "OFF blocks late write to retained voice")
        let replaced = message(retained: true); archive.put(replaced)
        perform(replaced, mutation: { archive.records[replaced.id.descriptionKey]?.message.media = [TelegramMediaFile("different-file")] }, expected: .cancelled)
        let changed = message(); context.account.postbox.store.messages[changed.id] = changed; archive.put(changed)
        perform(changed, mutation: { changed.media = [TelegramMediaFile("different-live")] }, expected: .cancelled)
        check(NagramiXTranscriptionRuntime.cached(archive.transcriptionMessage(id: changed.id, liveMessage: nil)!) == nil, "Rejected live write cannot overwrite archive with stale source")
        let newer = message(retained: true); archive.put(newer)
        perform(newer, mutation: { archive.records[newer.id.descriptionKey]?.message.attributes.append(AudioTranscriptionMessageAttribute(id: 42, text: "Newer", isPending: false, didRate: false, error: nil)) }, expected: .cancelled)

        let expired = message(retained: true); archive.put(expired)
        let expiredLive = message()
        expiredLive.media = [TelegramMediaExpiredContent()]
        let persistedBeforeRead = archive.persisted
        let publishedBeforeRead = archive.publishCount
        let resolvedExpired = archive.transcriptionMessage(id: expired.id, liveMessage: nil)
        check(resolvedExpired?.id == expired.id, "Retained row resolved independently of live lookup")
        check(archive.transcriptionMessage(id: expired.id, liveMessage: expiredLive) == nil, "Mismatched IDs rejected")
        check(archive.persisted == persistedBeforeRead && archive.publishCount == publishedBeforeRead, "Resolution never marks expiration or mutates archive")
        context.engine.resources.complete = false
        var unavailable: Result<String, NagramiXTranscriptionFailure>?
        let unavailableDone = DispatchSemaphore(value: 0)
        let unavailableJob = NagramiXTranscriptionRuntime.transcribe(context: context, messageId: expired.id).start(next: { unavailable = $0; unavailableDone.signal() })
        wait(unavailableDone)
        if case .failure(.unavailableMedia) = unavailable { checks += 1 } else { preconditionFailure("Missing local bytes must fail without download") }
        unavailableJob.dispose(); context.engine.resources.complete = true

        // The record is the actual production Codable type; older archives did
        // not contain transcriptionAttributes and must continue to decode.
        let oldJSON = Data(#"{"peerId":9,"namespace":0,"id":1,"timestamp":10,"incoming":true,"peerData":{},"content":{"text":"caption","entities":[],"media":[]},"revisions":[]}"#.utf8)
        var oldRecord = try JSONDecoder().decode(NagramiXArchivedRecord.self, from: oldJSON)
        check(oldRecord.transcriptionAttributes == nil, "Old archive schema remains readable")
        oldRecord.transcriptionAttributes = [Data([1, 2, 3])]
        let roundTrip = try JSONDecoder().decode(NagramiXArchivedRecord.self, from: JSONEncoder().encode(oldRecord))
        check(roundTrip == oldRecord, "New optional transcription field survives Codable round trip")

        configure(.telegram); context.engine.data.premium = true
        let server = message(); context.account.postbox.store.messages[server.id] = server
        var serverOutcome: Result<String, NagramiXTranscriptionFailure>?
        NagramiXTranscriptionRuntime.toggleContext(context: context, messageId: server.id) { serverOutcome = $0 }
        check(context.engine.messages.nativeRequests == 1, "Premium uses native RPC")
        if case .success = serverOutcome { checks += 1 } else { preconditionFailure("Premium result") }
        context.engine.messages.nativeResult = .error
        NagramiXTranscriptionRuntime.toggleContext(context: context, messageId: server.id) { serverOutcome = $0 }
        if case .failure(.network) = serverOutcome { checks += 1 } else { preconditionFailure("Server refusal must remain an error") }
        check(context.engine.messages.nativeRequests == 2, "Error is not retried through a different provider")
        context.engine.data.premium = false
        NagramiXTranscriptionRuntime.toggleContext(context: context, messageId: server.id) { serverOutcome = $0 }
        if case .failure(.authorization) = serverOutcome { checks += 1 } else { preconditionFailure("Premium required") }
        check(context.engine.messages.nativeRequests == 2, "No unauthorized native request")
        context.engine.data.premium = true
        check(!NagramiXTranscriptionRuntime.handlesContext(retained), "Archive excluded from native server action")
        archive.put(retained)
        NagramiXTranscriptionRuntime.toggleContext(context: context, messageId: retained.id) { serverOutcome = $0 }
        if case .failure(.unavailableMedia) = serverOutcome { checks += 1 } else { preconditionFailure("Archive cannot be transcribed by server ID") }
        check(context.engine.messages.nativeRequests == 2, "Archive never uploaded or forwarded to Telegram")
        print("PASS: \(checks) temporary voice transcription checks; Speech/HTTP/Postbox/disk/UI are explicit boundaries")
    }
}
