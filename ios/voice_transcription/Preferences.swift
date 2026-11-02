import Foundation
import UIKit
import Display
import AsyncDisplayKit
import AccountContext
import TelegramPresentationData
import ItemListUI

public final class NagramiXTranscriptionSettingsController: ViewController, UITableViewDataSource, UITableViewDelegate {
    private enum Page { case settings, language, models, keys, credential(NagramiXTranscriptionProvider), license }
    private let context: AccountContext
    private let presentationData: PresentationData
    private let table = UITableView(frame: .zero, style: .insetGrouped)
    private var page: Page = .settings
    private var observers: [NSObjectProtocol] = []
    private let keyField = UITextField()
    private let modelField = UITextField()
    private static let languages = [("ru-RU", "Русский"), ("en-US", "Английский"), ("uk-UA", "Украинский"), ("de-DE", "Немецкий"), ("fr-FR", "Французский"), ("es-ES", "Испанский"), ("it-IT", "Итальянский"), ("pt-BR", "Португальский"), ("tr-TR", "Турецкий"), ("zh-CN", "Китайский"), ("ja-JP", "Японский"), ("ko-KR", "Корейский"), ("ar-SA", "Арабский"), ("auto", "Автоопределение")]
    public init(context: AccountContext) {
        self.context = context; self.presentationData = context.sharedContext.currentPresentationData.with { $0 }
        super.init(navigationBarPresentationData: NavigationBarPresentationData(presentationData: self.presentationData))
        self.title = "Расшифровка"
        self.statusBar.statusBarStyle = self.presentationData.theme.rootController.statusBarStyle.style
        self.table.dataSource = self; self.table.delegate = self
        self.table.rowHeight = UITableView.automaticDimension; self.table.estimatedRowHeight = 58
        self.table.sectionHeaderHeight = UITableView.automaticDimension; self.table.estimatedSectionHeaderHeight = 36
        self.table.contentInsetAdjustmentBehavior = .never
        self.table.backgroundColor = self.presentationData.theme.list.blocksBackgroundColor
        self.table.separatorColor = self.presentationData.theme.list.itemBlocksSeparatorColor
        self.table.overrideUserInterfaceStyle = self.presentationData.theme.overallDarkAppearance ? .dark : .light
        for name in [NagramiXTranscriptionSettings.changed, NagramiXWhisperModels.changed] {
            self.observers.append(NotificationCenter.default.addObserver(forName: name, object: nil, queue: .main) { [weak self] _ in self?.refresh() })
        }
    }
    public required init(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    deinit { for observer in self.observers { NotificationCenter.default.removeObserver(observer) } }
    public override func loadDisplayNode() {
        self.displayNode = ASDisplayNode(); self.displayNode.backgroundColor = self.presentationData.theme.list.blocksBackgroundColor
        self.displayNode.view.addSubview(self.table); self.displayNodeDidLoad()
    }
    public override func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
        self.table.frame = CGRect(origin: .zero, size: layout.size)
        self.table.contentInset.top = self.navigationLayout(layout: layout).navigationFrame.maxY
        self.table.contentInset.bottom = max(layout.intrinsicInsets.bottom, layout.inputHeight ?? 0)
        self.table.scrollIndicatorInsets = self.table.contentInset
    }
    private func show(_ page: Page, _ title: String) {
        let controller = NagramiXTranscriptionSettingsController(context: self.context); controller.page = page; controller.title = title
        if case let .credential(provider) = page { controller.configureFields(provider) }
        self.push(controller)
    }
    public func numberOfSections(in tableView: UITableView) -> Int {
        switch self.page { case .settings: return 4; case .models: return 3; case .credential: return 2; default: return 1 }
    }
    public func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        switch self.page {
        case .settings: return [3, 2, 4, 2][section]
        case .models: return [2, 2, 2][section]
        case .keys: return 3
        case .language: return Self.languages.count
        case .credential: return section == 0 ? 5 : 1
        case .license: return 1
        }
    }
    public func tableView(_ tableView: UITableView, titleForHeaderInSection section: Int) -> String? {
        switch self.page {
        case .settings: return ["РАСШИФРОВКА", "НА УСТРОЙСТВЕ", "ЧЕРЕЗ ИНТЕРНЕТ", "ДОПОЛНИТЕЛЬНО"][section]
        case .models: return ["МОДЕЛЬ WHISPER", "ХРАНИЛИЩЕ", "APPLE"][section]
        case .credential: return section == 0 ? "ДОСТУП И МОДЕЛЬ" : "ПЕРЕДАЧА АУДИО"
        default: return nil
        }
    }
    public func tableView(_ tableView: UITableView, viewForHeaderInSection section: Int) -> UIView? {
        guard let text = self.tableView(tableView, titleForHeaderInSection: section) else { return nil }
        let view = UITableViewHeaderFooterView(reuseIdentifier: nil); var config = UIListContentConfiguration.groupedHeader()
        config.text = text; config.textProperties.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)
        config.textProperties.color = self.presentationData.theme.list.sectionHeaderTextColor; config.textProperties.numberOfLines = 0
        view.contentConfiguration = config; return view
    }
    public func tableView(_ tableView: UITableView, titleForFooterInSection section: Int) -> String? {
        switch self.page {
        case .settings:
            if section == 0 { return "Голосовые сообщения и кружки. Вручную — кнопкой →A или через «Расшифровать» в меню сообщения. Автоматически — только загруженные входящие записи в открытом чате. Исходная запись сохраняется." }
            if section == 1 { return "Бесплатно, без API-ключа и передачи аудио в облако. Apple доступен только для поддерживаемых iOS языков. Для Whisper сначала загрузите модель." }
            if section == 2 { return "Groq и Gemini используют ваш ключ и доступную ему бесплатную квоту или тариф. ChatGPT использует OpenAI Audio API и тариф вашего ключа. Telegram сохраняет штатные ограничения аккаунта; автоматический режим для него не запускается." }
        case .models:
            if section == 0 { return "Многоязычные модели Whisper, включая русский. Загрузка отдельно от приложения; размер и SHA-256 проверяются перед установкой. Более крупная модель требует больше памяти и времени." }
            if section == 1 { return "Активную модель нельзя удалить до окончания распознавания. Загрузка идёт, пока приложение открыто; закрытие может потребовать повторного запуска загрузки." }
            if section == 2 { return "На iOS 26 и новее выбранный язык Apple можно загрузить отдельно. На старых версиях моделями и доступными языками управляет iOS. Аудио распознаётся только на устройстве; при недоступности нет скрытого перехода на сервер Apple." }
        case let .credential(provider):
            if section == 0 { return provider == .chatgpt ? "Для расшифровки используется специализированная аудиомодель OpenAI, а не текстовый чат. Подписка ChatGPT не включает оплату API. Ключ сохраняется в Keychain этого iPhone." : "Бесплатный план требует собственного ключа; действуют лимиты вашего аккаунта. При исчерпании квоты платный резервный сервис не подключается. Ключ сохраняется в Keychain этого iPhone." }
            return "Включите только если согласны отправлять звуковую дорожку сообщения выбранному сервису. Изображение, переписка и другие сообщения не передаются. Результат дословный, без перевода и пересказа."
        case .language: return "Язык речи, а не язык перевода. Для Apple выберите конкретный поддерживаемый язык. Автоопределение доступно в Whisper и облачных сервисах."
        default: break
        }
        return nil
    }
    public func tableView(_ tableView: UITableView, willDisplayFooterView view: UIView, forSection section: Int) {
        guard let view = view as? UITableViewHeaderFooterView else { return }
        view.textLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)
        view.textLabel?.textColor = self.presentationData.theme.list.freeTextColor; view.textLabel?.numberOfLines = 0
    }
    public func tableView(_ tableView: UITableView, cellForRowAt path: IndexPath) -> UITableViewCell {
        let cell = UITableViewCell(style: .subtitle, reuseIdentifier: nil)
        cell.backgroundColor = self.presentationData.theme.list.itemBlocksBackgroundColor
        cell.textLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
        cell.textLabel?.textColor = self.presentationData.theme.list.itemPrimaryTextColor; cell.textLabel?.numberOfLines = 0
        cell.detailTextLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)
        cell.detailTextLabel?.textColor = self.presentationData.theme.list.itemSecondaryTextColor; cell.detailTextLabel?.numberOfLines = 0
        cell.tintColor = self.presentationData.theme.list.itemAccentColor
        let value = NagramiXTranscriptionSettings.current
        switch self.page {
        case .settings:
            if path.section == 0 {
                cell.textLabel?.text = ["Расшифровка сообщений", "Автоматическая расшифровка", "Язык речи"][path.row]
                if path.row < 2 { self.toggle(cell, tag: path.row, on: path.row == 0 ? value.enabled : value.automatic) }
                else { cell.detailTextLabel?.text = Self.languages.first { $0.0 == value.language }?.1 ?? value.language; cell.accessoryType = .disclosureIndicator }
            } else if path.section == 1 || path.section == 2 {
                let provider = NagramiXTranscriptionProvider.allCases[(path.section == 1 ? 0 : 2) + path.row]
                cell.textLabel?.text = provider.title; cell.accessoryType = value.provider == provider ? .checkmark : .none
                if provider == .apple { cell.detailTextLabel?.text = NagramiXTranscriptionApple.available(value.language) ? "На устройстве · Поддержку языка проверяет iOS" : "Нет поддержки выбранного языка в iOS" }
                else if provider == .whisper { cell.detailTextLabel?.text = "На устройстве · " + value.whisper.title }
                else if provider == .telegram { cell.detailTextLabel?.text = "Штатная квота аккаунта" }
                else { cell.detailTextLabel?.text = NagramiXTranscriptionKeys.read(provider)?.isEmpty == false ? "Свой ключ · Квота сервиса" : "Нужен свой ключ" }
            } else { cell.textLabel?.text = ["Языки и модели", "API-ключи и модели"][path.row]; cell.accessoryType = .disclosureIndicator }
        case .language:
            let language = Self.languages[path.row]; cell.textLabel?.text = language.1
            cell.accessoryType = value.language == language.0 ? .checkmark : .none
        case .models:
            if path.section == 0 {
                let model = NagramiXWhisperModel.allCases[path.row]; cell.textLabel?.text = model.title + " · " + model.rawValue
                cell.detailTextLabel?.text = NagramiXWhisperModels.shared.status(model); cell.accessoryType = value.whisper == model ? .checkmark : .none
            } else if path.section == 1 {
                cell.textLabel?.text = path.row == 0 ? "Whisper: только по Wi-Fi" : "Удалить выбранную модель"
                if path.row == 0 { self.toggle(cell, tag: 2, on: value.wifiOnly) }
            } else { cell.textLabel?.text = path.row == 0 ? "Загрузить язык Apple" : "Лицензии Whisper"; cell.accessoryType = .disclosureIndicator }
        case .keys:
            let provider = NagramiXTranscriptionProvider.allCases.filter { $0.cloud }[path.row]
            cell.textLabel?.text = provider.title; cell.detailTextLabel?.text = NagramiXTranscriptionKeys.read(provider)?.isEmpty == false ? "Ключ сохранён" : "Ключ не задан"; cell.accessoryType = .disclosureIndicator
        case let .credential(provider):
            if path.section == 1 { cell.textLabel?.text = "Разрешить передачу аудио"; self.toggle(cell, tag: 3, on: value.cloudAllowed[provider.rawValue] == true) }
            else if path.row < 2 {
                let field = path.row == 0 ? self.keyField : self.modelField
                field.removeFromSuperview(); field.translatesAutoresizingMaskIntoConstraints = false; cell.contentView.addSubview(field)
                NSLayoutConstraint.activate([field.leadingAnchor.constraint(equalTo: cell.contentView.layoutMarginsGuide.leadingAnchor), field.trailingAnchor.constraint(equalTo: cell.contentView.layoutMarginsGuide.trailingAnchor), field.topAnchor.constraint(equalTo: cell.contentView.topAnchor, constant: 15), field.bottomAnchor.constraint(equalTo: cell.contentView.bottomAnchor, constant: -15)])
            } else { cell.textLabel?.text = ["Сохранить", "Использовать ключ из настроек перевода", "Удалить ключ"][path.row - 2] }
        case .license: cell.textLabel?.text = NagramiXWhisperLicense.text
        }
        return cell
    }
    private func configureFields(_ provider: NagramiXTranscriptionProvider) {
        for field in [self.keyField, self.modelField] {
            field.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize); field.textColor = self.presentationData.theme.list.itemPrimaryTextColor
            field.autocorrectionType = .no; field.autocapitalizationType = .none; field.spellCheckingType = .no
        }
        self.keyField.placeholder = "API-ключ"; self.keyField.isSecureTextEntry = true; self.keyField.text = NagramiXTranscriptionKeys.read(provider)
        self.modelField.placeholder = "Модель"; self.modelField.text = NagramiXTranscriptionSettings.current.models[provider.rawValue] ?? provider.defaultModel
    }
    private func toggle(_ cell: UITableViewCell, tag: Int, on: Bool) {
        let toggle = UISwitch(); toggle.tag = tag; toggle.isOn = on; toggle.onTintColor = self.presentationData.theme.list.itemAccentColor
        toggle.accessibilityLabel = cell.textLabel?.text; toggle.addTarget(self, action: #selector(self.toggleChanged(_:)), for: .valueChanged)
        cell.accessoryView = toggle; cell.selectionStyle = .none
    }
    @objc private func toggleChanged(_ sender: UISwitch) {
        NagramiXTranscriptionSettings.update { value in
            switch sender.tag {
            case 0: value.enabled = sender.isOn
            case 1: value.automatic = sender.isOn
            case 2: value.wifiOnly = sender.isOn
            default: if case let .credential(provider) = self.page { value.cloudAllowed[provider.rawValue] = sender.isOn }
            }
        }
    }
    public func tableView(_ tableView: UITableView, didSelectRowAt path: IndexPath) {
        tableView.deselectRow(at: path, animated: true)
        switch self.page {
        case .settings:
            if path.section == 0 && path.row == 2 { self.show(.language, "Язык речи") }
            else if path.section == 1 || path.section == 2 {
                let provider = NagramiXTranscriptionProvider.allCases[(path.section == 1 ? 0 : 2) + path.row]
                NagramiXTranscriptionSettings.update { $0.provider = provider; if provider == .apple && $0.language == "auto" { $0.language = "ru-RU" } }
            } else if path.section == 3 { self.show(path.row == 0 ? .models : .keys, path.row == 0 ? "Языки и модели" : "API-ключи и модели") }
        case .language:
            let code = Self.languages[path.row].0
            if code == "auto" && NagramiXTranscriptionSettings.current.provider == .apple { self.alert("Для Apple выберите конкретный язык."); return }
            NagramiXTranscriptionSettings.update { $0.language = code }
        case .models:
            if path.section == 0 {
                let model = NagramiXWhisperModel.allCases[path.row]; NagramiXTranscriptionSettings.update { $0.whisper = model }
                if !NagramiXWhisperModels.shared.installed(model) { NagramiXWhisperModels.shared.downloadOrCancel(model) }
            } else if path.section == 1 && path.row == 1 {
                if !NagramiXWhisperModels.shared.remove(NagramiXTranscriptionSettings.current.whisper) { self.alert("Модель сейчас используется или загружается. Сначала дождитесь завершения или отмените загрузку.") }
                self.refresh()
            } else if path.section == 2 && path.row == 0 {
                #if compiler(>=6.2)
                if #available(iOS 26.0, *) {
                    self.alert("Запрошена загрузка языка Apple. iOS управляет установкой и повторными попытками при проблемах с сетью.")
                    NagramiXTranscriptionAnalyzer.install(language: NagramiXTranscriptionSettings.current.language) { [weak self] result in
                        DispatchQueue.main.async {
                            switch result { case let .success(text): self?.alert(text); case let .failure(error): self?.alert(error.text) }
                        }
                    }
                } else { self.alert("На этой версии iOS моделями Apple управляет система. Для отдельной загрузки выберите Whisper.") }
                #else
                self.alert("На этой версии iOS моделями Apple управляет система. Для отдельной загрузки выберите Whisper.")
                #endif
            } else if path.section == 2 { self.show(.license, "Лицензии Whisper") }
        case .keys: self.show(.credential(NagramiXTranscriptionProvider.allCases.filter { $0.cloud }[path.row]), NagramiXTranscriptionProvider.allCases.filter { $0.cloud }[path.row].title)
        case let .credential(provider):
            guard path.section == 0 && path.row >= 2 else { return }
            if path.row == 2 {
                let model = (self.modelField.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
                guard model.range(of: "\\A[A-Za-z0-9._:-]{1,128}\\z", options: .regularExpression) != nil else { self.alert("Укажите идентификатор поддерживаемой аудиомодели."); return }
                guard NagramiXTranscriptionKeys.save(self.keyField.text?.trimmingCharacters(in: .whitespacesAndNewlines), provider: provider) else { self.alert("Не удалось сохранить ключ."); return }
                NagramiXTranscriptionSettings.update { $0.models[provider.rawValue] = model }; self.view.endEditing(true); self.alert("Настройки сохранены.")
            } else if path.row == 3 {
                guard let key = NagramiXTranscriptionKeys.importTranslationKey(provider) else { self.alert("Для этого сервиса нет сохранённого ключа перевода."); return }
                self.keyField.text = key; self.alert("Ключ подставлен в поле. Нажмите «Сохранить», чтобы использовать его для расшифровки.")
            } else if NagramiXTranscriptionKeys.save(nil, provider: provider) { self.keyField.text = ""; NagramiXTranscriptionSettings.update { $0.cloudAllowed[provider.rawValue] = false } }
        case .license: break
        }
    }
    private func refresh() {
        // Preserve editing fields and keyboard; only reconfigure static cells.
        for path in self.table.indexPathsForVisibleRows ?? [] {
            if case .credential = self.page, path.section == 0 && path.row < 2 { continue }
            self.table.reloadRows(at: [path], with: .none)
        }
    }
    private func alert(_ text: String) {
        let alert = UIAlertController(title: "Расшифровка", message: text, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default))
        var host = self.view.window?.rootViewController
        while let presented = host?.presentedViewController { host = presented }
        host?.present(alert, animated: true)
    }
}
