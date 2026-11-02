import Foundation

// Only suppress an uncertain Cyrillic misclassification when the sample has
// substantial independent evidence of Russian. Cyrillic alone is not enough:
// Bulgarian, Ukrainian, Kazakh and many other languages use the same script.
enum NagramiXTranslationChatLanguage {
    private static let russianEvidence: Set<String> = [
        "если", "чтобы", "который", "которая", "которые", "которого", "которых", "потому", "поэтому", "можно", "нужно", "нельзя", "сегодня", "завтра", "вчера", "пожалуйста", "спасибо", "сообщение", "сообщения", "сообщений", "переписка", "написано", "написать", "получить", "отправить", "отправлено", "россии", "российской", "российский", "территориальных", "отделов", "полиции", "дежурных", "дежурную", "заявление", "подать", "подписаться", "электронном", "происшествия", "сообщите", "телефоны", "обращения", "обращение", "области", "здравствуйте", "необходимо", "будет", "будут", "вашего", "своего", "своих", "меня", "тебя", "сейчас"
    ]
    private static func hasStrongRussianEvidence(_ text: String) -> Bool {
        let letters = text.unicodeScalars.filter { CharacterSet.letters.contains($0) }
        guard letters.count >= 80 else { return false }
        let cyrillic = letters.filter { (0x0400...0x052f).contains($0.value) }.count
        guard Double(cyrillic) / Double(letters.count) >= 0.70 else { return false }
        guard let regex = try? NSRegularExpression(pattern: "\\p{L}+", options: []) else { return false }
        let range = NSRange(text.startIndex..., in: text)
        let words = regex.matches(in: text, range: range).compactMap { match -> String? in
            guard let range = Range(match.range, in: text) else { return nil }
            return String(text[range]).lowercased()
        }
        guard words.count >= 12 else { return false }
        let matches = words.filter { russianEvidence.contains($0) }
        return matches.count >= 4 && Set(matches).count >= 4 && Double(matches.count) / Double(words.count) >= 0.09
    }
    static func detect(_ messages: [String], target: String, ignored: [String], recognize: (String) -> [(String, Double)]) -> String? {
        let sample = messages.suffix(32).map { NagramiXTranslationLanguage.recognitionText(String($0.prefix(512))) }.filter { !$0.isEmpty }.joined(separator: "\n")
        let bounded = String(sample.suffix(8192))
        guard bounded.unicodeScalars.filter({ CharacterSet.letters.contains($0) }).count >= 40 else { return nil }
        guard let detected = NagramiXTranslationLanguage.accepted(recognize(bounded), interface: target, ignored: ignored) else { return nil }
        if NagramiXTranslationLanguage.base(target) == "ru" && hasStrongRussianEvidence(bounded) { return nil }
        return detected
    }
}
