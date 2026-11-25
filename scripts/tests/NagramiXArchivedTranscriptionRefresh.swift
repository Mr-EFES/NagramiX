extension PremiumFileTranscriptionChecks {
    static func verifyArchiveRefresh(_ c: AccountContext, _ m: Message, _ archive: NagramiXMessageArchive) {
        func row() -> Message {
            return archive.transcriptionMessage(id: m.id, liveMessage: nil)!
        }
        func visibleText(_ message: Message, _ forced: TranscribedText?) -> String? {
            if case let .success(text, false)? = nagramiXDisplayedTranscription(message, forced: forced) {
                return text
            }
            return nil
        }
        let premiumText = "Premium file transcript"
        let delayedLayout = TranscribedText.success(text: premiumText, isPending: false)
        let originalCalls = c.account.network.file.calls
        configure(.apple)
        NagramiXTranscriptionSettings.update { $0.language = "ru-RU" }
        expectFile(NagramiXTranscriptionRuntime.hasTemporaryTranscript(row(), context: c), "A opens the saved Telegram result after switching")
        expectFile(NagramiXTranscriptionRuntime.cached(row(), context: c) == nil, "provider cache really changed")
        expectFile(run(c, m) == .success(premiumText), "stale inline row resolves saved text without a recognizer")
        expectFile(c.account.network.file.calls == originalCalls, "no new Premium request from A")

        for text in ["first Apple result", "second Apple result"] {
            AudioBoundary.started = DispatchSemaphore(value: 0)
            let before = visibleText(row(), delayedLayout)
            let result = run(c, m, true) {
                wait(AudioBoundary.started, "menu invokes recognizer with unchanged settings as well")
                expectFile(AudioBoundary.provider == .apple, "selected provider is used")
                expectFile(visibleText(row(), delayedLayout) == before, "previous text stays during recognition")
                AudioBoundary.finish(.success(text))
            }
            expectFile(result == .success(text), "new recognition completed")
            expectFile(visibleText(row(), delayedLayout) == text, "A displays the persisted result even in expanded round layout")
        }

        NagramiXTranscriptionSettings.update { $0.language = "de-DE" }
        expectFile(NagramiXTranscriptionRuntime.hasTemporaryTranscript(row(), context: c), "A still reads text after a dictionary change")
        expectFile(run(c, m) == .success("second Apple result"), "opening text after a dictionary change uses no ASR")
        AudioBoundary.started = DispatchSemaphore(value: 0)
        let failed = run(c, m, true) {
            wait(AudioBoundary.started, "another menu request begins")
            AudioBoundary.finish(.failure(.noSpeech))
        }
        expectFile(failed == .failure(.noSpeech), "service failure is reported")
        expectFile(visibleText(row(), nil) == "second Apple result", "failed refresh preserves stored text")

        AudioBoundary.started = DispatchSemaphore(value: 0)
        NagramiXTranscriptionRuntime.startContext(context: c, messageId: m.id) { _ in fatalError("superseded request delivered") }
        wait(AudioBoundary.started, "first overlapping request started")
        let oldCancel = NagramiXTranscriptionRuntime.cancelContextAction(context: c, messageId: m.id)!
        let done = DispatchSemaphore(value: 0)
        var latest: Result<String, NagramiXTranscriptionFailure>?
        NagramiXTranscriptionRuntime.startContext(context: c, messageId: m.id) { latest = $0; done.signal() }
        oldCancel()
        expectFile(NagramiXTranscriptionRuntime.contextRunning(context: c, messageId: m.id), "an old cancel action cannot cancel the new request")
        AudioBoundary.finish(.success("superseded"))
        wait(AudioBoundary.started, "repeat starts a fresh recognizer")
        AudioBoundary.finish(.success("latest"))
        wait(done, "replacement completed")
        expectFile(latest == .success("latest"), "latest request succeeds")
        for pending in [true, false] {
            archive.retainTelegramTranscription(id: m.id, attribute: AudioTranscriptionMessageAttribute(id: 77, text: "old server update", isPending: pending, didRate: false, error: nil))
            expectFile(visibleText(row(), delayedLayout) == "latest", "late Telegram update cannot replace the selected result")
        }
        expectFile(c.account.network.file.calls == originalCalls && c.account.network.transcriptions == 0, "changed provider uses only local retained audio")
        expectFile(visibleText(m, delayedLayout) == premiumText, "live layout retains its forced text")
        configure()
    }
}
