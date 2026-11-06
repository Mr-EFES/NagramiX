import Foundation

private var checks = 0
private func check(_ value: @autoclosure () -> Bool, _ label: String) {
    checks += 1
    if !value() { fatalError("Local model size regression: " + label) }
}
@main struct LocalModelSizeTests {
    static func expectedSize(_ number: String, _ menu: MenuHarness, unit: String = "MB") -> String {
        let amount = number.replacingOccurrences(of: ".", with: menu.presentationData.dateTimeFormat.decimalSeparator)
        return menu.presentationData.strings.values["FileSize." + unit]!.replacingOccurrences(of: "%@", with: amount)
    }
    static func main() throws {
        let data = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
        let languages = try JSONDecoder().decode([FixtureLanguage].self, from: data)
        check(languages.count == 71, "all application locales represented")
        let whisper = NagramiXWhisperModels.shared, vosk = NagramiXVoskModels.shared
        let table = UITableView()
        let offered: [NagramiXWhisperModel] = [.base, .small_full, .large_v3_turbo_q8_0]
        check(NagramiXLocalInferenceMemory.whisperModels == offered, "approved weight IDs and order unchanged")
        let russian = NagramiXLocalInferenceMemory.voskModels(language: "ru")
        check(russian.map { $0.name } == ["vosk-model-small-ru-0.22", "vosk-model-ru-0.10-lgraph"], "same two Russian weights, no new model/download")
        func rows(_ menu: MenuHarness) -> [MenuHarness.Row] { menu.sections()[1].1 }
        func assertSingleLine(_ cells: [UITableViewCell]) {
            for cell in cells {
                check(cell.textLabel?.numberOfLines == 1 && cell.detailTextLabel?.numberOfLines == 1, "one-line native model cell")
                check(cell.textLabel?.adjustsFontSizeToFitWidth == false && cell.detailTextLabel?.adjustsFontSizeToFitWidth == false, "native font sizes are preserved")
            }
        }
        for locale in languages {
            let menu = MenuHarness(); menu.presentationData.strings = Strings(baseLanguageCode: locale.code, values: locale.values)
            let numberFormatter = NumberFormatter(); numberFormatter.locale = Locale(identifier: locale.code)
            menu.presentationData.dateTimeFormat.decimalSeparator = numberFormatter.decimalSeparator ?? "."
            // Cold first opening: every not-installed model exposes its size.
            whisper.present = []; whisper.progress = [:]; vosk.present = []; vosk.progress = [:]
            NagramiXTranscriptionSettings.current = .init(whisper: .base, voskModelID: russian[0].name)
            menu.page = .whisper
            check(rows(menu).map { $0.subtitle } == ["56.9", "465", "833.6"].map { expectedSize($0, menu) }, "fresh Whisper shows each catalog size in selected units")
            check(rows(menu).allSatisfy { menu.cell($0).accessoryType == .none }, "no installed checkmark on first opening")
            whisper.present = [.base]; whisper.progress = [.small_full: 53]
            let mixed = rows(menu)
            check(mixed[0].subtitle == nil && mixed[1].subtitle == menu.localModelDownloadProgress(installed: false, progress: 53) && mixed[2].subtitle == expectedSize("833.6", menu), "screenshot state: installed,53 percent,maximum size")
            check(mixed.map { menu.cell($0).accessoryType } == [.checkmark, .none, .none], "mixed state retains exact installed selection")
            whisper.progress = [:]
            check(rows(menu)[1].subtitle == expectedSize("465", menu), "cancel restores middle model size")
            whisper.present = []
            check(rows(menu)[0].subtitle == expectedSize("56.9", menu) && menu.cell(rows(menu)[0]).accessoryType == .none, "removing selected model restores size and removes checkmark")
            menu.page = .vosk
            check(rows(menu).map { $0.subtitle } == ["44", "167.6"].map { expectedSize($0, menu) }, "fresh Vosk shows both archive download sizes")
            vosk.present = [russian[0].name]; vosk.progress = [russian[1].name: 30]
            check(rows(menu)[0].subtitle == nil && rows(menu)[1].subtitle == menu.localModelDownloadProgress(installed: false, progress: 30), "Vosk installed and loading states")
            vosk.progress = [:]
            check(rows(menu)[1].subtitle == expectedSize("167.6", menu), "Vosk cancellation restores size")

            whisper.present = Set(offered); whisper.progress = [:]
            vosk.present = Set(russian.map { $0.name }); vosk.progress = [:]
            NagramiXTranscriptionSettings.current = .init(whisper: .small_full, voskModelID: russian[0].name)
            menu.page = .whisper
            let choices = rows(menu), cells = choices.map { menu.cell($0) }
            check(choices.map { $0.title } == Array(locale.expected.prefix(3)), "only localized Basic/Medium/Maximum names")
            check(choices.allSatisfy { $0.subtitle == nil }, "no loaded, size or technical subtitle")
            check(cells.map { $0.accessoryType } == [.none, .checkmark, .none], "checkmark follows selected installed Whisper model")
            assertSingleLine(cells)
            for section in 0..<3 { check(menu.tableView(table, titleForFooterInSection: section) == nil, "no Whisper model footer") }

            // Selection belongs to the configuration, never to progress order.
            for model in offered {
                NagramiXTranscriptionSettings.current.whisper = model
                let cells = rows(menu).map { menu.cell($0) }
                check(cells.filter { $0.accessoryType == .checkmark }.count == 1, "one selected Whisper checkmark")
                check(cells[offered.firstIndex(of: model)!].accessoryType == .checkmark, "checkmark beside exact selected ID")
            }
            NagramiXTranscriptionSettings.current.whisper = .small_full
            whisper.present.remove(.large_v3_turbo_q8_0); whisper.progress[.large_v3_turbo_q8_0] = 35
            let loading = rows(menu), loadingCells = loading.map { menu.cell($0) }
            check(loading[2].subtitle?.isEmpty == false, "download exposes a localized percentage")
            check(loading[0].subtitle == nil && loading[1].subtitle == nil, "other installed rows stay clear during download")
            check(loadingCells.map { $0.accessoryType } == [.none, .checkmark, .none], "downloading another model does not move the checkmark")
            assertSingleLine(loadingCells)
            whisper.present.insert(.large_v3_turbo_q8_0); whisper.progress[.large_v3_turbo_q8_0] = 100
            check(rows(menu)[2].subtitle == nil, "installed model suppresses stale 100 percent")
            NagramiXTranscriptionSettings.current.whisper = .large_v3_turbo_q8_0
            check(rows(menu).map { menu.cell($0).accessoryType } == [.none, .none, .checkmark], "completion/explicit selection checks the newly chosen installed model")
            whisper.present.remove(.large_v3_turbo_q8_0); whisper.progress = [:]
            check(rows(menu)[2].subtitle == expectedSize("833.6", menu) && menu.cell(rows(menu)[2]).accessoryType == .none, "cancelled/deleted model restores its own download size")

            menu.page = .vosk
            NagramiXTranscriptionSettings.current.voskModelID = russian[0].name
            let voskRows = rows(menu), voskCells = voskRows.map { menu.cell($0) }
            check(voskRows.map { $0.title } == [locale.expected[0], locale.expected[3]], "localized Vosk Basic/Alternative only")
            check(voskRows.allSatisfy { $0.subtitle == nil }, "installed Vosk rows have no status caption")
            check(voskCells.map { $0.accessoryType } == [.checkmark, .none], "selected Vosk ID checked")
            assertSingleLine(voskCells)
            for section in 0..<3 { check(menu.tableView(table, titleForFooterInSection: section) == nil, "no Vosk technical footer") }
            vosk.present.remove(russian[1].name); vosk.progress[russian[1].name] = 30
            check(rows(menu)[1].subtitle?.isEmpty == false, "alternative Vosk download percentage")
            check(rows(menu).map { menu.cell($0).accessoryType } == [.checkmark, .none], "Vosk progress does not select another row")
            vosk.present.insert(russian[1].name); vosk.progress[russian[1].name] = 100
            NagramiXTranscriptionSettings.current.voskModelID = russian[1].name
            check(rows(menu)[1].subtitle == nil, "installed Vosk suppresses stale percentage")
            check(rows(menu).map { menu.cell($0).accessoryType } == [.none, .checkmark], "selected alternative checked alone")
        }
        let menu = MenuHarness()
        menu.presentationData.strings.baseLanguageCode = "en"
        for (input, expected) in [(-12, "0%"), (0, "0%"), (33, "33%"), (99, "99%"), (100, "100%"), (150, "100%")] {
            check(menu.localModelDownloadProgress(installed: false, progress: input) == expected, "progress value only, clamped to native percent range")
            check(menu.localModelDownloadProgress(installed: true, progress: input) == nil, "any installed row hides percentage")
        }
        check(menu.localModelDownloadProgress(installed: false, progress: nil) == nil, "idle uninstalled row does not invent a download")
        check(menu.localModelDownloadProgress(installed: true, progress: nil) == nil, "idle installed row remains clear")
        let names = ["Базовая", "Средняя", "Максимальная"]
        for model in NagramiXWhisperModel.allCases { check(names.contains(menu.whisperModelTitle(model)), "legacy weights never expose technical names") }
        for language in NagramiXLocalInferenceMemory.voskLanguages {
            let models = NagramiXLocalInferenceMemory.voskModels(language: language)
            check(models.count <= 2, "Vosk offering limit unchanged")
            check(models.enumerated().map { menu.voskModelTitle(at: $0.offset) }.count == models.count, "friendly labels cover all offered speech languages")
        }
        let sized = MenuHarness()
        let english = languages.first { $0.code == "en" }!
        sized.presentationData.strings = Strings(baseLanguageCode: "en", values: english.values)
        for separator in [".", ","] {
            sized.presentationData.dateTimeFormat.decimalSeparator = separator
            check(sized.localModelDownloadStatus(installed: false, progress: nil, size: 59_707_625) == expectedSize("56.9", sized), "native presentation decimal separator")
        }
        for (bytes, number, unit) in [(Int64(0), "0", "B"), (Int64(-9), "0", "B"), (Int64(1024), "1", "KB"), (Int64(1_048_576), "1", "MB"), (Int64(5_000_000_000), "4.6", "GB")] {
            check(sized.localModelDownloadStatus(installed: false, progress: nil, size: bytes) == expectedSize(number, sized, unit: unit), "native unit threshold and Int64 size")
        }
        for progress in [nil, -1, 0, 53, 100, 101] as [Int?] {
            check(sized.localModelDownloadStatus(installed: true, progress: progress, size: 59_707_625) == nil, "installed state hides size and stale progress")
        }
        print("PASS: \(checks) local model size/state/localization checks; UIKit/download IO and native remote packs are boundaries")
    }
}
