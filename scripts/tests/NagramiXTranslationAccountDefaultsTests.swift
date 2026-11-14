private var checks = 0
private func expect(_ condition: @autoclosure () -> Bool, _ why: String) {
    checks += 1
    guard condition() else { print("FAIL: " + why); exit(96) }
}
private let key = "nagramix.translation.configuration.v1"
private func reset() { TranslationDefaultsStorage.defaults.removePersistentDomain(forName: TranslationDefaultsStorage.suite) }
private func saved(_ text: String) { TranslationDefaultsStorage.defaults.set(Data(text.utf8), forKey: key) }
private func context(_ id: Int64) -> TestContext { TestContext(account: TestAccount(id: TestId(int64: id))) }
private func config(_ id: Int64) -> NagramiXTranslationConfiguration { NagramiXTranslationSettings.configuration(accountId: id) }
@main private enum Tests {
    static func main() throws {
        let args = CommandLine.arguments
        if args.count > 1 {
            if args[1] == "--cold-write" {
                reset()
                NagramiXTranslationSettings.registerAccountDefault(accountId: 1, isPremium: true)
                selectProvider(.apple)
                NagramiXTranslationSettings.update { $0.enabled = false; $0.showTranslateButton = true; $0.automatic = true; $0.target = "de" }
                expect(TranslationDefaultsStorage.defaults.synchronize(), "cold storage flush succeeds")
            } else if args[1] == "--cold-read" {
                NagramiXTranslationSettings.registerAccountDefault(accountId: 1, isPremium: true)
                let value = config(1)
                expect(!value.enabled && value.provider == .apple && value.showsTranslateButton && value.automatic && value.target == "de", "cold process preserves manual provider and switches")
            } else if args[1] == "--cleanup" { reset() }
            else { exit(97) }
            print("\(checks) cold-process translation checks passed"); return
        }
        reset(); defer { reset() }
        var value = config(1)
        expect(value.enabled && !value.automatic && !value.showsTranslateButton, "fresh master on and both optional switches off")
        expect(value.provider == .apple && value.usesAccountDefaultProvider == true, "unknown account starts safely with Apple")
        let initial = value.revision
        registerPeer(account: context(1).account, peer: nil)
        expect(config(1).revision == initial && TranslationDefaultsStorage.defaults.data(forKey: key) == nil, "unknown peer never registers a speculative default")
        registerPeer(account: context(1).account, peer: TestPeer(isPremium: true))
        registerPeer(account: context(2).account, peer: TestPeer(isPremium: false))
        expect(config(1).provider == .telegram && config(2).provider == .apple, "two accounts resolve their own Premium defaults")
        value = config(1)
        expect(value.revision != initial, "account default invalidates stale shared requests")
        expect(value.enabled && !value.showsTranslateButton && !value.automatic, "Premium never enables panel or whole chats")
        let revision = value.revision
        NagramiXTranslationSettings.registerAccountDefault(accountId: 1, isPremium: true)
        expect(config(1).revision == revision, "repeated Premium event is idempotent")
        expect(config(1).revision == NagramiXTranslationSettings.current.revision, "resolved config preserves shared cancellation revision")
        for id: Int64 in [1,2] {
            let expected: NagramiXTranslationProvider = id == 1 ? .telegram : .apple
            expect(entries(translation: config(id)) == [.translationHeader,.translationEnabled(true),.translationOptions(expected)], "outer entries use account provider")
            expect(capture0(context: context(id)) == expected, "inline route uses account provider")
            expect(capture1(context: context(id)) == expected, "whole chat route uses account provider")
            expect(capture2(context: context(id)) == expected, "result screen uses account provider")
            expect(dispatch(context: context(id)) == expected, "common dispatch uses account provider")
        }
        expect(NagramiXTranslationProvider.telegram.settingsTitle == "Telegram" && NagramiXTranslationProvider.telegram.title == "Telegram Premium", "short outer label keeps full inner label")
        for provider in NagramiXTranslationProvider.allCases where provider != .telegram { expect(provider.settingsTitle == provider.title, "other provider labels preserved") }
        NagramiXTranslationSettings.update { $0.enabled = false; $0.target = "fr"; $0.ignored = ["it"]; $0.models = ["chatgpt":"gpt-5.4-mini"]; $0.temperatures = ["chatgpt":0.7] }
        expect(config(1).provider == .telegram && config(1).usesAccountDefaultProvider == true, "other preference edits retain account provider")
        expect(entries(translation: config(1)) == [.translationHeader,.translationEnabled(false)], "saved master OFF hides provider row")
        NagramiXTranslationSettings.registerAccountDefault(accountId: 1, isPremium: false)
        value = config(1)
        expect(!value.enabled && value.provider == .apple && value.target == "fr" && value.ignored == ["it"] && value.models["chatgpt"] == "gpt-5.4-mini" && value.temperatures?["chatgpt"] == 0.7, "Premium update preserves OFF and other preferences")
        NagramiXTranslationSettings.registerAccountDefault(accountId: 1, isPremium: true)
        expect(config(1).provider == .telegram && !config(1).enabled, "renewed Premium changes only automatic provider")
        selectProvider(.apple)
        expect(config(1).provider == .apple && config(1).usesAccountDefaultProvider == false, "selecting same raw Apple explicitly exits automatic provider")
        let manualRevision = config(1).revision
        NagramiXTranslationSettings.registerAccountDefault(accountId: 1, isPremium: false)
        NagramiXTranslationSettings.registerAccountDefault(accountId: 1, isPremium: true)
        expect(config(1).provider == .apple && config(1).revision == manualRevision, "manual Apple survives account events without request cancellation")
        for provider in NagramiXTranslationProvider.allCases {
            selectProvider(provider)
            NagramiXTranslationSettings.registerAccountDefault(accountId: 2, isPremium: true)
            NagramiXTranslationSettings.registerAccountDefault(accountId: 2, isPremium: false)
            expect(config(1).provider == provider && config(2).provider == provider, "explicit shared provider remains on both accounts")
            let encoded = try JSONEncoder().encode(NagramiXTranslationSettings.current)
            let decoded = try JSONDecoder().decode(NagramiXTranslationConfiguration.self, from: encoded)
            expect(decoded == NagramiXTranslationSettings.current && decoded.usesAccountDefaultProvider == false, "Codable preserves explicit selection")
        }
        for enabled in [false,true] { for panel in [false,true] { for automatic in [false,true] {
            saved("{\"enabled\":\(enabled),\"provider\":\"google\",\"showTranslateButton\":\(panel),\"automatic\":\(automatic),\"target\":\"de\",\"revision\":\"old\"}")
            NagramiXTranslationSettings.registerAccountDefault(accountId: 1, isPremium: true)
            value = config(1)
            expect(value.enabled == enabled && value.showsTranslateButton == panel && value.automatic == automatic && value.provider == .google && value.usesAccountDefaultProvider == false && value.revision == "old", "legacy saved switches and provider remain exact")
        } } }
        saved("{\"enabled\":false,\"provider\":\"apple\"}")
        expect(!config(1).enabled && config(1).provider == .apple && !config(1).showsTranslateButton, "legacy Apple not mistaken for missing provider")
        saved("{}")
        expect(config(1).enabled && config(1).provider == .telegram && !config(1).showsTranslateButton && !config(1).automatic, "missing fields receive new defaults")
        saved("{\"provider\":\"retired-service\",\"enabled\":false,\"automatic\":true,\"target\":\"es\"}")
        expect(config(1).provider == .apple && !config(1).enabled && !config(1).automatic && config(1).target == "es" && config(1).revision.hasPrefix("provider-migration:"), "retired provider keeps existing safe migration")
        reset()
        let chat = NagramiXTranslationSettings.chatKey(account: 1, peer: 9, thread: 4)
        NagramiXTranslationSettings.updateChat(chat) { $0.enabled = true; $0.target = "de"; $0.hidden = true }
        registerPeer(account: context(1).account, peer: TestPeer(isPremium: true))
        let choice = NagramiXTranslationSettings.chat(chat)
        expect(choice.enabled == true && choice.target == "de" && choice.hidden, "account defaults leave peer choices untouched")
        NagramiXTranslationSettings.update { $0.showTranslateButton = true; $0.automatic = true }
        NagramiXTranslationSettings.registerAccountDefault(accountId: 1, isPremium: false)
        expect(config(1).showsTranslateButton && config(1).automatic, "saved optional switches ON never reset")
        print("\(checks) actual translation account-default checks passed")
    }
}
