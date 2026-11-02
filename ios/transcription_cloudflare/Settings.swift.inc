import Foundation

public enum NagramiXTranscriptionProvider: String, Codable, CaseIterable {
    case apple, whisper, groq, gemini, chatgpt, telegram, grok, cloudflare
    public var title: String {
        switch self {
        case .cloudflare: return "Cloudflare"
        case .apple: return "Apple"
        case .whisper: return "Whisper"
        case .groq: return "Groq"
        case .grok: return "Grok"
        case .gemini: return "Gemini"
        case .chatgpt: return "ChatGPT"
        case .telegram: return "Telegram"
        }
    }
    public var cloud: Bool { self == .groq || self == .gemini || self == .chatgpt || self == .grok || self == .cloudflare }
    public var defaultModel: String {
        switch self {
        case .cloudflare, .groq: return "whisper-large-v3-turbo"
        case .grok: return "grok-voice-transcribe-2.0"
        case .gemini: return "gemini-3.1-flash-lite"
        case .chatgpt: return "gpt-transcribe"
        default: return ""
        }
    }
}

public enum NagramiXWhisperModel: String, Codable, CaseIterable {
    case base, small
    case base_q8_0 = "base-q8_0"
    case base_full = "base-full"
    case large_v1 = "large-v1"
    case large_v2_q5_0 = "large-v2-q5_0"
    case large_v2_q8_0 = "large-v2-q8_0"
    case large_v2 = "large-v2"
    case large_v3_q5_0 = "large-v3-q5_0"
    case large_v3_turbo_q5_0 = "large-v3-turbo-q5_0"
    case large_v3_turbo_q8_0 = "large-v3-turbo-q8_0"
    case large_v3_turbo = "large-v3-turbo"
    case large_v3 = "large-v3"
    case medium_q5_0 = "medium-q5_0"
    case medium_q8_0 = "medium-q8_0"
    case medium = "medium"
    case small_q8_0 = "small-q8_0"
    case small_full = "small-full"
    case tiny_q5_1 = "tiny-q5_1"
    case tiny_q8_0 = "tiny-q8_0"
    case tiny = "tiny"
    case base_en_q5_1 = "base.en-q5_1"
    case base_en_q8_0 = "base.en-q8_0"
    case base_en = "base.en"
    case medium_en_q5_0 = "medium.en-q5_0"
    case medium_en_q8_0 = "medium.en-q8_0"
    case medium_en = "medium.en"
    case small_en_q5_1 = "small.en-q5_1"
    case small_en_q8_0 = "small.en-q8_0"
    case small_en = "small.en"
    case tiny_en_q5_1 = "tiny.en-q5_1"
    case tiny_en_q8_0 = "tiny.en-q8_0"
    case tiny_en = "tiny.en"
    private static let catalog: [Self: (String, Int64, String)] = [
        .base_en_q5_1: ("ggml-base.en-q5_1.bin", 59721011, "4baf70dd0d7c4247ba2b81fafd9c01005ac77c2f9ef064e00dcf195d0e2fdd2f"),
        .base_en_q8_0: ("ggml-base.en-q8_0.bin", 81781811, "a4d4a0768075e13cfd7e19df3ae2dbc4a68d37d36a7dad45e8410c9a34f8c87e"),
        .base_en: ("ggml-base.en.bin", 147964211, "a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002"),
        .medium_en_q5_0: ("ggml-medium.en-q5_0.bin", 539225533, "76733e26ad8fe1c7a5bf7531a9d41917b2adc0f20f2e4f5531688a8c6cd88eb0"),
        .medium_en_q8_0: ("ggml-medium.en-q8_0.bin", 823382461, "43fa2cd084de5a04399a896a9a7a786064e221365c01700cea4666005218f11c"),
        .medium_en: ("ggml-medium.en.bin", 1533774781, "cc37e93478338ec7700281a7ac30a10128929eb8f427dda2e865faa8f6da4356"),
        .small_en_q5_1: ("ggml-small.en-q5_1.bin", 190098681, "bfdff4894dcb76bbf647d56263ea2a96645423f1669176f4844a1bf8e478ad30"),
        .small_en_q8_0: ("ggml-small.en-q8_0.bin", 264477561, "67a179f608ea6114bd3fdb9060e762b588a3fb3bd00c4387971be4d177958067"),
        .small_en: ("ggml-small.en.bin", 487614201, "c6138d6d58ecc8322097e0f987c32f1be8bb0a18532a3f88f734d1bbf9c41e5d"),
        .tiny_en_q5_1: ("ggml-tiny.en-q5_1.bin", 32166155, "c77c5766f1cef09b6b7d47f21b546cbddd4157886b3b5d6d4f709e91e66c7c2b"),
        .tiny_en_q8_0: ("ggml-tiny.en-q8_0.bin", 43550795, "5bc2b3860aa151a4c6e7bb095e1fcce7cf12c7b020ca08dcec0c6d018bb7dd94"),
        .tiny_en: ("ggml-tiny.en.bin", 77704715, "921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f"),
        .base: ("ggml-base-q5_1.bin", 59707625, "422f1ae452ade6f30a004d7e5c6a43195e4433bc370bf23fac9cc591f01a8898"),
        .small: ("ggml-small-q5_1.bin", 190085487, "ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb"),
        .base_q8_0: ("ggml-base-q8_0.bin", 81768585, "c577b9a86e7e048a0b7eada054f4dd79a56bbfa911fbdacf900ac5b567cbb7d9"),
        .base_full: ("ggml-base.bin", 147951465, "60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe"),
        .large_v1: ("ggml-large-v1.bin", 3094623691, "7d99f41a10525d0206bddadd86760181fa920438b6b33237e3118ff6c83bb53d"),
        .large_v2_q5_0: ("ggml-large-v2-q5_0.bin", 1080732091, "3a214837221e4530dbc1fe8d734f302af393eb30bd0ed046042ebf4baf70f6f2"),
        .large_v2_q8_0: ("ggml-large-v2-q8_0.bin", 1656129691, "fef54e6d898246a65c8285bfa83bd1807e27fadf54d5d4e81754c47634737e8c"),
        .large_v2: ("ggml-large-v2.bin", 3094623691, "9a423fe4d40c82774b6af34115b8b935f34152246eb19e80e376071d3f999487"),
        .large_v3_q5_0: ("ggml-large-v3-q5_0.bin", 1081140203, "d75795ecff3f83b5faa89d1900604ad8c780abd5739fae406de19f23ecd98ad1"),
        .large_v3_turbo_q5_0: ("ggml-large-v3-turbo-q5_0.bin", 574041195, "394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2"),
        .large_v3_turbo_q8_0: ("ggml-large-v3-turbo-q8_0.bin", 874188075, "317eb69c11673c9de1e1f0d459b253999804ec71ac4c23c17ecf5fbe24e259a1"),
        .large_v3_turbo: ("ggml-large-v3-turbo.bin", 1624555275, "1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69"),
        .large_v3: ("ggml-large-v3.bin", 3095033483, "64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2"),
        .medium_q5_0: ("ggml-medium-q5_0.bin", 539212467, "19fea4b380c3a618ec4723c3eef2eb785ffba0d0538cf43f8f235e7b3b34220f"),
        .medium_q8_0: ("ggml-medium-q8_0.bin", 823369779, "42a1ffcbe4167d224232443396968db4d02d4e8e87e213d3ee2e03095dea6502"),
        .medium: ("ggml-medium.bin", 1533763059, "6c14d5adee5f86394037b4e4e8b59f1673b6cee10e3cf0b11bbdbee79c156208"),
        .small_q8_0: ("ggml-small-q8_0.bin", 264464607, "49c8fb02b65e6049d5fa6c04f81f53b867b5ec9540406812c643f177317f779f"),
        .small_full: ("ggml-small.bin", 487601967, "1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b"),
        .tiny_q5_1: ("ggml-tiny-q5_1.bin", 32152673, "818710568da3ca15689e31a743197b520007872ff9576237bda97bd1b469c3d7"),
        .tiny_q8_0: ("ggml-tiny-q8_0.bin", 43537433, "c2085835d3f50733e2ff6e4b41ae8a2b8d8110461e18821b09a15c40c42d1cca"),
        .tiny: ("ggml-tiny.bin", 77691713, "be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21"),
    ]
    public var fileName: String { Self.catalog[self]!.0 }
    public var size: Int64 { Self.catalog[self]!.1 }
    public var englishOnly: Bool { self.fileName.contains(".en") }
    public var sha256: String { Self.catalog[self]!.2 }
    public var title: String { self.fileName.replacingOccurrences(of: "ggml-", with: "").replacingOccurrences(of: ".bin", with: "") }
    public var url: URL { URL(string: "https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/\(self.fileName)")! }
}

public struct NagramiXTranscriptionConfiguration: Codable, Equatable {
    public var enabled = false
    public var automatic = false
    public var localFallback: Bool?
    public var provider: NagramiXTranscriptionProvider = .apple
    public var language = "ru-RU"
    public var whisper: NagramiXWhisperModel = .base_full
    public var wifiOnly = true
    public var cloudAllowed: [String: Bool] = [:]
    public var models: [String: String] = [:]
    public var credentialRevision = "initial"
    public var revision = "initial"
    public init() {}
    public var model: String { self.provider == .whisper ? self.whisper.rawValue : (self.models[self.provider.rawValue] ?? self.provider.defaultModel) }
    public var cacheTag: String { [self.provider.rawValue, self.model, self.language, self.credentialRevision].joined(separator: ":") + (self.localFallback == true ? ":fallback" : "") }
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
    case unavailableMedia, tooLarge, noSpeech, network, quota, authorization, invalidResponse, busy, storage, insufficientMemory
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
        case .insufficientMemory: return "Недостаточно доступной памяти для этой модели. Выберите модель меньшего размера и повторите попытку."
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
