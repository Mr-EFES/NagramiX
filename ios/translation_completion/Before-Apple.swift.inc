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
                do { try await session.prepareTranslation(); self.finished = true }
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
