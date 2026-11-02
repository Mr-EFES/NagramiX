import Foundation

enum NagramiXTranslationFailure: Error { case tooLarge, invalidText, invalidResponse }

@main struct NagramiXTranslationSpacingTests {
    static func main() throws {
        let one = try NagramiXTranslationTextPlan(text: "First\nSecond", spans: [])
        let corrected = try one.restore(["Первый\n\nВторой"])
        precondition(corrected.0 == "Первый\nВторой")
        let paragraphs = try NagramiXTranslationTextPlan(text: "First\n\nSecond", spans: [])
        let kept = try paragraphs.restore(["Первый\n\nВторой"])
        precondition(kept.0 == "Первый\n\nВторой")
        let formatted = try NagramiXTranslationTextPlan(text: "Hello world", spans: [.init(range: 6 ..< 11, protected: false)])
        let result = try formatted.restore(["Привет", "мир"])
        precondition(result.0 == "Привет мир" && result.1 == [7 ..< 10])
    }
}
