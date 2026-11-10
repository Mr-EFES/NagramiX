
private var defaultChecks = 0
private func expect(_ value: Bool, _ label: String) {
    defaultChecks += 1
    if !value { fputs("Transcription defaults regression: \(label)\n", stderr); exit(96) }
}

@main struct TranscriptionAccountDefaultsTests {
    static let key = "nagramix.transcription.configuration.v1"
    static func clear() {
        UserDefaults.standard.removeObject(forKey: key)
        for id in [-9, 1, 2, 3] { UserDefaults.standard.removeObject(forKey: "nagramix.transcription.account-default.v1.\(id)") }
    }
    static func wait(_ semaphore: DispatchSemaphore, _ label: String) {
        expect(semaphore.wait(timeout: .now() + 4) == .success, label)
    }
    static func config(_ id: Int64) -> NagramiXTranscriptionConfiguration {
        NagramiXTranscriptionSettings.configuration(accountId: id)
    }
    static func main() throws {
        clear(); defer { clear() }
        let fresh = NagramiXTranscriptionSettings.current
        expect(fresh.enabled, "fresh master is enabled")
        expect(!fresh.automatic, "fresh automatic stays opt-in")
        expect(fresh.usesAccountDefaultProvider == true && fresh.provider == .apple, "fresh starts with safe local default")
        expect(fresh.cloudAllowed.isEmpty && fresh.models.isEmpty, "no cloud consent or downloads on startup")
        let premium = AccountContext(); premium.account.id.int64 = 2
        let free = AccountContext(); free.account.id.int64 = 1
        observeAccount(premium.account, peer: StartupPeer(isPremium: true))
        expect(config(2).provider == .telegram, "known Premium selects Telegram")
        observeAccount(free.account, peer: StartupPeer(isPremium: false))
        expect(config(1).provider == .apple, "free account selects Apple")
        expect(config(2).provider == .telegram, "second account does not overwrite Premium default")
        expect(config(1).sourceAccountId == 1 && config(2).sourceAccountId == 2, "runtime scope follows requesting account")
        let beforeNil = config(2)
        observeAccount(premium.account, peer: nil)
        expect(config(2) == beforeNil, "unknown peer never overwrites real Premium")
        expect(UserDefaults.standard.data(forKey: key) == nil, "startup leaves shared settings unwritten")
        let voice = PrivateTemporaryTranscriptionTests.message(ttl: nil)
        expect(!NagramiXTranscriptionRuntime.handles(voice, context: premium), "Premium runtime uses native Telegram")
        expect(NagramiXTranscriptionRuntime.handles(voice, context: free), "free runtime uses local Apple")
        expect(NagramiXTranscriptionRuntime.handlesContext(voice, context: premium), "Premium context action remains available")
        let round = PrivateTemporaryTranscriptionTests.message(round: true, ttl: nil)
        expect(!NagramiXTranscriptionRuntime.handles(round, context: premium) && NagramiXTranscriptionRuntime.handles(round, context: free), "round uses same per-account routing")
        PrivateTemporaryTranscriptionTests.retained(true)
        let temporary = PrivateTemporaryTranscriptionTests.message(round: true)
        expect(NagramiXTranscriptionRuntime.handles(temporary, context: premium), "private temporary keeps local Apple override")
        expect(!NagramiXTranscriptionRuntime.canUseTelegram(temporary), "private temporary never reaches native RPC")
        let freeRevision = config(1).revision
        observeAccount(premium.account, peer: StartupPeer(isPremium: false))
        expect(config(2).provider == .apple && config(2).revision != beforeNil.revision, "automatic default follows actual subscription change")
        expect(config(1).revision == freeRevision, "other account revision stays stable")
        observeAccount(premium.account, peer: StartupPeer(isPremium: true))

        // An ordinary settings edit keeps initial account defaults, but OFF is durable.
        NagramiXTranscriptionSettings.update { $0.enabled = false; $0.language = "ru-RU" }
        let savedOff = UserDefaults.standard.data(forKey: key)
        observeAccount(premium.account, peer: StartupPeer(isPremium: false))
        observeAccount(premium.account, peer: StartupPeer(isPremium: true))
        expect(!config(2).enabled && config(2).provider == .telegram && config(2).language == "ru-RU", "saved OFF survives account refresh")
        expect(UserDefaults.standard.data(forKey: key) == savedOff, "account refresh never rewrites shared bytes")
        expect(NagramiXTranscriptionSettings.current.sourceAccountId == nil, "runtime scope not persisted")

        // Decode real old Codable data, including absence of the new optional field.
        for enabled in [false, true] {
            var old = NagramiXTranscriptionConfiguration()
            old.enabled = enabled; old.provider = .vosk; old.automatic = true
            old.language = "fr-FR"; old.voskModelID = "custom-model"; old.models = ["gemini":"custom-cloud-model"]
            old.cloudAllowed = ["gemini":true]; old.temperatures = ["gemini":0.37]
            old.credentialRevision = "existing-credential"; old.revision = "legacy-revision"
            var json = try JSONSerialization.jsonObject(with: JSONEncoder().encode(old)) as! [String:Any]
            json.removeValue(forKey: "usesAccountDefaultProvider"); json.removeValue(forKey: "sourceAccountId")
            let bytes = try JSONSerialization.data(withJSONObject: json)
            UserDefaults.standard.set(bytes, forKey: key)
            NagramiXTranscriptionSettings.registerAccountDefault(accountId: 2, isPremium: false)
            NagramiXTranscriptionSettings.registerAccountDefault(accountId: 2, isPremium: true)
            let restored = config(2)
            expect(restored.provider == .vosk && restored.enabled == enabled && restored.usesAccountDefaultProvider == nil, "legacy provider and OFF survive")
            expect(restored.automatic && restored.language == old.language && restored.voskModelID == old.voskModelID, "legacy language and model survive")
            expect(restored.cloudAllowed == old.cloudAllowed && restored.temperatures == old.temperatures && restored.models == old.models && restored.credentialRevision == old.credentialRevision, "cloud keys metadata and consents survive")
            expect(restored.revision == old.revision && UserDefaults.standard.data(forKey: key) == bytes, "legacy storage is not migrated destructively")
        }
        clear(); observeAccount(premium.account, peer: StartupPeer(isPremium: true))
        chooseProvider(.apple)
        expect(config(2).provider == .apple && config(2).usesAccountDefaultProvider == false, "explicit same-value Apple freezes choice")
        observeAccount(premium.account, peer: StartupPeer(isPremium: false)); observeAccount(premium.account, peer: StartupPeer(isPremium: true))
        expect(config(2).provider == .apple && config(1).provider == .apple, "manual choice remains shared and durable")
        NagramiXTranscriptionSettings.update { $0.provider = .gemini }
        expect(config(2).provider == .gemini && config(2).usesAccountDefaultProvider == false, "other explicit provider remains selected")
        expect(config(2).cloudAllowed.isEmpty, "default selection never grants cloud consent")

        clear(); observeAccount(free.account, peer: StartupPeer(isPremium: false))
        NagramiXTranscriptionSettings.registerAccountDefault(accountId: 3, isPremium: false)
        let coordinator = NagramiXTranscriptionCoordinator()
        let activeStarted = DispatchSemaphore(value: 0), activeCompleted = DispatchSemaphore(value: 0), pendingCancelled = DispatchSemaphore(value: 0)
        var finishActive: ((NagramiXTranscriptionCoordinator.Outcome)->Void)?
        var activeToken: NagramiXTranscriptionCancellation?
        let active = coordinator.request(key: "active-account-1", configuration: config(1), automatic: false, work: { token, finish in
            activeToken = token; finishActive = finish; activeStarted.signal()
        }, completion: { result in
            if case .success = result { activeCompleted.signal() }
        })
        wait(activeStarted, "scoped coordinator starts")
        let pending = coordinator.request(key: "pending-account-3", configuration: config(3), automatic: false, work: { _, _ in
            expect(false, "obsolete pending job must not start")
        }, completion: { result in
            if case .failure(.cancelled) = result { pendingCancelled.signal() }
        })
        coordinator.flushForDefaults()
        NagramiXTranscriptionSettings.registerAccountDefault(accountId: 3, isPremium: true)
        wait(pendingCancelled, "pending job follows its own account revision")
        coordinator.flushForDefaults()
        expect(activeToken?.cancelled == false, "other account change leaves active job")
        finishActive?(.success("ok")); wait(activeCompleted, "valid active job finishes")
        active.cancel(); pending.cancel()
        let stale = config(1)
        NagramiXTranscriptionSettings.registerAccountDefault(accountId: 1, isPremium: true)
        let rejected = DispatchSemaphore(value: 0)
        let staleRequest = coordinator.request(key: "stale", configuration: stale, automatic: false, work: { _, _ in
            expect(false, "stale job must not start")
        }, completion: { result in if case .failure(.disabled) = result { rejected.signal() } })
        wait(rejected, "stale scoped request rejected"); staleRequest.cancel()
        clear()
        print("Transcription account defaults checks: \(defaultChecks)")
        // Retest the complete existing private temporary ASR/RPC/TTL suite on the new runtime.
        PrivateTemporaryTranscriptionTests.main()
    }
}
