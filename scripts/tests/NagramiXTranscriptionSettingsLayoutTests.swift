import Foundation

final class NagramiXWhisperModels {
    static let shared = NagramiXWhisperModels()
    func status(_ model: NagramiXWhisperModel) -> String { return model.rawValue }
}
enum NagramiXWhisperLicense { static let text = "MIT" }

final class SettingsLayoutHarness {
    // ACTUAL_TYPES
    var page: Page = .settings
    var selectedModel = "selected"
    var appleSupported: [Locale] = []
    var appleInstalled: Set<String> = []
    var appleLoading: String?
    var appleHasManagedDownloads = true
    static let whisperLanguages = ["en", "ru", "de"]
    static func label(_ code: String) -> String { return code }
    func appleHas(_ code: String) -> Bool { return appleInstalled.contains(code) }
    // ACTUAL_SECTIONS
    func run() {
        for provider in NagramiXTranscriptionProvider.allCases {
            NagramiXTranscriptionSettings.update { $0.provider = provider }
            self.page = .settings
            let sections = self.makeSections()
            precondition(sections.count == 4 && sections[1].0 == "TELEGRAM" && sections[2].0 == "НА УСТРОЙСТВЕ" && sections[3].0 == "ЧЕРЕЗ ИНТЕРНЕТ")
            let rows = sections.flatMap { $0.1 }
            precondition(rows.filter { $0.title == "Автоматическая расшифровка" }.count == 1)
            let settings = rows.filter { $0.title.hasPrefix("Настройки ") }
            if provider == .telegram { precondition(settings.isEmpty) }
            else { precondition(settings.count == 1 && settings[0].title == "Настройки " + provider.title) }
        }
        self.page = .apple; self.appleSupported = [Locale(identifier:"ru_RU"),Locale(identifier:"en_US")]; self.appleInstalled = ["ru_RU"]
        precondition(self.makeSections()[1].1.count == 2)
        self.page = .appleLanguages; precondition(self.makeSections()[0].1.count == 2)
        self.page = .whisper; precondition(self.makeSections()[1].1.count == NagramiXWhisperModel.allCases.count)
        self.page = .whisperLanguages; precondition(self.makeSections()[0].1.first?.title == "Автоопределение")
        self.page = .credential(.grok); precondition(self.makeSections()[0].1.map(\.title) == ["API-ключ", "Модель", "Разрешить передачу аудио"])
        print("PASS: real settings row generation / provider, language, model and consent pages")
    }
}
@main struct Tests { static func main() { SettingsLayoutHarness().run() } }
