import Foundation

@main
struct NagramiXInlineTranslationTests {
    private static var checks = 0
    private static func check(_ value: @autoclosure () -> Bool, _ reason: String) {
        checks += 1
        if !value() { fatalError(reason) }
    }
    static func main() throws {
        let key = "nagramix.translation.configuration.v1"
        let defaults = UserDefaults.standard
        let saved = defaults.data(forKey: key)
        defer { if let saved { defaults.set(saved, forKey: key) } else { defaults.removeObject(forKey: key) } }
        check(NagramiXTranslationProvider.allCases.count == 7, "seven explicit services")
        check(NagramiXTranslationProvider.allCases.first == .telegram, "Telegram first")
        check(!NagramiXTranslationProvider.telegram.requiresAPIKey, "Telegram uses account authorization")
        check(!NagramiXTranslationProvider.telegram.isFreeWeb, "Telegram never anonymous web")
        check(!NagramiXTranslationProvider.telegram.isLanguageModel, "Telegram not LLM key flow")
        var config = NagramiXTranslationConfiguration()
        config.enabled = true; config.provider = .telegram; config.revision = "test-revision"
        config.target = "ru"; config.ignored = ["fr"]
        func persist() throws { defaults.set(try JSONEncoder().encode(config), forKey: key) }
        try persist()
        let decoded = try JSONDecoder().decode(NagramiXTranslationConfiguration.self, from: JSONEncoder().encode(config))
        check(decoded == config, "new provider roundtrip")
        let old = try JSONDecoder().decode(NagramiXTranslationConfiguration.self, from: Data("{\"provider\":\"google\",\"enabled\":true,\"revision\":\"legacy\"}".utf8))
        check(old.provider == .google && old.revision == "legacy" && old.enabled, "existing selection preserved")
        check(config.effectiveIgnored(interface: "en") == ["fr", "ru"], "exclusions remain common")
        let entities = [MessageTextEntity(range: 0..<5, type: "bold")]
        let source = Message(text: "Hello world", attributes: [TextEntitiesMessageAttribute(entities)])
        let fingerprint = nagramiXInlineTranslationFingerprint(source)
        let normal = TranslationMessageAttribute(text: "Привет, мир", entities: entities, toLang: "ru")
        check(normal.nagramiXInlineRevision == nil && !normal.nagramiXInlineHidden, "native constructors unchanged")
        check(nagramiXInlineTranslationTarget(Message(text: source.text, attributes: [normal])) == nil, "native cache does not enable single-message display")
        let translated = TranslationMessageAttribute(text: "Привет, мир", entities: entities, toLang: "ru",
            nagramiXInlineRevision: config.revision, nagramiXInlineSource: fingerprint)
        let shown = Message(text: source.text, attributes: source.attributes + [translated])
        check(nagramiXInlineTranslationTarget(shown) == "ru", "manual translation shown without chat auto")
        check(shown.text == "Hello world", "original untouched")
        check(!config.automatic, "manual display independent of auto")
        let encoder = PostboxEncoder(); translated.encode(encoder)
        check(TranslationMessageAttribute(decoder: PostboxDecoder(encoder.values)) == translated, "inline metadata roundtrip")
        let hidden = TranslationMessageAttribute(text: source.text, entities: entities, toLang: "ru",
            nagramiXInlineRevision: config.revision, nagramiXInlineSource: fingerprint, nagramiXInlineHidden: true)
        let hiddenEncoder = PostboxEncoder(); hidden.encode(hiddenEncoder)
        let hiddenCopy = TranslationMessageAttribute(decoder: PostboxDecoder(hiddenEncoder.values))
        check(hiddenCopy == hidden && hiddenCopy.nagramiXInlineHidden, "show original choice persisted")
        check(nagramiXInlineTranslationTarget(Message(text: source.text, attributes: source.attributes + [hidden])) == "ru", "original choice blocks auto overwrite")
        check(hidden != translated, "attribute equality includes manual state")
        let legacyEncoder = PostboxEncoder(); normal.encode(legacyEncoder)
        legacyEncoder.values.removeValue(forKey: "nxr"); legacyEncoder.values.removeValue(forKey: "nxs"); legacyEncoder.values.removeValue(forKey: "nxh")
        let legacyAttribute = TranslationMessageAttribute(decoder: PostboxDecoder(legacyEncoder.values))
        check(legacyAttribute == normal, "legacy decoding remains native")
        check(nagramiXInlineTranslationTarget(Message(text: "Edited", attributes: shown.attributes)) == nil, "edited text rejects stale translation")
        check(nagramiXInlineTranslationTarget(Message(text: source.text, attributes: [translated])) == nil, "changed entities reject stale translation")
        config.revision = "new-revision"; try persist()
        check(nagramiXInlineTranslationTarget(shown) == nil, "provider/settings revision invalidates display")
        config.revision = "test-revision"; config.enabled = false; try persist()
        check(nagramiXInlineTranslationTarget(shown) == nil, "master OFF disables manual display")
        defaults.set(Data("invalid".utf8), forKey: key)
        check(nagramiXInlineTranslationTarget(shown) == nil, "invalid settings fail closed")
        defaults.removeObject(forKey: key)
        check(nagramiXInlineTranslationTarget(shown) == nil, "absent settings fail closed")
        config.enabled = true; try persist()
        check(nagramiXInlineTranslationTarget(shown) == "ru", "configuration cache refreshes after restore")
        print("PASS: \(checks) inline attribute/configuration checks")
    }
}
