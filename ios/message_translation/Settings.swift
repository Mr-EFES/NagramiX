import Foundation

public enum NagramiXTranslationProvider: String, Codable, CaseIterable {
    case apple, google, yandex, gemini, chatgpt, deepseek

    public var title: String {
        switch self {
        case .apple: return "Apple"
        case .google: return "Google"
        case .yandex: return "Яндекс"
        case .gemini: return "Gemini"
        case .chatgpt: return "ChatGPT"
        case .deepseek: return "DeepSeek"
        }
    }
    public var defaultModel: String {
        switch self {
        case .gemini: return "gemini-3.1-flash-lite"
        case .chatgpt: return "gpt-5-mini"
        case .deepseek: return "deepseek-flash"
        default: return ""
        }
    }
    public var isLanguageModel: Bool { self == .gemini || self == .chatgpt || self == .deepseek }
}

public struct NagramiXTranslationConfiguration: Codable, Equatable {
    public var enabled = false
    public var automatic = false
    public var provider: NagramiXTranslationProvider = .apple
    public var target = ""
    public var ignored: [String] = []
    public var models: [String: String] = [:]
    public var revision = UUID().uuidString

    public init() {}
    public var model: String { self.models[self.provider.rawValue] ?? self.provider.defaultModel }
}

public struct NagramiXTranslationChatChoice: Codable, Equatable {
    public var enabled: Bool?
    public var target: String?
    public var hidden = false
    public init() {}
}

public enum NagramiXTranslationSettings {
    public static let changed = Notification.Name("NagramiXTranslationSettingsChanged")
    private static let key = "nagramix.translation.configuration.v1"
    private static let chatsKey = "nagramix.translation.chats.v1"
    private static let lock = NSRecursiveLock()

    public static var current: NagramiXTranslationConfiguration {
        self.lock.lock(); defer { self.lock.unlock() }
        guard let data = UserDefaults.standard.data(forKey: self.key),
              let value = try? JSONDecoder().decode(NagramiXTranslationConfiguration.self, from: data) else {
            var value = NagramiXTranslationConfiguration()
            value.revision = "initial"
            return value
        }
        return value
    }
    public static func update(_ transform: (inout NagramiXTranslationConfiguration) -> Void) {
        self.lock.lock()
        var value = self.current
        let previous = value
        transform(&value)
        guard value != previous else { self.lock.unlock(); return }
        value.revision = UUID().uuidString
        guard let data = try? JSONEncoder().encode(value) else { self.lock.unlock(); return }
        UserDefaults.standard.set(data, forKey: self.key)
        self.lock.unlock()
        NotificationCenter.default.post(name: self.changed, object: nil)
    }
    public static func credentialsChanged() {
        self.update { $0.revision = UUID().uuidString }
    }
    public static func chatKey(account: Int64, peer: Int64, thread: Int64?) -> String {
        return "\(account):\(peer):\(thread.map(String.init) ?? "peer")"
    }
    private static func chats() -> [String: NagramiXTranslationChatChoice] {
        guard let data = UserDefaults.standard.data(forKey: self.chatsKey),
              let values = try? JSONDecoder().decode([String: NagramiXTranslationChatChoice].self, from: data) else { return [:] }
        return values
    }
    public static func chat(_ key: String) -> NagramiXTranslationChatChoice {
        self.lock.lock(); defer { self.lock.unlock() }
        return self.chats()[key] ?? NagramiXTranslationChatChoice()
    }
    public static func updateChat(_ key: String, _ transform: (inout NagramiXTranslationChatChoice) -> Void) {
        self.lock.lock()
        var values = self.chats()
        var choice = values[key] ?? NagramiXTranslationChatChoice()
        let old = choice
        transform(&choice)
        guard choice != old else { self.lock.unlock(); return }
        values[key] = choice
        guard let data = try? JSONEncoder().encode(values) else { self.lock.unlock(); return }
        UserDefaults.standard.set(data, forKey: self.chatsKey)
        self.lock.unlock()
        NotificationCenter.default.post(name: self.changed, object: nil)
    }
    public static func revealPanels() {
        self.lock.lock()
        var values = self.chats()
        for key in Array(values.keys) { values[key]?.hidden = false }
        if let data = try? JSONEncoder().encode(values) { UserDefaults.standard.set(data, forKey: self.chatsKey) }
        self.lock.unlock()
        NotificationCenter.default.post(name: self.changed, object: nil)
    }
}

public enum NagramiXTranslationLanguage {
    public static func base(_ code: String) -> String {
        let value = code.replacingOccurrences(of: "_", with: "-").lowercased().split(separator: "-").first.map(String.init) ?? ""
        return value == "nb" ? "no" : (value == "iw" ? "he" : value)
    }
    public static func title(_ code: String, interface: String) -> String {
        let locale = Locale(identifier: interface)
        let value = locale.localizedString(forLanguageCode: code) ?? code
        return value.prefix(1).uppercased(with: locale) + value.dropFirst()
    }
    public static func badge(_ code: String) -> String {
        let value = self.base(code)
        return ["auto":"АВТО", "en":"ENG", "ru":"RUS", "de":"DEU", "fr":"FRA", "es":"SPA", "it":"ITA", "pt":"POR", "zh":"ZHO", "ja":"JPN", "ko":"KOR", "ar":"ARA", "uk":"UKR", "tr":"TUR", "pl":"POL"][value] ?? value.uppercased()
    }
    // Recognition is separate so this policy can be checked without Apple's ML runtime.
    public static func accepted(_ hypotheses: [(String, Double)], interface: String, ignored: [String]) -> String? {
        let sorted = hypotheses.filter { $0.1.isFinite && $0.1 >= 0 }.sorted { $0.1 > $1.1 }
        guard let first = sorted.first, first.1 >= 0.65,
              sorted.count == 1 || first.1 - sorted[1].1 >= 0.15 else { return nil }
        let code = self.base(first.0)
        guard !code.isEmpty, code != "und", code != self.base(interface),
              !ignored.contains(where: { self.base($0) == code }) else { return nil }
        return code
    }
    public static func recognitionText(_ text: String) -> String {
        let source = String(text.prefix(4096))
        let stripped = source.replacingOccurrences(of: "(?i)(?:https?://|www\\.)\\S+|(?:[\\p{L}\\p{N}](?:[\\p{L}\\p{N}-]*[\\p{L}\\p{N}])?\\.)+[\\p{L}]{2,63}(?:[/:?][^\\s]*)?|[\\w.+-]+@[\\w.-]+\\.[A-Za-z]{2,}|[@#][\\p{L}\\p{N}_]+", with: " ", options: .regularExpression)
        guard stripped.unicodeScalars.filter({ CharacterSet.letters.contains($0) }).count >= 2 else { return "" }
        return stripped
    }
}
