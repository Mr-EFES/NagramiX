import Foundation

// A bounded combined sample gives the language recognizer context and prevents
// a single short message from dominating after target-language votes are lost.
enum NagramiXTranslationChatLanguage {
    static func detect(_ messages: [String], target: String, ignored: [String], recognize: (String) -> [(String, Double)]) -> String? {
        let sample = messages.suffix(32).map { NagramiXTranslationLanguage.recognitionText(String($0.prefix(512))) }.filter { !$0.isEmpty }.joined(separator: "\n")
        let bounded = String(sample.suffix(8192))
        guard bounded.unicodeScalars.filter({ CharacterSet.letters.contains($0) }).count >= 40 else { return nil }
        return NagramiXTranslationLanguage.accepted(recognize(bounded), interface: target, ignored: ignored)
    }
}
