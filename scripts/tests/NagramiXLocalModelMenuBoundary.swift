import Foundation

// Production titles, row builders, footers, native cell configuration and
// checkmark decisions are inserted below. UIKit and installed/download state
// are explicit boundaries; real catalogs/IDs/translations are used.
final class UITableView {}
final class UILabel {
    enum LineBreakMode { case byWordWrapping, byTruncatingTail }
    var text: String?; var numberOfLines = 0; var adjustsFontSizeToFitWidth = true
    var lineBreakMode = LineBreakMode.byWordWrapping
}
final class UITableViewCell {
    enum AccessoryType: Equatable { case none, checkmark }
    var textLabel: UILabel? = UILabel(); var detailTextLabel: UILabel? = UILabel()
    var accessoryType = AccessoryType.none
}
struct NagramiXTranscriptionConfiguration {
    var whisper = NagramiXWhisperModel.base
    var voskModelID: String?
    var whisperLanguage: String? = "auto"
    var language = "ru"
}
enum NagramiXTranscriptionSettings { static var current = NagramiXTranscriptionConfiguration() }
final class NagramiXWhisperModels {
    static let shared = NagramiXWhisperModels()
    var present: Set<NagramiXWhisperModel> = []; var progress: [NagramiXWhisperModel: Int] = [:]
    func installed(_ model: NagramiXWhisperModel) -> Bool { present.contains(model) }
    func downloadProgress(_ model: NagramiXWhisperModel) -> Int? { progress[model] }
    func status(_ model: NagramiXWhisperModel) -> String { progress[model].map { "Загрузка · \($0)%" } ?? (installed(model) ? "Загружена" : "\(model.size / 1_000_000) МБ") }
}
final class NagramiXVoskModels {
    static let shared = NagramiXVoskModels()
    var present: Set<String> = []; var progress: [String: Int] = [:]
    func installed(_ model: NagramiXVoskModel) -> Bool { present.contains(model.name) }
    func downloadProgress(_ model: NagramiXVoskModel) -> Int? { progress[model.name] }
    func status(_ model: NagramiXVoskModel) -> String { progress[model.name].map { "Загрузка · \($0)%" } ?? (installed(model) ? "Загружена" : "\(model.size / 1_000_000) МБ") }
}
enum NagramiXLocalInferenceMemory {
    // PRODUCTION_MODEL_OFFERINGS
}
enum NagramiXTranscriptionVosk {
    // PRODUCTION_VOSK_RESOLVER
}
struct FixtureLanguage: Decodable { let code: String; let values: [String: String]; let expected: [String] }
struct Strings {
    var baseLanguageCode = "ru"
    var values: [String: String] = [:]
    func nagramiXUILocalized(_ value: String) -> String { values[value] ?? value }
    func nagramiXLocalized(_ key: String) -> String { values[key] ?? key }
}
struct PresentationData { var strings = Strings() }
final class MenuHarness {
    // PRODUCTION_PAGE_ROW_ACTION
    var page = Page.whisper
    var presentationData = PresentationData()
    // PRODUCTION_PRESENTATION_HELPERS
    // PRODUCTION_LANGUAGE_LABEL
    func sections() -> [(String?, [Row])] {
        let value = NagramiXTranscriptionSettings.current
        switch page {
        // PRODUCTION_LOCAL_SECTIONS
        default: return []
        }
    }
    // PRODUCTION_FOOTER
    func cell(_ row: Row) -> UITableViewCell {
        let cell = UITableViewCell()
        cell.textLabel?.text = self.presentationData.strings.nagramiXUILocalized(row.title)
        cell.detailTextLabel?.text = row.subtitle.map { self.presentationData.strings.nagramiXUILocalized($0) }
        let value = NagramiXTranscriptionSettings.current
        switch row.action {
        // PRODUCTION_ACCESSORIES
        default: break
        }
        return cell
    }
}
