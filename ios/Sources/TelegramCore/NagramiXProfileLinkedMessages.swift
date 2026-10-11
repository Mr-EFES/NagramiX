import Foundation
import Postbox

// Только проверенный пользователь текущего аккаунта; недоступный ID не ломает отправку.
func nagramiXProfileLinkTarget(transaction: Transaction, accountPeerId: PeerId) -> PeerId? {
    let defaults = UserDefaults.standard
    guard defaults.object(forKey: "nagramix.messages.profileLinkEnabled") as? Bool ?? false else { return nil }
    let stored = defaults.string(forKey: "nagramix.messages.profileLinkUserId") ?? ""
    let targetId: PeerId
    if stored.isEmpty {
        targetId = accountPeerId
    } else {
        guard stored.utf8.allSatisfy({ $0 >= 48 && $0 <= 57 }), let value = Int64(stored), value > 0, value <= 0x00ff_ffff_ffff_ffff else { return nil }
        targetId = PeerId(namespace: Namespaces.Peer.CloudUser, id: PeerId.Id._internalFromInt64Value(value))
    }
    // Минимальный peer из чужого сообщения может иметь только контекстный hash.
    // Для ссылки в произвольном чате нужен полноценный доступ к выбранному user.
    guard let user = transaction.getPeer(targetId) as? TelegramUser,
          let accessHash = user.accessHash, case .personal = accessHash,
          apiInputUser(user) != nil else { return nil }
    return targetId
}

private let nagramiXProfileLinkDetector = try? NSDataDetector(types: NSTextCheckingResult.CheckingType.link.rawValue | NSTextCheckingResult.CheckingType.phoneNumber.rawValue)
private let nagramiXProfileLinkTokens = try? NSRegularExpression(pattern: #"(?<![\p{L}\p{N}_])(?:[@#\$][\p{L}\p{N}_]+|/[A-Za-z][A-Za-z0-9_]*(?:@[A-Za-z0-9_]+)?)"#)

// Смещения Telegram — UTF-16. Ссылки не пересекают сущности и границы суррогатных пар.
func nagramiXProfileLinkEntities(text: String, entities: [MessageTextEntity], linkType: MessageTextEntityType) -> [MessageTextEntity] {
    let units = Array(text.utf16)
    guard !units.isEmpty, units.count <= Int(Int32.max), entities.count < 100 else { return entities }
    func validBoundary(_ offset: Int) -> Bool {
        guard offset >= 0, offset <= units.count else { return false }
        if offset > 0, offset < units.count, (0xdc00...0xdfff).contains(units[offset]), (0xd800...0xdbff).contains(units[offset - 1]) { return false }
        return true
    }
    var boundaries: Set<Int> = [0, units.count]
    var blocked: [Range<Int>] = []
    for entity in entities {
        guard !entity.range.isEmpty, validBoundary(entity.range.lowerBound), validBoundary(entity.range.upperBound) else { return entities }
        boundaries.insert(entity.range.lowerBound)
        boundaries.insert(entity.range.upperBound)
        switch entity.type {
        case .Bold, .Italic, .Underline, .Strikethrough, .Spoiler, .BlockQuote:
            break
        default:
            blocked.append(entity.range)
        }
    }
    // Защищаем и автоматически распознаваемые ссылки/упоминания в обычном тексте.
    let fullRange = NSRange(location: 0, length: units.count)
    let detected = (nagramiXProfileLinkDetector?.matches(in: text, range: fullRange) ?? []).map { $0.range }
        + (nagramiXProfileLinkTokens?.matches(in: text, range: fullRange) ?? []).map { $0.range }
    for range in detected {
        let end = range.location + range.length
        guard range.length > 0, validBoundary(range.location), validBoundary(end) else { continue }
        blocked.append(range.location..<end)
        boundaries.insert(range.location)
        boundaries.insert(end)
    }
    let offsets = boundaries.sorted()
    let string = text as NSString
    var result = entities
    for index in 0..<(offsets.count - 1) {
        let range = offsets[index]..<offsets[index + 1]
        guard !blocked.contains(where: { $0.overlaps(range) }),
              !string.substring(with: NSRange(location: range.lowerBound, length: range.count)).trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { continue }
        guard result.count < 100 else { break }
        result.append(MessageTextEntity(range: range, type: linkType))
    }
    return result.sorted {
        if $0.range.lowerBound != $1.range.lowerBound { return $0.range.lowerBound < $1.range.lowerBound }
        return $0.range.upperBound > $1.range.upperBound
    }
}

func nagramiXProfileLinkedMessage(_ message: EnqueueMessage, targetPeerId: PeerId?, isSecretChat: Bool) -> EnqueueMessage {
    guard let targetPeerId, case let .message(text, attributes, _, _, _, _, _, _, _, _) = message,
          !text.isEmpty, !attributes.contains(where: { $0 is RichTextMessageAttribute || $0 is InlineBotMessageAttribute }) else { return message }
    let entityAttributes = attributes.compactMap { $0 as? TextEntitiesMessageAttribute }
    guard entityAttributes.count <= 1 else { return message }
    let original = entityAttributes.first?.entities ?? []
    // SecretChat не кодирует TextMention: сохраняем стандартную tg-ссылку вместо него.
    let linkType: MessageTextEntityType = isSecretChat
        ? .TextUrl(url: "tg://user?id=\(targetPeerId.id._internalGetInt64Value())")
        : .TextMention(peerId: targetPeerId)
    let updated = nagramiXProfileLinkEntities(text: text, entities: original, linkType: linkType)
    guard updated.count > original.count else { return message }
    return message.withUpdatedAttributes { attributes in
        var attributes = attributes.filter { !($0 is TextEntitiesMessageAttribute) }
        attributes.append(TextEntitiesMessageAttribute(entities: updated))
        return attributes
    }
}
