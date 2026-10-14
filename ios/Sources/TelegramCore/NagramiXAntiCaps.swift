import Foundation
import Postbox

private let nagramiXAntiCapsDetector = try? NSDataDetector(types: NSTextCheckingResult.CheckingType.link.rawValue | NSTextCheckingResult.CheckingType.phoneNumber.rawValue)
private let nagramiXAntiCapsTokens = try? NSRegularExpression(pattern: #"(?<![\p{L}\p{N}_])(?:[@#\$][\p{L}\p{N}_]+|/[A-Za-z][A-Za-z0-9_]*(?:@[A-Za-z0-9_]+)?)"#)

// nil означает: оставить исходный текст и сущности без изменений.
func nagramiXAntiCapsText(_ text: String, entities: [MessageTextEntity]) -> (text: String, entities: [MessageTextEntity])? {
    let units = Array(text.utf16)
    guard !units.isEmpty, units.count <= Int(Int32.max),
          let detector = nagramiXAntiCapsDetector, let tokens = nagramiXAntiCapsTokens else { return nil }
    func validBoundary(_ offset: Int) -> Bool {
        guard offset >= 0, offset <= units.count else { return false }
        return !(offset > 0 && offset < units.count && (0xdc00...0xdfff).contains(units[offset]) && (0xd800...0xdbff).contains(units[offset - 1]))
    }
    var protected: [Range<Int>] = []
    for entity in entities {
        guard !entity.range.isEmpty, validBoundary(entity.range.lowerBound), validBoundary(entity.range.upperBound) else { return nil }
        switch entity.type {
        case .Bold, .Italic, .Underline, .Strikethrough, .Spoiler, .BlockQuote:
            break
        default:
            // URL, упоминания, команды, code/pre и custom emoji не переписываем.
            protected.append(entity.range)
        }
    }
    let fullRange = NSRange(location: 0, length: units.count)
    for match in detector.matches(in: text, range: fullRange) + tokens.matches(in: text, range: fullRange) {
        let range = match.range.location..<(match.range.location + match.range.length)
        guard !range.isEmpty, validBoundary(range.lowerBound), validBoundary(range.upperBound) else { return nil }
        protected.append(range)
    }
    var merged: [Range<Int>] = []
    for range in protected.sorted(by: { $0.lowerBound < $1.lowerBound }) {
        if let last = merged.last, last.upperBound >= range.lowerBound {
            merged[merged.count - 1] = last.lowerBound..<max(last.upperBound, range.upperBound)
        } else {
            merged.append(range)
        }
    }
    var runs: [(range: Range<Int>, protected: Bool)] = []
    var end = 0
    for range in merged {
        if end < range.lowerBound { runs.append((end..<range.lowerBound, false)) }
        runs.append((range, true))
        end = range.upperBound
    }
    if end < units.count { runs.append((end..<units.count, false)) }
    let string = text as NSString
    var letterCount = 0
    var firstLetter: Int?
    for run in runs where !run.protected {
        var offset = run.range.lowerBound
        let part = string.substring(with: NSRange(location: offset, length: run.range.count))
        for scalar in part.unicodeScalars {
            let value = String(scalar)
            if CharacterSet.letters.contains(scalar), value.lowercased() != value.uppercased() {
                // Смешанный регистр — осознанный текст, его не меняем.
                guard value == value.uppercased() else { return nil }
                letterCount += 1
                if firstLetter == nil { firstLetter = offset }
            }
            offset += value.utf16.count
        }
    }
    guard letterCount >= 4, let firstLetter else { return nil }

    // Unicode lowercase может менять длину (İ → i + combining dot).
    // Пересчитываем UTF-16 границы сущностей, включая вложенное форматирование.
    var offsets = [Int?](repeating: nil, count: units.count + 1)
    var result = ""
    var resultLength = 0
    for run in runs {
        let part = string.substring(with: NSRange(location: run.range.lowerBound, length: run.range.count))
        var converted = run.protected ? part : part.lowercased()
        var originalOffset = run.range.lowerBound
        var convertedOffset = 0
        for scalar in part.unicodeScalars {
            let value = String(scalar)
            let lowered = run.protected ? value : value.lowercased()
            offsets[originalOffset] = resultLength + convertedOffset
            if originalOffset == firstLetter {
                converted = (converted as NSString).replacingCharacters(in: NSRange(location: convertedOffset, length: lowered.utf16.count), with: value)
                convertedOffset += value.utf16.count
            } else {
                convertedOffset += lowered.utf16.count
            }
            originalOffset += value.utf16.count
            offsets[originalOffset] = resultLength + convertedOffset
        }
        // Контекстный lowercase (например, греческая конечная ς) выполняется
        // для всей строки участка; неизвестное изменение длины не портит разметку.
        guard convertedOffset == converted.utf16.count else { return nil }
        result += converted
        resultLength += convertedOffset
    }
    guard result != text else { return nil }
    var updated: [MessageTextEntity] = []
    for entity in entities {
        guard let lower = offsets[entity.range.lowerBound], let upper = offsets[entity.range.upperBound], lower < upper else { return nil }
        updated.append(MessageTextEntity(range: lower..<upper, type: entity.type))
    }
    return (result, updated)
}

func nagramiXAntiCapsMessage(_ message: EnqueueMessage, enabled: Bool, limits: UserLimitsConfiguration = .defaultValue) -> EnqueueMessage {
    guard enabled,
          case let .message(text, attributes, inlineStickers, mediaReference, threadId, replyToMessageId, replyToStoryId, localGroupingKey, correlationId, bubbleUpEmojiOrStickersets) = message,
          !attributes.contains(where: { $0 is RichTextMessageAttribute || $0 is InlineBotMessageAttribute }) else { return message }
    let entityAttributes = attributes.compactMap { $0 as? TextEntitiesMessageAttribute }
    guard entityAttributes.count <= 1,
          let result = nagramiXAntiCapsText(text, entities: entityAttributes.first?.entities ?? []) else { return message }
    let limit = mediaReference == nil ? limits.maxMessageLength : limits.maxCaptionLength
    // Не увеличиваем уже разбитое сообщение/подпись за разрешённый предел.
    guard result.text.utf16.count <= max(0, Int(limit)) else { return message }
    var updatedAttributes = attributes.filter { !($0 is TextEntitiesMessageAttribute) }
    if !result.entities.isEmpty { updatedAttributes.append(TextEntitiesMessageAttribute(entities: result.entities)) }
    return .message(text: result.text, attributes: updatedAttributes, inlineStickers: inlineStickers, mediaReference: mediaReference, threadId: threadId, replyToMessageId: replyToMessageId, replyToStoryId: replyToStoryId, localGroupingKey: localGroupingKey, correlationId: correlationId, bubbleUpEmojiOrStickersets: bubbleUpEmojiOrStickersets)
}
