import Foundation

@main struct Tests {
    static func main() {
        func source(_ detected: String?, _ chat: String?, _ target: String = "ru", _ ignored: [String] = ["ru"]) -> String? {
            return NagramiXTranslationChatLanguage.messageSource(detected: detected, chatSource: chat, target: target, ignored: ignored)
        }
        precondition(source(nil, "en") == "en")
        precondition(source("de", "en") == "de")
        precondition(source("ru", "en") == nil)
        precondition(source("fr", "en", "ru", ["ru", "fr-FR"]) == nil)
        precondition(source(nil, "ru") == nil)
        precondition(source(nil, nil) == nil)
        precondition(source(nil, "auto") == nil)
        precondition(source(nil, "en-US", "ru", ["ru"]) == "en")
        print("Автоматический выбор языка сообщения: проверки пройдены")
    }
}
