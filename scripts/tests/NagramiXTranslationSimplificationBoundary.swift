import Foundation

// Only UIKit text fields, alerts and Keychain are replaced. Configuration,
// JSON migration, request codecs and the inserted Save method are production.
final class TranslationField { var text: String?; init(_ text: String?) { self.text = text } }
final class TranslationView { func endEditing(_ force: Bool) {} }
final class TranslationNotificationCounter: @unchecked Sendable {
    private let lock = NSLock()
    private var count = 0
    func increment() { self.lock.lock(); self.count += 1; self.lock.unlock() }
    var value: Int { self.lock.lock(); defer { self.lock.unlock() }; return self.count }
}
enum NagramiXTranslationKeys {
    static var values: [NagramiXTranslationProvider: NagramiXTranslationCredential] = [:]
    static var fail = false
    static func save(_ value: NagramiXTranslationCredential?, provider: NagramiXTranslationProvider, notify: Bool = true) -> Bool {
        guard !self.fail, provider.requiresAPIKey else { return false }
        self.values[provider] = value
        if notify { NagramiXTranslationSettings.credentialsChanged() }
        return true
    }
}
final class TranslationDraftHarness {
    enum Page { case settings, credential(NagramiXTranslationProvider) }
    var page: Page
    let view = TranslationView()
    let keyField: TranslationField
    var draftModel: String
    var draftTemperature: Double
    var errors: [String] = []
    var dismissed = false
    init(provider: NagramiXTranslationProvider, key: String, model: String, temperature: Double) {
        self.page = .credential(provider)
        self.keyField = TranslationField(key)
        self.draftModel = model
        self.draftTemperature = temperature
    }
    func alert(_ value: String) { self.errors.append(value) }
    func dismiss() { self.dismissed = true }
    // SAVE_METHOD
}
