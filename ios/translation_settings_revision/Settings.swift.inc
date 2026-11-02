import Foundation

public enum NagramiXTranslationProvider: String, Codable, CaseIterable {
    case apple, google, yandex, gemini, chatgpt, deepseek, gptoss

    public var title: String {
        switch self {
        case .apple: return "Apple"
        case .google: return "Google"
        case .yandex: return "Яндекс"
        case .gemini: return "Gemini"
        case .chatgpt: return "ChatGPT"
        case .deepseek: return "DeepSeek"
        case .gptoss: return "Pollinations"
        }
    }
    public var defaultModel: String {
        switch self {
        case .gemini: return "gemini-3.1-flash-lite"
        case .chatgpt: return "gpt-5.4-mini"
        case .deepseek: return "deepseek-flash"
        case .gptoss: return "gpt-oss-20b"
        default: return ""
        }
    }
    public var isLanguageModel: Bool { self == .gemini || self == .chatgpt || self == .deepseek || self == .gptoss }
    public var requiresAPIKey: Bool { self == .gemini || self == .chatgpt || self == .deepseek }
    public var isFreeWeb: Bool { self == .google || self == .yandex }
    public func supportsTemperature(model: String) -> Bool {
        switch self {
        case .gptoss: return model == self.defaultModel
        case .deepseek: return model == "deepseek-flash" || model == "deepseek-v4-pro"
        case .gemini:
            return ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro", "gemini-3.1-flash-lite"].contains(model)
        case .chatgpt:
            return ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-5.1", "gpt-5.2", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano"].contains(model)
        default: return false
        }
    }
}

public struct NagramiXTranslationConfiguration: Codable, Equatable {
    public var enabled = false
    public var automatic = false
    // Optional preserves configurations saved before this setting existed.
    public var showTranslateButton: Bool?
    public var showsTranslateButton: Bool { self.showTranslateButton ?? true }
    public var provider: NagramiXTranslationProvider = .apple
    public var target = ""
    public var ignored: [String] = []
    public var models: [String: String] = [:]
    // Optional for backwards-compatible decoding of the v1 configuration.
    public var temperatures: [String: Double]?
    public var revision = UUID().uuidString

    public init() {}
    public var model: String { self.provider == .gptoss ? self.provider.defaultModel : (self.models[self.provider.rawValue] ?? self.provider.defaultModel) }
    public func temperature(for provider: NagramiXTranslationProvider) -> Double {
        let value = self.temperatures?[provider.rawValue] ?? (provider == .gemini ? 1.0 : 0.2)
        return value.isFinite ? min(2.0, max(0.0, (value * 10).rounded() / 10)) : 0.2
    }
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
