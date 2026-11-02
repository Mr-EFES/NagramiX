import Foundation

public enum NagramiXTranscriptionProvider: String, Codable, CaseIterable {
    case apple, whisper, groq, gemini, chatgpt, telegram
    public var title: String {
        switch self {
        case .apple: return "Apple"
        case .whisper: return "Whisper"
        case .groq: return "Groq"
        case .gemini: return "Gemini"
        case .chatgpt: return "ChatGPT"
        case .telegram: return "Telegram"
        }
    }
    public var cloud: Bool { self == .groq || self == .gemini || self == .chatgpt }
    public var defaultModel: String {
        switch self {
        case .groq: return "whisper-large-v3-turbo"
        case .gemini: return "gemini-3.1-flash-lite"
        case .chatgpt: return "gpt-transcribe"
        default: return ""
        }
    }
}

public enum NagramiXWhisperModel: String, Codable, CaseIterable {
    case base, small
    public var title: String { self == .base ? "Стандарт" : "Высокое" }
    public var fileName: String { "ggml-\(self.rawValue)-q5_1.bin" }
    public var size: Int64 { self == .base ? 59_707_625 : 190_085_487 }
    public var sha256: String {
        self == .base ? "422f1ae452ade6f30a004d7e5c6a43195e4433bc370bf23fac9cc591f01a8898" : "ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb"
    }
    public var url: URL { URL(string: "https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/\(self.fileName)")! }
}

public struct NagramiXTranscriptionConfiguration: Codable, Equatable {
    public var enabled = false
    public var automatic = false
    public var provider: NagramiXTranscriptionProvider = .apple
    public var language = "ru-RU"
    public var whisper: NagramiXWhisperModel = .base
    public var wifiOnly = true
    public var cloudAllowed: [String: Bool] = [:]
    public var models: [String: String] = [:]
    public var credentialRevision = "initial"
    public var revision = "initial"
    public init() {}
    public var model: String { self.provider == .whisper ? self.whisper.rawValue : (self.models[self.provider.rawValue] ?? self.provider.defaultModel) }
    public var cacheTag: String { [self.provider.rawValue, self.model, self.language, self.credentialRevision].joined(separator: ":") }
}

public enum NagramiXTranscriptionSettings {
    public static let changed = Notification.Name("NagramiXTranscriptionSettingsChanged")
    private static let key = "nagramix.transcription.configuration.v1"
    private static let lock = NSRecursiveLock()
    public static var current: NagramiXTranscriptionConfiguration {
        self.lock.lock(); defer { self.lock.unlock() }
        guard let data = UserDefaults.standard.data(forKey: self.key), let value = try? JSONDecoder().decode(NagramiXTranscriptionConfiguration.self, from: data) else { return .init() }
        return value
    }
    public static func update(_ transform: (inout NagramiXTranscriptionConfiguration) -> Void) {
        self.lock.lock()
        var value = self.current; let previous = value
        transform(&value)
        guard value != previous else { self.lock.unlock(); return }
        value.revision = UUID().uuidString
        guard let data = try? JSONEncoder().encode(value) else { self.lock.unlock(); return }
        UserDefaults.standard.set(data, forKey: self.key); self.lock.unlock()
        NotificationCenter.default.post(name: self.changed, object: nil)
    }
    public static func credentialsChanged() { self.update { $0.credentialRevision = UUID().uuidString } }
}

public enum NagramiXTranscriptionFailure: Error, Equatable {
    case cancelled, disabled, unavailable, language, permission, missingModel, missingKey, cloudPermission
    case unavailableMedia, tooLarge, noSpeech, network, quota, authorization, invalidResponse, busy, storage
    public var text: String {
        switch self {
        case .cancelled: return "Расшифровка отменена."
        case .disabled: return "Расшифровка сообщений выключена."
        case .unavailable: return "Распознавание Apple на устройстве недоступно для этого языка. Выберите другой язык или загрузите Whisper."
        case .language: return "Выберите поддерживаемый язык речи. Автоопределение доступно для Whisper и облачных сервисов."
        case .permission: return "Разрешите распознавание речи в настройках iPhone."
        case .missingModel: return "Сначала загрузите выбранную модель в разделе «Языки и модели»."
        case .missingKey: return "Добавьте свой API-ключ выбранного сервиса. Для бесплатной квоты он тоже нужен."
        case .cloudPermission: return "Разрешите передачу аудио выбранному сервису в настройках расшифровки."
        case .unavailableMedia: return "Запись недоступна для расшифровки."
        case .tooLarge: return "Слишком большая запись. Поддерживаются записи до 15 минут и аудиофайлы до 25 МБ."
        case .noSpeech: return "Речь не обнаружена."
        case .network: return "Не удалось получить расшифровку. Проверьте подключение и повторите попытку."
        case .quota: return "Лимит сервиса исчерпан. Попробуйте позже или выберите другой распознаватель."
        case .authorization: return "Проверьте ключ и доступ к выбранной модели."
        case .invalidResponse: return "Сервис вернул неполный ответ. Исходная запись сохранена."
        case .busy: return "Очередь расшифровки заполнена. Попробуйте позже."
        case .storage: return "Не удалось подготовить или сохранить файл. Проверьте свободное место."
        }
    }
}

// Cancellation is safe across media IO, URLSession, Swift Tasks and C++ inference.
public final class NagramiXTranscriptionCancellation {
    private let lock = NSLock()
    private var cancelledValue = false
    private var actions: [() -> Void] = []
    public init() {}
    public var cancelled: Bool { self.lock.lock(); defer { self.lock.unlock() }; return self.cancelledValue }
    public func add(_ action: @escaping () -> Void) {
        self.lock.lock()
        if self.cancelledValue { self.lock.unlock(); action() } else { self.actions.append(action); self.lock.unlock() }
    }
    public func cancel() {
        self.lock.lock(); guard !self.cancelledValue else { self.lock.unlock(); return }
        self.cancelledValue = true; let actions = self.actions; self.actions.removeAll(); self.lock.unlock()
        actions.forEach { $0() }
    }
}
