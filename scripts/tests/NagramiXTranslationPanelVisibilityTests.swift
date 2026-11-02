import Foundation

@main struct Tests {
    static func main() throws {
        var configuration = NagramiXTranslationConfiguration()
        precondition(nagramiXTranslationPanelAllowed(configuration))
        configuration.enabled = true
        configuration.automatic = true
        configuration.showTranslateButton = false
        precondition(!nagramiXTranslationPanelAllowed(configuration))
        precondition(configuration.automatic)
        let source = NagramiXTranslationLanguage.accepted([("en", 0.99)], interface: "ru", ignored: ["ru"])
        precondition(source == "en")
        precondition(NagramiXTranslationLanguage.accepted([("ru", 0.99)], interface: "ru", ignored: ["ru"]) == nil)
        precondition(NagramiXTranslationLanguage.accepted([("en", 0.99)], interface: "ru", ignored: ["en"]) == nil)
        let data = try JSONEncoder().encode(configuration)
        let restored = try JSONDecoder().decode(NagramiXTranslationConfiguration.self, from: data)
        precondition(restored.showTranslateButton == false && restored.automatic && !nagramiXTranslationPanelAllowed(restored))
        configuration.showTranslateButton = true
        precondition(nagramiXTranslationPanelAllowed(configuration) && configuration.automatic)
        configuration.enabled = false
        configuration.showTranslateButton = false
        precondition(nagramiXTranslationPanelAllowed(configuration))
        print("Панель перевода и независимый перевод сообщения: проверки пройдены")
    }
}
