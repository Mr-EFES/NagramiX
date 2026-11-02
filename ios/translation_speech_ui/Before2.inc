import Foundation

struct NagramiXTranslationSpan {
    let range: Range<Int>
    let protected: Bool
}

// Entity offsets are UTF-16, as in Telegram. Protected fragments never leave
// the device; translated fragments retain the original formatting boundaries.
struct NagramiXTranslationTextPlan {
    let source: String
    let spans: [NagramiXTranslationSpan]
    let chunks: [String]
    let requested: [Int]
    private let boundaries: [Int]

    init(text: String, spans: [NagramiXTranslationSpan]) throws {
        let length = text.utf16.count
        guard length <= 32768, spans.count <= 256 else { throw NagramiXTranslationFailure.tooLarge }
        var protectedSpans = spans
        let detector = try NSRegularExpression(pattern: "(?i)(?:https?://|www\\.)[^\\s]+|(?:[\\p{L}\\p{N}](?:[\\p{L}\\p{N}-]*[\\p{L}\\p{N}])?\\.)+[\\p{L}]{2,63}(?:[/:?][^\\s]*)?|[\\w.+-]+@[\\w.-]+\\.[A-Za-z]{2,}|[@#][\\p{L}\\p{N}_]+")
        for match in detector.matches(in: text, range: NSRange(location: 0, length: length)) {
            protectedSpans.append(NagramiXTranslationSpan(range: match.range.location ..< NSMaxRange(match.range), protected: true))
        }
        guard protectedSpans.count <= 512 else { throw NagramiXTranslationFailure.tooLarge }
        var points: Set<Int> = [0, length]
        for span in protectedSpans {
            guard span.range.lowerBound >= 0, span.range.upperBound <= length, !span.range.isEmpty,
                  Range(NSRange(location: span.range.lowerBound, length: span.range.count), in: text) != nil else {
                throw NagramiXTranslationFailure.invalidText
            }
            points.insert(span.range.lowerBound); points.insert(span.range.upperBound)
        }
        let boundaries = points.sorted()
        var chunks: [String] = [], requested: [Int] = []
        for i in 0 ..< max(0, boundaries.count - 1) {
            let start = boundaries[i], end = boundaries[i + 1]
            guard let range = Range(NSRange(location: start, length: end - start), in: text) else { throw NagramiXTranslationFailure.invalidText }
            let chunk = String(text[range])
            let protected = protectedSpans.contains { $0.protected && $0.range.lowerBound <= start && $0.range.upperBound >= end }
            if !protected && chunk.unicodeScalars.contains(where: { CharacterSet.letters.contains($0) }) { requested.append(i) }
            chunks.append(chunk)
        }
        self.source = text; self.spans = spans; self.chunks = chunks
        self.requested = requested; self.boundaries = boundaries
    }
    var texts: [String] { self.requested.map { self.chunks[$0].trimmingCharacters(in: .whitespacesAndNewlines) } }

    func restore(_ translations: [String]) throws -> (String, [Range<Int>]) {
        guard translations.count == self.requested.count else { throw NagramiXTranslationFailure.invalidResponse }
        var chunks = self.chunks
        for (position, index) in self.requested.enumerated() {
            let value = translations[position].trimmingCharacters(in: .whitespacesAndNewlines)
            guard !value.isEmpty, value.utf16.count <= 65536 else { throw NagramiXTranslationFailure.invalidResponse }
            let old = chunks[index]
            chunks[index] = String(old.prefix(while: { $0.isWhitespace })) + value + String(old.reversed().prefix(while: { $0.isWhitespace }).reversed())
        }
        var offsets: [Int: Int] = [0: 0]
        var result = ""
        for (index, chunk) in chunks.enumerated() {
            result += chunk
            offsets[self.boundaries[index + 1]] = result.utf16.count
        }
        let ranges = try self.spans.map { span -> Range<Int> in
            guard let start = offsets[span.range.lowerBound], let end = offsets[span.range.upperBound], start < end else { throw NagramiXTranslationFailure.invalidResponse }
            return start ..< end
        }
        return (result, ranges)
    }
}
