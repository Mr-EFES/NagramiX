import Foundation
import UIKit
import Display
import AsyncDisplayKit
import AccountContext
import TelegramPresentationData
import ItemListUI

public final class NagramiXTranslationSettingsController: ViewController, UITableViewDataSource, UITableViewDelegate {
    private enum Page {
        case settings, keys, credential(NagramiXTranslationProvider), languages, ignored, local
    }
    private let context: AccountContext
    private let presentationData: PresentationData
    private let table = UITableView(frame: .zero, style: .insetGrouped)
    private var page: Page = .settings
    private var observer: NSObjectProtocol?
    private var languageSelected: ((String) -> Void)?
    private var pickerLanguage: String?
    private let keyField = UITextField()
    private let modelField = UITextField()
    private weak var temperatureSlider: UISlider?
    private weak var temperatureLabel: UILabel?
    private var localSource = "en"
    private var localTarget = "ru"
    private var interfaceLanguage: String { NagramiXTranslationLanguage.base(self.presentationData.strings.baseLanguageCode) }

    public init(context: AccountContext) {
        self.context = context
        self.presentationData = context.sharedContext.currentPresentationData.with { $0 }
        super.init(navigationBarPresentationData: NavigationBarPresentationData(presentationData: self.presentationData))
        self.statusBar.statusBarStyle = self.presentationData.theme.rootController.statusBarStyle.style
        self.title = "Перевод"
        self.table.dataSource = self; self.table.delegate = self
        self.table.rowHeight = UITableView.automaticDimension; self.table.estimatedRowHeight = 54
        self.table.sectionHeaderHeight = UITableView.automaticDimension; self.table.estimatedSectionHeaderHeight = 36
        self.table.contentInsetAdjustmentBehavior = .never
        self.table.backgroundColor = self.presentationData.theme.list.blocksBackgroundColor
        self.table.separatorColor = self.presentationData.theme.list.itemBlocksSeparatorColor
        self.table.overrideUserInterfaceStyle = self.presentationData.theme.overallDarkAppearance ? .dark : .light
        self.localTarget = NagramiXTranslationSettings.current.target.isEmpty ? self.interfaceLanguage : NagramiXTranslationSettings.current.target
        self.localSource = NagramiXTranslationLanguage.base(self.localTarget) == "en" ? "ru" : "en"
        self.observer = NotificationCenter.default.addObserver(forName: NagramiXTranslationSettings.changed, object: nil, queue: .main) { [weak self] _ in self?.refresh() }
    }
    public required init(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    deinit { if let observer { NotificationCenter.default.removeObserver(observer) } }

    public override func loadDisplayNode() {
        self.displayNode = ASDisplayNode()
        self.displayNode.backgroundColor = self.presentationData.theme.list.blocksBackgroundColor
        self.displayNode.view.addSubview(self.table)
        self.displayNodeDidLoad()
    }
    public override func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
        self.table.frame = CGRect(origin: .zero, size: layout.size)
        self.table.contentInset.top = self.navigationLayout(layout: layout).navigationFrame.maxY
        self.table.contentInset.bottom = max(layout.intrinsicInsets.bottom, layout.inputHeight ?? 0)
        self.table.scrollIndicatorInsets = self.table.contentInset
    }
    private func show(_ page: Page, title: String, selectedCode: String? = nil, selected: ((String) -> Void)? = nil) {
        let controller = NagramiXTranslationSettingsController(context: self.context)
        controller.page = page; controller.title = title; controller.languageSelected = selected; controller.pickerLanguage = selectedCode
        if case let .credential(provider) = page { controller.configureFields(provider) }
        self.push(controller)
    }
    public func numberOfSections(in tableView: UITableView) -> Int {
        if case .settings = self.page { return 3 }
        if case .credential = self.page { return 3 }
        return 1
    }
    public func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        switch self.page {
        case .settings: return [3, 6, 4][section]
        case .keys: return 3
        case .credential: return section == 0 ? 3 : 1
        case .languages, .ignored: return supportedTranslationLanguages.count
        case .local: return 3
        }
    }
    public func tableView(_ tableView: UITableView, titleForHeaderInSection section: Int) -> String? {
        if case .settings = self.page { return ["ПЕРЕВОД", "ПЕРЕВОДЧИК", "ДОПОЛНИТЕЛЬНО"][section] }
        if case .credential = self.page { return ["ДОСТУП И МОДЕЛЬ", "ТЕМПЕРАТУРА", ""][section] }
        return nil
    }
    public func tableView(_ tableView: UITableView, viewForHeaderInSection section: Int) -> UIView? {
        guard let text = self.tableView(tableView, titleForHeaderInSection: section) else { return nil }
        let header = UITableViewHeaderFooterView(reuseIdentifier: nil)
        var configuration = UIListContentConfiguration.groupedHeader()
        configuration.text = text
        configuration.textProperties.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)
        configuration.textProperties.color = self.presentationData.theme.list.sectionHeaderTextColor
        configuration.textProperties.numberOfLines = 0
        header.contentConfiguration = configuration
        return header
    }
    public func tableView(_ tableView: UITableView, titleForFooterInSection section: Int) -> String? {
        switch self.page {
        case .settings:
            if section == 0 { return "Перевод личных чатов, групп и каналов. Пункт «Перевести» доступен для текста на другом языке, чем язык приложения." }
            if section == 1 { return "Apple — офлайн после загрузки языков. Google и Яндекс — бесплатно через интернет, без ключей. Нейросети используют ваш ключ и доступную ему квоту. Текст отправляется выбранному сервису." }
        case let .credential(provider):
            if section == 0 {
                if provider == .gemini { return "У Google AI Studio есть бесплатная квота для подходящих аккаунтов и моделей. Для неё тоже нужен собственный ключ. Платный или бесплатный тариф определяется вашим проектом Google. Ключ хранится в Keychain этого iPhone." }
                return "Используется только ваш API-ключ. Бесплатные или пробные кредиты применяются сервисом, если доступны аккаунту. Бесплатный чат на сайте не предоставляет бесплатный API. Ключ хранится в Keychain этого iPhone."
            }
            if section == 1 { return "Ниже — более предсказуемые формулировки, выше — больше вариативности. Это не оценка качества. Для неизвестной модели или модели без поддержки температуры параметр не отправляется." }
            return nil
        case .local: return "Выберите пару языков и загрузите модели Apple. Для загрузки нужен интернет, сам перевод выполняется на устройстве. Требуется iOS 18 или новее."
        case .ignored: return "Эти языки не предлагаются для перевода. Язык приложения всегда исключён автоматически."
        default: break
        }
        return nil
    }
    public func tableView(_ tableView: UITableView, willDisplayFooterView view: UIView, forSection section: Int) {
        guard let header = view as? UITableViewHeaderFooterView else { return }
        header.textLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)
        header.textLabel?.textColor = self.presentationData.theme.list.freeTextColor
        header.textLabel?.numberOfLines = 0
    }
    public func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = UITableViewCell(style: .subtitle, reuseIdentifier: nil)
        self.configure(cell, path: indexPath)
        return cell
    }
    private func configure(_ cell: UITableViewCell, path: IndexPath) {
        let value = NagramiXTranslationSettings.current
        cell.backgroundColor = self.presentationData.theme.list.itemBlocksBackgroundColor
        cell.textLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
        cell.textLabel?.textColor = self.presentationData.theme.list.itemPrimaryTextColor
        cell.textLabel?.numberOfLines = 0
        cell.detailTextLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)
        cell.detailTextLabel?.textColor = self.presentationData.theme.list.itemSecondaryTextColor
        cell.detailTextLabel?.numberOfLines = 0
        cell.tintColor = self.presentationData.theme.list.itemAccentColor
        cell.accessoryType = .none; cell.accessoryView = nil
        cell.accessibilityTraits = .button
        switch self.page {
        case .settings:
            if path.section == 0 {
                cell.textLabel?.text = ["Перевод сообщений", "Автоперевод чатов", "Язык перевода"][path.row]
                if path.row < 2 {
                    let toggle = UISwitch()
                    toggle.tag = path.row
                    toggle.isOn = path.row == 0 ? value.enabled : value.automatic
                    toggle.isEnabled = path.row == 0 || value.enabled
                    toggle.onTintColor = self.presentationData.theme.list.itemAccentColor
                    toggle.accessibilityLabel = cell.textLabel?.text
                    toggle.addTarget(self, action: #selector(self.toggleChanged(_:)), for: .valueChanged)
                    cell.accessoryView = toggle; cell.selectionStyle = .none
                } else {
                    cell.detailTextLabel?.text = self.languageTitle(value.target.isEmpty ? self.interfaceLanguage : value.target)
                    cell.accessoryType = .disclosureIndicator
                }
            } else if path.section == 1 {
                let provider = NagramiXTranslationProvider.allCases[path.row]
                cell.textLabel?.text = provider.title
                cell.detailTextLabel?.text = provider == .apple ? "На устройстве" : (provider.isFreeWeb ? "Бесплатно · Интернет" : (provider == .gemini ? "Свой ключ · Доступна бесплатная квота" : "Свой ключ · Квота сервиса"))
                cell.accessoryType = value.provider == provider ? .checkmark : .none
                if value.provider == provider { cell.accessibilityTraits.insert(.selected) }
            } else {
                cell.textLabel?.text = ["Языки на устройстве", "Ключи и параметры нейросетей", "Не переводить", "Вернуть скрытые панели"][path.row]
                cell.accessoryType = .disclosureIndicator
                if path.row == 2 { cell.detailTextLabel?.text = value.ignored.map(self.languageTitle).joined(separator: ", ") }
            }
        case .keys:
            let provider = NagramiXTranslationProvider.allCases.filter { $0.isLanguageModel }[path.row]
            cell.textLabel?.text = provider.title
            cell.detailTextLabel?.text = NagramiXTranslationKeys.read(provider)?.key.isEmpty == false ? "Ключ сохранён" : "Ключ не задан"
            cell.accessoryType = .disclosureIndicator
        case let .credential(provider):
            let fields = [self.keyField, self.modelField]
            if path.section == 0, path.row < fields.count {
                let field = fields[path.row]
                field.removeFromSuperview(); field.translatesAutoresizingMaskIntoConstraints = false
                cell.contentView.addSubview(field)
                NSLayoutConstraint.activate([field.leadingAnchor.constraint(equalTo: cell.contentView.leadingAnchor, constant: 20),
                    field.trailingAnchor.constraint(equalTo: cell.contentView.trailingAnchor, constant: -20),
                    field.topAnchor.constraint(equalTo: cell.contentView.topAnchor, constant: 15),
                    field.bottomAnchor.constraint(equalTo: cell.contentView.bottomAnchor, constant: -15)])
            } else if path.section == 0 { cell.textLabel?.text = provider == .gemini ? "Получить ключ Google AI Studio" : "Открыть кабинет API"; cell.accessoryType = .disclosureIndicator }
            else if path.section == 1 { self.configureTemperature(cell, provider: provider) }
            else { cell.textLabel?.text = "Удалить ключ"; cell.textLabel?.textColor = self.presentationData.theme.list.itemDestructiveColor }
        case .languages, .ignored:
            let code = supportedTranslationLanguages[path.row]
            cell.textLabel?.text = self.languageTitle(code)
            let selected: Bool
            if case .ignored = self.page { selected = value.ignored.contains { NagramiXTranslationLanguage.base($0) == NagramiXTranslationLanguage.base(code) } }
            else { selected = (self.pickerLanguage ?? (value.target.isEmpty ? self.interfaceLanguage : value.target)).lowercased() == code.lowercased() }
            cell.accessoryType = selected ? .checkmark : .none
        case .local:
            cell.textLabel?.text = ["Исходный язык", "Язык перевода", "Загрузить языки"][path.row]
            if path.row < 2 { cell.detailTextLabel?.text = self.languageTitle(path.row == 0 ? self.localSource : self.localTarget); cell.accessoryType = .disclosureIndicator }
        }
    }
    private func languageTitle(_ code: String) -> String { NagramiXTranslationLanguage.title(code, interface: self.interfaceLanguage) }
    private func refresh() {
        for path in self.table.indexPathsForVisibleRows ?? [] {
            // Editable fields retain their cursor/selection and are never recreated on notification.
            if case .credential = self.page { continue }
            if let cell = self.table.cellForRow(at: path) { self.configure(cell, path: path) }
        }
    }
    private func alert(_ text: String) {
        let controller = UIAlertController(title: "Перевод", message: text, preferredStyle: .alert)
        controller.addAction(UIAlertAction(title: self.presentationData.strings.Common_OK, style: .default))
        self.present(controller, animated: true)
    }
    @objc private func toggleChanged(_ sender: UISwitch) {
        if sender.tag == 1, sender.isOn, let error = nagramiXTranslationAvailability(NagramiXTranslationSettings.current) {
            sender.setOn(false, animated: true); self.alert(error.text); return
        }
        NagramiXTranslationSettings.update { value in
            if sender.tag == 0 { value.enabled = sender.isOn }
            else { value.automatic = sender.isOn }
        }
    }
    public func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        tableView.deselectRow(at: indexPath, animated: true)
        switch self.page {
        case .settings:
            if indexPath.section == 0, indexPath.row == 2 {
                self.show(.languages, title: "Язык перевода", selected: { code in NagramiXTranslationSettings.update { $0.target = code } })
            } else if indexPath.section == 1 {
                let provider = NagramiXTranslationProvider.allCases[indexPath.row]
                NagramiXTranslationSettings.update { $0.provider = provider }
                if let error = nagramiXTranslationAvailability(NagramiXTranslationSettings.current), NagramiXTranslationSettings.current.automatic {
                    NagramiXTranslationSettings.update { $0.automatic = false }; self.alert(error.text)
                }
            } else if indexPath.section == 2 {
                switch indexPath.row {
                case 0: self.show(.local, title: "Языки на устройстве")
                case 1: self.show(.keys, title: "Нейросети")
                case 2: self.show(.ignored, title: "Не переводить")
                default: NagramiXTranslationSettings.revealPanels(); self.alert("Панели перевода снова будут отображаться в подходящих чатах.")
                }
            }
        case .keys:
            let provider = NagramiXTranslationProvider.allCases.filter { $0.isLanguageModel }[indexPath.row]
            self.show(.credential(provider), title: provider.title)
        case let .credential(provider):
            if indexPath.section == 0, indexPath.row == 2 {
                let url = provider == .gemini ? "https://aistudio.google.com/apikey" : (provider == .chatgpt ? "https://platform.openai.com/api-keys" : "https://platform.deepseek.com/api_keys")
                if let url = URL(string: url) { UIApplication.shared.open(url) }
            } else if indexPath.section == 2 {
                if NagramiXTranslationKeys.save(nil, provider: provider) { self.keyField.text = ""; self.dismiss() }
                else { self.alert("Не удалось удалить ключ из Keychain.") }
            }
        case .languages:
            self.languageSelected?(supportedTranslationLanguages[indexPath.row]); self.dismiss()
        case .ignored:
            let code = NagramiXTranslationLanguage.base(supportedTranslationLanguages[indexPath.row])
            NagramiXTranslationSettings.update { value in
                if value.ignored.contains(code) { value.ignored.removeAll { $0 == code } } else { value.ignored.append(code) }
            }
        case .local:
            if indexPath.row == 0 { self.show(.languages, title: "Исходный язык", selectedCode: self.localSource, selected: { [weak self] code in self?.localSource = code; self?.refresh() }) }
            else if indexPath.row == 1 { self.show(.languages, title: "Язык перевода", selectedCode: self.localTarget, selected: { [weak self] code in self?.localTarget = code; self?.refresh() }) }
            else { nagramiXPrepareTranslationLanguages(presenter: self, source: self.localSource, target: self.localTarget) }
        }
    }
    private func configureFields(_ provider: NagramiXTranslationProvider) {
        let credentials = NagramiXTranslationKeys.read(provider)
        self.keyField.text = credentials?.key; self.keyField.isSecureTextEntry = true; self.keyField.placeholder = "API-ключ"
        self.modelField.text = NagramiXTranslationSettings.current.models[provider.rawValue] ?? provider.defaultModel; self.modelField.placeholder = "Модель"
        self.modelField.addTarget(self, action: #selector(self.modelChanged), for: .editingChanged)
        for field in [self.keyField, self.modelField] {
            field.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
            field.textColor = self.presentationData.theme.list.itemPrimaryTextColor
            field.autocorrectionType = .no; field.autocapitalizationType = .none; field.spellCheckingType = .no
            field.smartQuotesType = .no; field.smartDashesType = .no; field.keyboardType = .asciiCapable
            field.clearButtonMode = .whileEditing
        }
        self.navigationItem.rightBarButtonItem = UIBarButtonItem(title: "Сохранить", style: .done, target: self, action: #selector(self.saveCredentials))
    }
    @objc private func saveCredentials() {
        guard case let .credential(provider) = self.page else { return }
        let key = (self.keyField.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        let model = (self.modelField.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        guard key.utf8.count <= 4096, !key.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }) else { self.alert("Укажите корректный API-ключ."); return }
        guard !provider.isLanguageModel || (!model.isEmpty && model.count <= 128 && model.range(of: "^[A-Za-z0-9._:-]+$", options: .regularExpression) != nil) else { self.alert("Укажите идентификатор модели."); return }
        guard NagramiXTranslationKeys.save(key.isEmpty ? nil : NagramiXTranslationCredential(key: key, folder: ""), provider: provider) else { self.alert("Не удалось сохранить ключ в Keychain."); return }
        if provider.isLanguageModel { NagramiXTranslationSettings.update { $0.models[provider.rawValue] = model } }
        self.dismiss()
    }
    private func configureTemperature(_ cell: UITableViewCell, provider: NagramiXTranslationProvider) {
        let stack = UIStackView(); stack.axis = .vertical; stack.spacing = 8
        let label = UILabel(); label.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
        label.textColor = self.presentationData.theme.list.itemPrimaryTextColor; label.numberOfLines = 0
        let slider = UISlider(); slider.minimumValue = 0; slider.maximumValue = 2
        slider.value = Float(NagramiXTranslationSettings.current.temperature(for: provider))
        slider.tintColor = self.presentationData.theme.list.itemAccentColor
        slider.accessibilityLabel = "Температура"
        slider.addTarget(self, action: #selector(self.temperatureMoved(_:)), for: .valueChanged)
        slider.addTarget(self, action: #selector(self.temperatureSaved(_:)), for: [.touchUpInside, .touchUpOutside, .touchCancel])
        stack.addArrangedSubview(label); stack.addArrangedSubview(slider)
        stack.translatesAutoresizingMaskIntoConstraints = false; cell.contentView.addSubview(stack)
        NSLayoutConstraint.activate([stack.leadingAnchor.constraint(equalTo: cell.contentView.leadingAnchor, constant: 20),
            stack.trailingAnchor.constraint(equalTo: cell.contentView.trailingAnchor, constant: -20),
            stack.topAnchor.constraint(equalTo: cell.contentView.topAnchor, constant: 15),
            stack.bottomAnchor.constraint(equalTo: cell.contentView.bottomAnchor, constant: -15)])
        cell.selectionStyle = .none; self.temperatureSlider = slider; self.temperatureLabel = label
        self.modelChanged(); self.temperatureMoved(slider)
    }
    @objc private func modelChanged() {
        guard case let .credential(provider) = self.page else { return }
        let model = (self.modelField.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        self.temperatureSlider?.isEnabled = provider.supportsTemperature(model: model)
        if let slider = self.temperatureSlider { self.temperatureMoved(slider) }
    }
    @objc private func temperatureMoved(_ sender: UISlider) {
        sender.value = (sender.value * 10).rounded() / 10
        let value = String(format: "%.1f", Double(sender.value)).replacingOccurrences(of: ".", with: ",")
        self.temperatureLabel?.text = sender.isEnabled ? "Температура: " + value : "Температура: управляется моделью"
        sender.accessibilityValue = value
        // VoiceOver changes do not necessarily produce a touch-up event.
        if UIAccessibility.isVoiceOverRunning { self.temperatureSaved(sender) }
    }
    @objc private func temperatureSaved(_ sender: UISlider) {
        guard sender.isEnabled, case let .credential(provider) = self.page else { return }
        NagramiXTranslationSettings.update { value in
            var temperatures = value.temperatures ?? [:]; temperatures[provider.rawValue] = Double(sender.value)
            value.temperatures = temperatures
        }
    }
}

public func nagramiXTranslationAvailability(_ value: NagramiXTranslationConfiguration) -> NagramiXTranslationFailure? {
    if value.provider == .apple {
        if #available(iOS 18.0, *) { return nil }
        return .unavailable
    }
    if value.provider.isFreeWeb { return nil }
    guard let credentials = NagramiXTranslationKeys.read(value.provider), !credentials.key.isEmpty else { return .missingKey }
    return nil
}
