// Compile with the actual TranslationSettings declaration substituted below.
struct StringCodingKey: CodingKey, ExpressibleByStringLiteral {
    let stringValue: String
    let intValue: Int?
    init(stringLiteral value: String) { self.stringValue = value; self.intValue = nil }
    init?(stringValue: String) { self.stringValue = stringValue; self.intValue = nil }
    init?(intValue: Int) { self.stringValue = String(intValue); self.intValue = intValue }
}
// STRUCTURE
let fresh = TranslationSettings.defaultSettings
precondition(!fresh.showTranslate && !fresh.translateChats)
let enabled = try JSONDecoder().decode(TranslationSettings.self, from: Data("{\"showTranslate\":true,\"translateChats\":true}".utf8))
precondition(enabled.showTranslate && enabled.translateChats)
let disabled = try JSONDecoder().decode(TranslationSettings.self, from: Data("{\"showTranslate\":false,\"translateChats\":false}".utf8))
precondition(!disabled.showTranslate && !disabled.translateChats)
let legacy = try JSONDecoder().decode(TranslationSettings.self, from: Data("{\"showTranslate\":true}".utf8))
precondition(legacy.showTranslate && legacy.translateChats)
precondition(fresh.withUpdatedShowTranslate(true).showTranslate && !fresh.withUpdatedShowTranslate(true).translateChats)
precondition(fresh.withUpdatedTranslateChats(true).translateChats && !fresh.withUpdatedTranslateChats(true).showTranslate)
let roundTrip = try JSONDecoder().decode(TranslationSettings.self, from: JSONEncoder().encode(enabled))
precondition(roundTrip == enabled)
print("Telegram translation default/compatibility tests: OK")
