import Foundation
import NaturalLanguage

@main struct Tests {
    static func main() {
        func recognize(_ text: String) -> [(String, Double)] {
            let recognizer = NLLanguageRecognizer(); recognizer.processString(text)
            return recognizer.languageHypotheses(withMaximum: 4).map { ($0.key.rawValue, $0.value) }
        }
        let russian = "Если вы стали свидетелем происшествия, сообщите об этом в дежурную часть полиции. Телефоны дежурных частей территориальных отделов полиции. Подать заявление можно в электронном виде."
        let english = "The latest update fixes several issues and improves the way messages are displayed. Thank you for helping us test this application and sharing your feedback with the team."
        let german = "Die neueste Aktualisierung behebt mehrere Fehler und verbessert die Darstellung der Nachrichten. Vielen Dank für Ihre Unterstützung und Ihre hilfreichen Rückmeldungen."
        precondition(NagramiXTranslationChatLanguage.detect([russian], target: "ru", ignored: ["ru"], recognize: recognize) == nil)
        precondition(NagramiXTranslationChatLanguage.detect([english], target: "ru", ignored: ["ru"], recognize: recognize) == "en")
        precondition(NagramiXTranslationChatLanguage.detect([german], target: "ru", ignored: ["ru"], recognize: recognize) == "de")
        precondition(NagramiXTranslationChatLanguage.detect(["Привет"], target: "ru", ignored: [], recognize: { _ in [("bg", 1)] }) == nil)
        var combined = false
        let result = NagramiXTranslationChatLanguage.detect(["Короткий текст", russian], target: "ru", ignored: [], recognize: { text in
            combined = text.contains("Короткий текст") && text.contains("полиции")
            return [("ru", 0.95), ("bg", 0.03)]
        })
        precondition(combined && result == nil)
        precondition(NagramiXTranslationChatLanguage.detect([english], target: "ru", ignored: ["en-US"], recognize: { _ in [("en", 0.95)] }) == nil)
        precondition(NagramiXTranslationChatLanguage.detect([german], target: "ru", ignored: [], recognize: { _ in [("de", 0.55), ("en", 0.42)] }) == nil)
        let screenshotText = "Телефоны дежурных частей территориальных отделов полиции. Подать заявление в электронном виде. Подписаться на ГУ МВД России по Херсонской области. Остальное пока в процессе работы."
        for wrong in ["bg", "kk", "uk", "en"] {
            precondition(NagramiXTranslationChatLanguage.detect([screenshotText], target: "ru", ignored: [], recognize: { _ in [(wrong, 0.99)] }) == nil)
        }
        let bulgarian = "Българският език е официалният език на Република България. Този текст съдържа информация за новите правила и възможностите за гражданите. Благодарим ви за вниманието и помощта."
        let kazakh = "Қазақстан Республикасының азаматтары жаңа ережелер туралы ақпаратты ресми сайттан ала алады. Бүгін барлық тұрғындарға арналған маңызды жаңалықтар жарияланды."
        let ukrainian = "Українська мова є державною мовою України. Сьогодні мешканці міста можуть отримати важливу інформацію та звернутися до місцевої служби підтримки. Дякуємо за увагу."
        precondition(NagramiXTranslationChatLanguage.detect([ukrainian], target: "ru", ignored: [], recognize: { _ in [("uk", 0.99)] }) == "uk")
        precondition(NagramiXTranslationChatLanguage.detect([bulgarian], target: "ru", ignored: [], recognize: { _ in [("bg", 0.99)] }) == "bg")
        precondition(NagramiXTranslationChatLanguage.detect([kazakh], target: "ru", ignored: [], recognize: { _ in [("kk", 0.99)] }) == "kk")
        precondition(NagramiXTranslationChatLanguage.detect([screenshotText], target: "en", ignored: [], recognize: { _ in [("bg", 0.99)] }) == "bg")
        print("Chat language detection tests passed")
    }
}
