// Foundation boundary for the actual Core localization code; UIKit and Telegram runtime are not mocked as passing.
import Foundation
public final class PresentationStrings {
    public struct Component { public let languageCode: String; public let dict: [String: String] }
    public let primaryComponent: Component
    public let secondaryComponent: Component?
    public init(_ code: String, secondary: String? = nil, dict: [String: String] = [:]) {
        self.primaryComponent = Component(languageCode: code, dict: dict)
        self.secondaryComponent = secondary.map { Component(languageCode: $0, dict: [:]) }
    }
}

@main struct Checks {
    static func main() {
        let en = PresentationStrings("en"), ru = PresentationStrings("ru"), de = PresentationStrings("de-DE")
        precondition(en.nagramiXSettingsOther == "Other")
        precondition(ru.nagramiXSettingsOther == "Прочее")
        precondition(de.nagramiXSettingsOther == "Weitere")
        precondition(en.nagramiXUILocalized("Качественные кружки") == "High-Quality Video Messages")
        precondition(ru.nagramiXUILocalized("Качественные кружки") == "Качественные кружки")
        precondition(de.nagramiXUILocalized("Качественные кружки") == "Hochwertige Videonachrichten")
        precondition(de.nagramiXUILocalized("Перевод сообщений") == "Nachrichtenübersetzung")
        precondition(en.nagramiXUILocalized("Температура: 20%") == "Temperature: 20%")
        precondition(en.nagramiXUILocalized("Загрузка · 45%") == "Downloading · 45%")
        precondition(en.nagramiXUILocalized("2000 кбит/с") == "2000 kbps")
        precondition(en.nagramiXUILocalized("30 FPS · 1.5 Мбит/с · H.264 (AVC)") == "30 FPS · 1.5 Mbps · H.264 (AVC)")
        precondition(NagramiXAppLocalization.format("%2$@ / %1$@ %%", arguments: ["A%2$@", "B"]) == "B / A%2$@ %")
        precondition(PresentationStrings("en").nagramiXUILocalized("No user text is transformed: Качественные кружки") == "No user text is transformed: Качественные кружки")
        precondition(PresentationStrings("zz").nagramiXSettingsOther == "Other")
        precondition(PresentationStrings("custom", secondary: "de").nagramiXSettingsOther == "Weitere")
        precondition(PresentationStrings("en", dict: ["NagramiX.Settings.Page.Other":"Pack override"]).nagramiXSettingsOther == "Pack override")
        precondition(NagramiXAppLocalization.languageCandidates("zh_TW").contains("zh-hant"))
        precondition(NagramiXAppLocalization.languageCandidates("pt_BR").contains("pt-br"))
        precondition(NagramiXAppLocalization.languageCandidates("de-DE").contains("de"))
        precondition(NagramiXAppLocalization.languageCandidates("iw").contains("he"))
        var checks = 20
        for code in testedLanguageCodes {
            precondition(NagramiXAppLocalization.localized("NagramiX.Test.LanguageCode", languageCode: code) == code)
            precondition(NagramiXAppLocalization.localized("NagramiX.Test.LanguageCode", languageCode: code.uppercased().replacingOccurrences(of: "-", with: "_")) == code)
            checks += 2
        }
        for (alias, expected) in [("no", "nb"), ("iw", "he"), ("tl", "fil"), ("in", "id"), ("zh_TW", "zh-hant")] {
            precondition(NagramiXAppLocalization.localized("NagramiX.Test.LanguageCode", languageCode: alias) == expected)
            checks += 1
        }
        precondition(NagramiXAppLocalization.format("صوت 🎙️ %2$@ / %1$@", arguments: ["100%", "A%2$@"]) == "صوت 🎙️ A%2$@ / 100%")
        precondition(NagramiXAppLocalization.format("%1$@ · עברית", arguments: ["🎙️"]) == "🎙️ · עברית")
        checks += 2
        for (code, values) in productionCatalogs {
            for (key, expected) in values {
                precondition(NagramiXAppLocalization.localized(key, languageCode: code) == expected, "\(code): \(key)")
                checks += 1
            }
        }
        print("\(checks) localization runtime checks passed; \(productionCatalogs.count) real catalogs plus explicit routing fixtures; UIKit/SDK not exercised.")
    }
}
