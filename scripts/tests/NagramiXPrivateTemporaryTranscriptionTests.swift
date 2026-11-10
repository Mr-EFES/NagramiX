import Foundation

private var checks = 0
private func check(_ value: Bool, _ message: String) {
    checks += 1
    if !value {
        fputs("Private transcription regression: \(message)\n", stderr)
        exit(96)
    }
}

@main struct PrivateTemporaryTranscriptionTests {
    static let keys = ["nagramix.messages.saveTemporaryMessages", "nagramix.messages.replayViewOnce"]
    static var serial: Int32 = 100
    static func retained(_ enabled: Bool) { for key in keys { UserDefaults.standard.set(enabled, forKey: key) } }
    static func configure(_ provider: NagramiXTranscriptionProvider, enabled: Bool = true, automatic: Bool = false) {
        NagramiXTranscriptionSettings.update {
            $0 = .init(); $0.provider = provider; $0.enabled = enabled; $0.automatic = automatic
            $0.language = "en-US"; $0.localFallback = false
            $0.cloudAllowed[provider.rawValue] = provider.cloud
        }
    }
    static func message(round: Bool = false, ttl: Int32? = viewOnceTimeout, incoming: Bool = true, secret: Bool = false) -> Message {
        serial += 1
        let file = TelegramMediaFile("voice-\(serial)"); file.isVoice = !round; file.isInstantVideo = round
        let result = Message(MessageId(peerId: PeerId(namespace: secret ? Namespaces.Peer.SecretChat : Namespaces.Peer.CloudUser, value: 9), namespace: secret ? Namespaces.Message.SecretIncoming : Namespaces.Message.Cloud, id: serial), file)
        result.minAutoremoveOrClearTimeout = ttl; result.containsSecretMedia = ttl != nil; result.isSelfExpiring = ttl != nil
        result.flags = incoming ? [.Incoming] : []
        result.attributes.append(ConsumableContentMessageAttribute(consumed: false))
        return result
    }
    static func wait(_ semaphore: DispatchSemaphore, _ message: String) {
        check(semaphore.wait(timeout: .now() + 4) == .success, message)
    }
    static func recognize(_ context: AccountContext, message: Message, expectedProvider: NagramiXTranscriptionProvider, contextMenu: Bool = false,
                          mutation: (() -> Void)? = nil, outcome: Result<String, NagramiXTranscriptionFailure> = .success("Recognized locally"), expectedError: NagramiXTranscriptionFailure? = nil) {
        AudioBoundary.started = DispatchSemaphore(value: 0)
        let done = DispatchSemaphore(value: 0)
        var received: Result<String, NagramiXTranscriptionFailure>?
        var disposable: Disposable?
        if contextMenu {
            NagramiXTranscriptionRuntime.toggleContext(context: context, messageId: message.id) { received = $0; done.signal() }
        } else {
            disposable = NagramiXTranscriptionRuntime.transcribe(context: context, messageId: message.id).start(next: { received = $0; done.signal() })
        }
        wait(AudioBoundary.started, "safe recognizer starts")
        check(AudioBoundary.provider == expectedProvider, "recognizer preserves selected safe provider")
        mutation?()
        AudioBoundary.finish(outcome)
        wait(done, "recognizer finishes")
        if let expectedError {
            if case let .failure(error)? = received { check(error == expectedError, "failure propagated without server fallback") }
            else { check(false, "expected failed recognition") }
        } else {
            if case let .success(text)? = received { check(text == "Recognized locally", "recognition text stored") }
            else { check(false, "expected successful recognition") }
        }
        disposable?.dispose()
        check(context.account.network.transcriptions == 0 && context.account.network.rates == 0, "safe recognition sends no Telegram RPC")
    }
    static func unchangedLifetime(_ value: Message, file: TelegramMediaFile, ttl: Int32 = viewOnceTimeout) {
        check(value.media.first as? TelegramMediaFile === file, "ASR keeps original media object")
        check(value.minAutoremoveOrClearTimeout == ttl, "ASR preserves original TTL")
        let timers = value.attributes.compactMap { $0 as? AutoremoveTimeoutMessageAttribute }
        check(timers.count == 1 && timers.allSatisfy { $0.countdownBeginTime == nil }, "ASR never starts local countdown")
        let receipts = value.attributes.compactMap { $0 as? ConsumableContentMessageAttribute }
        check(receipts.count == 1 && receipts.allSatisfy { !$0.consumed }, "ASR never marks media consumed")
        check(!value.wasDeleted && !value.attributes.contains { $0 is NagramiXArchivedMessageAttribute }, "live media never becomes a deleted copy")
    }
    static func main() {
        let defaults = UserDefaults.standard
        let oldKeys = Dictionary(uniqueKeysWithValues: (keys + ["nagramix.messages.showDeletedMessages", "nagramix.transcription.configuration.v1"]).map { ($0, defaults.object(forKey: $0)) })
        defer { for (key, value) in oldKeys { if let value { defaults.set(value, forKey: key) } else { defaults.removeObject(forKey: key) } } }
        let audioPath = URL(fileURLWithPath: "/tmp/nagramix-asr-boundary-audio.m4a")
        try! Data([1,2,3,4]).write(to: audioPath)
        defer { try? FileManager.default.removeItem(at: audioPath) }
        defaults.set(true, forKey: "nagramix.messages.showDeletedMessages")
        let archive = NagramiXMessageArchive(); NagramiXMessageArchive.registered = archive
        defer { NagramiXMessageArchive.registered = nil }

        for round in [false, true] {
            for incoming in [false, true] {
                for provider in NagramiXTranscriptionProvider.allCases {
                    retained(true); configure(provider)
                    let context = AccountContext(), value = message(round: round, incoming: incoming)
                    let file = value.media[0] as! TelegramMediaFile
                    context.account.postbox.store.messages[value.id] = value
                    archive.put(value); archive.records[value.id.descriptionKey]?.deletedAt = nil
                    check(NagramiXTranscriptionRuntime.handles(value), "temporary voice and round always use safe route")
                    check(!NagramiXTranscriptionRuntime.canUseTelegram(value), "temporary source ID never eligible for Telegram ASR")
                    recognize(context, message: value, expectedProvider: provider == .telegram ? .apple : provider)
                    unchangedLifetime(value, file: file)
                    check(archive.records[value.id.descriptionKey]?.deletedAt == nil, "ASR never expires retained live record")
                    check(NagramiXTranscriptionRuntime.cached(value) == "Recognized locally", "private result cache uses effective provider")
                    check(NagramiXTranscriptionSettings.current.provider == provider, "safe route does not rewrite settings")
                }
            }
        }
        for round in [false, true] {
            retained(true); configure(.telegram, enabled: false)
            let context = AccountContext(), value = message(round: round)
            let file = value.media[0] as! TelegramMediaFile
            context.account.postbox.store.messages[value.id] = value
            check(NagramiXTranscriptionRuntime.handlesContext(value), "context menu retains private native-button fallback")
            recognize(context, message: value, expectedProvider: .apple, contextMenu: true)
            unchangedLifetime(value, file: file)
            check(!NagramiXTranscriptionSettings.current.enabled && NagramiXTranscriptionSettings.current.provider == .telegram, "manual fallback leaves disabled custom ASR untouched")
        }
        for round in [false, true] {
            retained(true); configure(.telegram)
            let context = AccountContext(), value = message(round: round, secret: true)
            context.account.postbox.store.messages[value.id] = value
            recognize(context, message: value, expectedProvider: .apple)
            unchangedLifetime(value, file: value.media[0] as! TelegramMediaFile)
        }
        for first in [false, true] {
            for second in [false, true] {
                configure(.telegram)
                defaults.set(first, forKey: keys[0]); defaults.set(second, forKey: keys[1])
                for round in [false, true] {
                    let context = AccountContext(), value = message(round: round)
                    context.account.postbox.store.messages[value.id] = value
                    var emitted = false
                    let d = _internal_transcribeAudio(postbox: context.account.postbox, network: context.account.network, messageId: value.id).start(next: { _ in emitted = true })
                    let rate = _internal_rateAudioTranscription(postbox: context.account.postbox, network: context.account.network, messageId: value.id, id: 99, isGood: true).start()
                    check(emitted, "core transcription returns a terminal result")
                    check(context.account.network.transcriptions == (first || second ? 0 : 1), "core blocks protected voice and round RPC")
                    check(context.account.network.rates == (first || second ? 0 : 1), "core blocks protected transcript rating RPC")
                    d.dispose(); rate.dispose()
                }
            }
        }
        retained(false)
        let raced = AccountContext(), raceMessage = message()
        raced.account.postbox.store.messages[raceMessage.id] = raceMessage
        raced.account.postbox.afterTransaction = { retained(true) }
        let raceRequest = _internal_transcribeAudio(postbox: raced.account.postbox, network: raced.account.network, messageId: raceMessage.id).start()
        check(raced.account.network.transcriptions == 0, "last network boundary rechecks changed retention")
        raceRequest.dispose()

        retained(true)
        let expiredContext = AccountContext(), expired = message()
        expired.media = [TelegramMediaExpiredContent()]
        expiredContext.account.postbox.store.messages[expired.id] = expired
        let expiredRequest = _internal_transcribeAudio(postbox: expiredContext.account.postbox, network: expiredContext.account.network, messageId: expired.id).start()
        check(expiredContext.account.network.transcriptions == 0, "expired temporary ID cannot reach native RPC")
        expiredRequest.dispose()

        retained(true); configure(.telegram, enabled: false)
        let automaticContext = AccountContext(), automatic = message()
        automaticContext.account.postbox.store.messages[automatic.id] = automatic
        let automaticDone = DispatchSemaphore(value: 0)
        var automaticDisabled = false
        let automaticRequest = NagramiXTranscriptionRuntime.transcribe(context: automaticContext, messageId: automatic.id, automatic: true).start(next: {
            if case .failure(.disabled) = $0 { automaticDisabled = true }; automaticDone.signal()
        })
        wait(automaticDone, "disabled automatic request terminates")
        check(automaticDisabled && automaticContext.account.network.transcriptions == 0, "manual private fallback never enables automatic ASR")
        automaticRequest.dispose()

        retained(true); configure(.telegram)
        let unavailableContext = AccountContext(), unavailable = message()
        unavailableContext.account.postbox.store.messages[unavailable.id] = unavailable
        NagramiXTranscriptionApple.supported = false
        let unavailableDone = DispatchSemaphore(value: 0)
        var unavailableResult = false
        let unavailableRequest = NagramiXTranscriptionRuntime.transcribe(context: unavailableContext, messageId: unavailable.id).start(next: {
            if case .failure(.unavailable) = $0 { unavailableResult = true }; unavailableDone.signal()
        })
        wait(unavailableDone, "unavailable private recognizer terminates")
        check(unavailableResult && unavailableContext.account.network.transcriptions == 0, "unavailable device recognizer never falls back to Telegram")
        unchangedLifetime(unavailable, file: unavailable.media[0] as! TelegramMediaFile)
        unavailableRequest.dispose(); NagramiXTranscriptionApple.supported = true

        retained(true); configure(.telegram)
        let cancelled = AccountContext(), c = message(); cancelled.account.postbox.store.messages[c.id] = c
        recognize(cancelled, message: c, expectedProvider: .apple, mutation: { retained(false) }, expectedError: .cancelled)
        unchangedLifetime(c, file: c.media[0] as! TelegramMediaFile)
        check(!c.attributes.contains { $0 is AudioTranscriptionMessageAttribute }, "OFF blocks late private transcript write")

        retained(true); configure(.telegram)
        let failed = AccountContext(), f = message(); failed.account.postbox.store.messages[f.id] = f
        recognize(failed, message: f, expectedProvider: .apple, outcome: .failure(.network), expectedError: .network)
        unchangedLifetime(f, file: f.media[0] as! TelegramMediaFile)

        retained(true); configure(.telegram)
        let deleted = AccountContext(), x = message(round: true)
        deleted.account.postbox.store.messages[x.id] = x; archive.put(x); archive.records[x.id.descriptionKey]?.deletedAt = nil
        recognize(deleted, message: x, expectedProvider: .apple, mutation: {
            deleted.account.postbox.store.messages[x.id] = nil
            archive.records[x.id.descriptionKey]?.deletedAt = 42
        })
        check(archive.records[x.id.descriptionKey]?.deletedAt == 42 && deleted.account.postbox.store.messages[x.id] == nil, "genuine deletion remains genuine without Postbox recreation")

        for temp in [false, true] {
            retained(temp); configure(.telegram)
            let context = AccountContext(), ordinary = message(ttl: nil)
            context.account.postbox.store.messages[ordinary.id] = ordinary
            check(NagramiXTranscriptionRuntime.canUseTelegram(ordinary), "ordinary native Telegram eligibility unchanged")
            let request = context.engine.messages.transcribeAudio(messageId: ordinary.id).start()
            check(context.account.network.transcriptions == 1, "ordinary Telegram RPC remains available")
            request.dispose()
        }
        print("Private temporary transcription checks: \(checks)")
    }
}
