import Foundation

@main struct TranslationCompletionTests {
    static func main() throws {
        let ignored = ["ru_RU", "EN-us", "iw"]
        precondition(NagramiXTranslationLanguage.isExcluded("ru", ignored: ignored))
        precondition(NagramiXTranslationLanguage.isExcluded("en-GB", ignored: ignored))
        precondition(NagramiXTranslationLanguage.isExcluded("he", ignored: ignored))
        precondition(!NagramiXTranslationLanguage.isExcluded("fr", ignored: ignored))
        precondition(!NagramiXTranslationLanguage.isExcluded("", ignored: ignored))
        var config = NagramiXTranslationConfiguration()
        precondition(config.appleSource == nil && config.showsTranslateButton)
        config.appleSource = "de"
        let data = try JSONEncoder().encode(config)
        let decoded = try JSONDecoder().decode(NagramiXTranslationConfiguration.self, from: data)
        precondition(decoded.appleSource == "de")
        var legacy = try JSONSerialization.jsonObject(with: data) as! [String: Any]
        legacy.removeValue(forKey: "appleSource"); legacy.removeValue(forKey: "showTranslateButton")
        let oldData = try JSONSerialization.data(withJSONObject: legacy)
        let migrated = try JSONDecoder().decode(NagramiXTranslationConfiguration.self, from: oldData)
        precondition(migrated.appleSource == nil && migrated.showsTranslateButton)
        print("PASS: language exclusions and legacy settings")
    }
}
