extension PremiumFileTranscriptionChecks {
    static func verifyRetainedAudio() {
        let archive = NagramiXMessageArchive()
        NagramiXMessageArchive.registered = archive
        defer { NagramiXMessageArchive.registered = nil }
        let path = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try! Data([11, 22, 33, 44]).write(to: path)
        defer { try? FileManager.default.removeItem(at: path) }
        func keepDeleted(_ value: Bool) { fileTestDefaults.set(value, forKey: "nagramix.messages.showDeletedMessages") }
        func retain(_ m: Message, temporary: Bool) {
            let file = m.media[0] as! TelegramMediaFile
            let local = TelegramMediaFile("different-cache-id")
            local.fileId = file.fileId
            local.size = file.size
            local.duration = file.duration
            local.isVoice = file.isVoice
            local.isInstantVideo = file.isInstantVideo
            local.resource = LocalFileReferenceMediaResource(path.path, size: 4)
            let retained = Message(m.id, local)
            retained.attributes = [NagramiXArchivedMessageAttribute(isTemporary: temporary)]
            archive.records[m.id.descriptionKey] = ArchiveRecord(sourceWasTemporary: temporary, message: retained, deletedAt: 812, temporary: temporary)
        }

        for round in [false, true] {
            for ttl: Int32? in [nil, 30, viewOnceTimeout] {
                for menu in [false, true] {
                    configure()
                    PrivateTemporaryTranscriptionTests.retained(false)
                    keepDeleted(true)
                    let c = context(), m = message(c, round, true, ttl)
                    retain(m, temporary: ttl != nil)
                    c.account.postbox.store.messages.removeValue(forKey: m.id)
                    c.engine.resources.complete = false
                    fixtureInputPath = ""
                    expectFile(run(c, m, menu) == .success("Premium file transcript"), "deleted round/voice uses available audio")
                    expectFile(fixtureInputPath == path.path && c.engine.resources.fetches == 0, "reads archived bytes with empty MediaBox")
                    expectFile(c.account.network.file.calls == 1 && c.account.network.transcriptions == 0, "no message ID request for deleted audio")
                    guard let record = archive.records[m.id.descriptionKey], let displayed = archive.transcriptionMessage(id: m.id, liveMessage: nil) else { fatalError("missing saved copy") }
                    expectFile(record.wasTemporary == (ttl != nil) && record.deletedAt == 812, "recognition preserves TTL provenance and deletion date")
                    expectFile(NagramiXTranscriptionRuntime.hasReadyTranscript(displayed), "transcript reopens on the archived row")
                    expectFile(run(c, m) == .success("Premium file transcript") && c.account.network.file.calls == 1, "reuse completed text")
                    expectFile(c.account.postbox.store.messages[m.id] == nil, "no recreated server row")
                    keepDeleted(false)
                    expectFile(run(c, m) == .failure(.unavailableMedia), "hidden deleted archive is not a source")
                }
            }
            for ttl: Int32 in [30, viewOnceTimeout] {
                configure()
                PrivateTemporaryTranscriptionTests.retained(false)
                keepDeleted(false)
                let c = context(), m = message(c, round, true, ttl)
                expectFile(run(c, m) == .success("Premium file transcript"), "live temporary audio works independently of retention")
                expectFile(c.account.network.file.calls == 1 && archive.records[m.id.descriptionKey] == nil, "live recognition does not create an archive")

                let expired = message(c, round, true, ttl)
                PrivateTemporaryTranscriptionTests.retained(true)
                retain(expired, temporary: true)
                archive.records[expired.id.descriptionKey]?.deletedAt = nil
                archive.records[expired.id.descriptionKey]?.mediaExpiredAt = 910
                c.account.postbox.store.messages.removeValue(forKey: expired.id)
                expectFile(run(c, expired) == .success("Premium file transcript"), "expired retained audio remains transcribable")
                let record = archive.records[expired.id.descriptionKey]
                expectFile(record?.mediaExpiredAt == 910 && record?.deletedAt == nil, "expiry stays distinct from message deletion")
            }
            configure()
            keepDeleted(true)
            let staleContext = context(), stale = message(staleContext, round, true, nil)
            retain(stale, temporary: false)
            expectFile(run(staleContext, stale) == .success("Premium file transcript"), "known deletion supersedes stale live row")
            expectFile(!NagramiXTranscriptionRuntime.hasReadyTranscript(stale) && staleContext.account.network.transcriptions == 0, "stale row is not the write or RPC target")

            let missingContext = context(), missing = message(missingContext, round, true, nil)
            retain(missing, temporary: false)
            let absent = path.appendingPathExtension("missing")
            let missingFile = archive.records[missing.id.descriptionKey]!.message.media[0] as! TelegramMediaFile
            missingFile.resource = LocalFileReferenceMediaResource(absent.path, size: 4)
            missingContext.engine.resources.complete = false
            missingContext.account.postbox.store.messages.removeValue(forKey: missing.id)
            expectFile(run(missingContext, missing) == .failure(.unavailableMedia), "missing retained audio has no transcript")
            expectFile(missingContext.engine.resources.fetches == 0 && missingContext.account.network.file.calls == 0, "missing archive does not refetch or upload")
            for provider in [NagramiXTranscriptionProvider.apple, .whisper, .vosk, .gemini, .chatgpt, .grok, .cloudflare] {
                configure(provider)
                keepDeleted(true)
                let c = context(), m = message(c, round, true, nil)
                retain(m, temporary: false)
                c.account.postbox.store.messages.removeValue(forKey: m.id)
                AudioBoundary.started = DispatchSemaphore(value: 0)
                let done = DispatchSemaphore(value: 0)
                var result: Result<String, NagramiXTranscriptionFailure>?
                let d = NagramiXTranscriptionRuntime.transcribe(context: c, messageId: m.id).start(next: { result = $0; done.signal() })
                wait(AudioBoundary.started, "selected recognizer starts")
                expectFile(AudioBoundary.provider == provider, "archived message keeps the explicit provider")
                AudioBoundary.finish(.success("saved text"))
                wait(done, "archive commit finishes")
                expectFile(result == .success("saved text") && c.account.network.file.calls == 0, "text stored without a Telegram upload")
                d.dispose()
            }
        }
        configure(.apple)
        keepDeleted(true)
        let c = context(), m = message(c, false, true, nil)
        AudioBoundary.started = DispatchSemaphore(value: 0)
        let done = DispatchSemaphore(value: 0)
        var result: Result<String, NagramiXTranscriptionFailure>?
        let d = NagramiXTranscriptionRuntime.transcribe(context: c, messageId: m.id).start(next: { result = $0; done.signal() })
        wait(AudioBoundary.started, "regular live job starts")
        retain(m, temporary: false)
        c.account.postbox.store.messages.removeValue(forKey: m.id)
        AudioBoundary.finish(.success("survived deletion"))
        wait(done, "in-flight job finishes on retained file")
        expectFile(result == .success("survived deletion"), "resource identity survives deletion")
        d.dispose()

        let cleared = message(c, false, true, nil)
        retain(cleared, temporary: false)
        c.account.postbox.store.messages.removeValue(forKey: cleared.id)
        AudioBoundary.started = DispatchSemaphore(value: 0)
        let clearedResult = run(c, cleared, false) {
            wait(AudioBoundary.started, "recognition starts before clearing")
            archive.clearAll()
            AudioBoundary.finish(.success("late result"))
        }
        expectFile(clearedResult == .failure(.cancelled) && archive.records.isEmpty, "late recognition cannot recreate a cleared archive")

        var legacy = ArchiveRecord(message: m, temporary: false, transcriptionAttributes: [])
        expectFile(legacy.wasTemporary, "legacy cleared flags preserve old temporary provenance")
        legacy.sourceWasTemporary = false
        expectFile(!legacy.wasTemporary, "new regular transcript does not enable replay")
    }
}
