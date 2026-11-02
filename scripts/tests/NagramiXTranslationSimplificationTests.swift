import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

@main struct TranslationSimplificationTests {
    static func main() throws {
        let configurationKey = "nagramix.translation.configuration.v1"
        let old = UserDefaults.standard.data(forKey: configurationKey)
        defer {
            if let old { UserDefaults.standard.set(old, forKey: configurationKey) }
            else { UserDefaults.standard.removeObject(forKey: configurationKey) }
        }
        UserDefaults.standard.removeObject(forKey: configurationKey)
        let fresh = NagramiXTranslationSettings.current
        precondition(!fresh.enabled && !fresh.automatic && fresh.provider == .apple)
        precondition(fresh.target.isEmpty && fresh.ignored.isEmpty)
        precondition(NagramiXTranslationProvider.allCases.map(\.title) == ["Apple", "Google", "Яндекс", "Gemini", "ChatGPT", "DeepSeek"])
        for provider in NagramiXTranslationProvider.allCases {
            precondition(provider.requiresAPIKey == provider.isLanguageModel)
            precondition(fresh.temperature(for: provider) == 0.2)
        }

        let retired = Data(#"{"enabled":true,"automatic":true,"showTranslateButton":false,"provider":"gptoss","target":"de","ignored":["ru"],"models":{"gptoss":"gpt-oss-20b","chatgpt":"gpt-4.1-mini"},"temperatures":{"gptoss":0.8,"chatgpt":0.4},"appleSource":"en","revision":"saved"}"#.utf8)
        let migrated = try JSONDecoder().decode(NagramiXTranslationConfiguration.self, from: retired)
        precondition(migrated.enabled && !migrated.automatic && !migrated.showsTranslateButton)
        precondition(migrated.provider == .apple && migrated.target == "de" && migrated.ignored == ["ru"])
        precondition(migrated.models == ["chatgpt":"gpt-4.1-mini"] && migrated.temperatures == ["chatgpt":0.4])
        precondition(migrated.revision == "provider-migration:saved")
        let encoded = try JSONEncoder().encode(migrated)
        precondition(!String(data: encoded, encoding: .utf8)!.contains("gptoss"))
        precondition(!String(data: encoded, encoding: .utf8)!.contains("appleSource"))
        let roundtrip = try JSONDecoder().decode(NagramiXTranslationConfiguration.self, from: encoded)
        precondition(roundtrip == migrated)
        for provider in NagramiXTranslationProvider.allCases {
            let input: [String: Any] = ["enabled":true, "automatic":true, "provider":provider.rawValue, "target":"fr", "ignored":["en"], "revision":"existing"]
            let value = try JSONDecoder().decode(NagramiXTranslationConfiguration.self, from: JSONSerialization.data(withJSONObject: input))
            precondition(value.provider == provider && value.enabled && value.automatic && value.target == "fr" && value.revision == "existing")
        }

        var policy = NagramiXTranslationConfiguration()
        precondition(policy.resolvedTarget(interface: "ru-RU") == "ru")
        precondition(policy.effectiveIgnored(interface: "ru") == ["ru"])
        policy.target = "de"
        precondition(policy.effectiveIgnored(interface: "ru") == ["de"])
        policy.ignored = ["ru", "EN-us", "en"]
        precondition(policy.effectiveIgnored(interface: "ru") == ["de", "en", "ru"])
        precondition(policy.effectiveIgnored(interface: "ru", target: "fr") == ["en", "fr", "ru"])
        precondition(policy.ignored == ["ru", "EN-us", "en"])
        precondition(policy.resolvedTarget(interface: "ru", targetOverride: "es") == "es")
        precondition(NagramiXTranslationLanguage.accepted([("de", 0.95)], interface: "de", ignored: policy.effectiveIgnored(interface: "ru")) == nil)
        precondition(NagramiXTranslationLanguage.accepted([("it", 0.95)], interface: "de", ignored: policy.effectiveIgnored(interface: "ru")) == "it")

        // Editing is a draft; failed validation/Keychain does not persist it.
        NagramiXTranslationSettings.update { $0.enabled = true; $0.provider = .gemini }
        let prior = NagramiXTranslationSettings.current
        let draft = TranslationDraftHarness(provider: .gemini, key: "new-test-key", model: "gemini-2.5-flash", temperature: 0.6)
        precondition(NagramiXTranslationSettings.current == prior && NagramiXTranslationKeys.values.isEmpty)
        NagramiXTranslationKeys.fail = true
        draft.saveCredentials()
        precondition(NagramiXTranslationSettings.current == prior && !draft.dismissed && !draft.errors.isEmpty)
        NagramiXTranslationKeys.fail = false
        let notifications = TranslationNotificationCounter()
        let observer = NotificationCenter.default.addObserver(forName: NagramiXTranslationSettings.changed, object: nil, queue: nil) { _ in
            notifications.increment()
            let value = NagramiXTranslationSettings.current
            precondition(value.models["gemini"] == "gemini-2.5-flash" && value.temperature(for: .gemini) == 0.6)
            precondition(NagramiXTranslationKeys.values[.gemini]?.key == "new-test-key")
        }
        draft.saveCredentials()
        precondition(draft.dismissed && notifications.value == 1)
        NotificationCenter.default.removeObserver(observer)
        let beforeDelete = NagramiXTranslationSettings.current.revision
        let deletion = TranslationDraftHarness(provider: .gemini, key: "", model: "gemini-2.5-flash", temperature: 0.4)
        precondition(NagramiXTranslationKeys.values[.gemini] != nil)
        deletion.saveCredentials()
        precondition(NagramiXTranslationKeys.values[.gemini] == nil && deletion.dismissed)
        precondition(NagramiXTranslationSettings.current.revision != beforeDelete)
        let invalid = TranslationDraftHarness(provider: .chatgpt, key: "bad\nkey", model: "gpt-4.1-mini", temperature: 0.2)
        let snapshot = NagramiXTranslationSettings.current
        invalid.saveCredentials()
        precondition(!invalid.dismissed && NagramiXTranslationSettings.current == snapshot)

        // All three neural services require the user's key and the right host.
        for provider in [NagramiXTranslationProvider.gemini, .chatgpt, .deepseek] {
            do {
                _ = try NagramiXTranslationCloudCodec.request(provider: provider, credential: .init(key: "", folder: ""), model: provider.defaultModel, texts: ["Hello"], source: "en", target: "ru")
                preconditionFailure("Neural translation without a key")
            } catch { precondition(error as? NagramiXTranslationFailure == .missingKey) }
            let request = try NagramiXTranslationCloudCodec.request(provider: provider, credential: .init(key: "fixture-key", folder: ""), model: provider.defaultModel, texts: ["Hello"], source: "en", target: "ru", temperature: 0.2)
            precondition(request.httpMethod == "POST" && request.url?.scheme == "https")
            precondition(!request.url!.absoluteString.contains("fixture-key"))
            if provider == .gemini { precondition(request.url?.host == "generativelanguage.googleapis.com" && request.value(forHTTPHeaderField: "x-goog-api-key") == "fixture-key") }
            else {
                precondition(request.url?.host == (provider == .chatgpt ? "api.openai.com" : "api.deepseek.com"))
                precondition(request.value(forHTTPHeaderField: "Authorization") == "Bearer fixture-key")
            }
        }
        for provider in [NagramiXTranslationProvider.google, .yandex] {
            let plan = try NagramiXTranslationWebPlan(provider: provider, texts: ["Hello 👨‍👩‍👧‍👦 world"], source: "en", target: "ru")
            precondition(plan.requests.allSatisfy { $0.value(forHTTPHeaderField: "Authorization") == nil && $0.value(forHTTPHeaderField: "x-goog-api-key") == nil })
            do {
                _ = try NagramiXTranslationCloudCodec.request(provider: provider, credential: .init(key: "legacy-key", folder: "old"), model: "", texts: ["Hello"], source: "en", target: "ru")
                preconditionFailure("Paid web fallback")
            } catch { precondition(error as? NagramiXTranslationFailure == .invalidText) }
        }
        print("PASS: production v1/provider migration, automatic/manual exclusions, draft and atomic Save, key deletion/failure, neural auth and free-web isolation; UIKit/Keychain/network mocked")
    }
}
