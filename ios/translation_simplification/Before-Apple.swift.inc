import UIKit
import SwiftUI
import Translation

@available(iOS 18.0, *)
private struct NagramiXTranslationDownloadView: View {
    let source: String
    let target: String
    @Environment(\.dismiss) private var dismiss
    @State private var finished = false
    @State private var error: String?

    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                if !self.finished && self.error == nil { ProgressView() }
                Text(self.finished ? "Языки готовы" : (self.error ?? "Подготовка языков Apple…"))
                    .multilineTextAlignment(.center)
                Text("После загрузки моделей перевод этой пары языков доступен на устройстве.")
                    .font(.footnote).foregroundStyle(.secondary).multilineTextAlignment(.center)
                Button(self.finished || self.error != nil ? "Готово" : "Отмена") { self.dismiss() }
            }
            .padding(24)
            .navigationTitle("Языки Apple")
            .navigationBarTitleDisplayMode(.inline)
            .translationTask(source: Locale.Language(identifier: self.source), target: Locale.Language(identifier: self.target)) { session in
                do {
                    try await session.prepareTranslation()
                    let availability = LanguageAvailability()
                    let status = await availability.status(from: Locale.Language(identifier: self.source), to: Locale.Language(identifier: self.target))
                    if status == .installed { self.finished = true }
                    else { self.error = "Загрузка языков ещё не завершена. Проверьте состояние в списке языков." }
                }
                catch { self.error = "Не удалось подготовить языки. Проверьте поддержку этой пары и подключение к интернету." }
            }
        }
    }
}

public func nagramiXPrepareTranslationLanguages(presenter: UIViewController, source: String, target: String) {
    if #available(iOS 18.0, *) {
        let controller = UIHostingController(rootView: NagramiXTranslationDownloadView(source: source, target: target))
        controller.modalPresentationStyle = .pageSheet
        presenter.present(controller, animated: true)
    } else {
        let controller = UIAlertController(title: "Apple", message: NagramiXTranslationFailure.unavailable.text, preferredStyle: .alert)
        controller.addAction(UIAlertAction(title: "OK", style: .default))
        presenter.present(controller, animated: true)
    }
}

@available(iOS 18.0, *)
private struct NagramiXAppleLanguageRow: Identifiable {
    let id: String
    let name: String
    let status: LanguageAvailability.Status
}

@available(iOS 18.0, *)
private struct NagramiXAppleLanguageSelection: Identifiable {
    let id: String
}

@available(iOS 18.0, *)
private struct NagramiXAppleLanguagesView: View {
    let target: String
    let interface: String
    let choosingSource: Bool
    let selected: (String?) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var rows: [NagramiXAppleLanguageRow] = []
    @State private var loading = true
    @State private var download: NagramiXAppleLanguageSelection?

    var body: some View {
        NavigationView {
            List {
                if self.choosingSource {
                    Button("Автоопределение") { self.selected(nil); self.dismiss() }
                } else {
                    Text("Выберите исходный язык для загрузки пары. iOS запросит разрешение на скачивание.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                if self.loading { ProgressView() }
                ForEach(self.rows) { row in
                    Button {
                        if self.choosingSource { self.selected(row.id); self.dismiss() }
                        else if NagramiXTranslationLanguage.base(row.id) != NagramiXTranslationLanguage.base(self.target) && row.status != .unsupported {
                            self.download = NagramiXAppleLanguageSelection(id: row.id)
                        }
                    } label: {
                        HStack {
                            Text(row.name)
                            Spacer()
                            Text(NagramiXTranslationLanguage.base(row.id) == NagramiXTranslationLanguage.base(self.target) ? "Язык перевода" : self.statusText(row.status)).font(.footnote).foregroundStyle(.secondary)
                        }
                    }.disabled(!self.choosingSource && (NagramiXTranslationLanguage.base(row.id) == NagramiXTranslationLanguage.base(self.target) || row.status == .unsupported))
                }
            }
            .navigationTitle(self.choosingSource ? "Исходящий язык" : "Языки Apple")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .navigationBarTrailing) { Button("Готово") { self.dismiss() } } }
            .task { await self.refresh() }
            .sheet(item: self.$download, onDismiss: { Task { await self.refresh() } }) { item in
                NagramiXTranslationDownloadView(source: item.id, target: self.target)
            }
        }
    }

    private func statusText(_ status: LanguageAvailability.Status) -> String {
        switch status {
        case .installed: return "Пара загружена"
        case .supported: return "Пара доступна для загрузки"
        case .unsupported: return "Пара не поддерживается"
        @unknown default: return "Недоступно"
        }
    }

    @MainActor private func refresh() async {
        self.loading = true
        let availability = LanguageAvailability()
        let languages = await availability.supportedLanguages
        var found: [NagramiXAppleLanguageRow] = []
        var seen = Set<String>()
        for language in languages {
            let code = language.minimalIdentifier
            guard seen.insert(code).inserted else { continue }
            let targetLanguage = NagramiXTranslationLanguage.base(code) == NagramiXTranslationLanguage.base(self.target) ? nil : Locale.Language(identifier: self.target)
            let status = await availability.status(from: language, to: targetLanguage)
            let name = NagramiXTranslationLanguage.title(code, interface: self.interface)
            found.append(NagramiXAppleLanguageRow(id: code, name: name, status: status))
        }
        self.rows = found.sorted { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending }
        self.loading = false
    }
}

public func nagramiXShowAppleLanguages(presenter: UIViewController, target: String, interface: String, choosingSource: Bool, selected: @escaping (String?) -> Void) {
    if #available(iOS 18.0, *) {
        let controller = UIHostingController(rootView: NagramiXAppleLanguagesView(target: target, interface: interface, choosingSource: choosingSource, selected: selected))
        controller.modalPresentationStyle = .pageSheet
        presenter.present(controller, animated: true)
    } else {
        let controller = UIAlertController(title: "Apple", message: NagramiXTranslationFailure.unavailable.text, preferredStyle: .alert)
        controller.addAction(UIAlertAction(title: "OK", style: .default))
        presenter.present(controller, animated: true)
    }
}
