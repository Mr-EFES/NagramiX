import Foundation
import UIKit
import Display
import AsyncDisplayKit
import AccountContext
import TelegramPresentationData
import ItemListUI
import TelegramCore
import SwiftSignalKit

public final class NagramiXTranslationSettingsController: ViewController, UITableViewDataSource, UITableViewDelegate, UISearchBarDelegate {
    private enum Page {
        case settings, languages, preferred, credential(NagramiXTranslationProvider)
    }
    private let context: AccountContext
    private let presentationData: PresentationData
    private let table = UITableView(frame: .zero, style: .insetGrouped)
    private let search = UISearchBar()
    private var page: Page = .settings
    private var observer: NSObjectProtocol?
    private let premiumDisposable = MetaDisposable()
    private var isPremium: Bool?
    // Stable logical section IDs; hide the Telegram group until Premium is known.
    private var settingsSections: [Int] { self.isPremium == true ? [0, 1, 2, 3] : [0, 2, 3] }
    private var searchText = ""
    private let keyField = UITextField()
    private var draftModel = ""
    private var draftTemperature = 0.2
    private weak var temperatureSlider: UISlider?
    private weak var temperatureLabel: UILabel?
    private var interfaceLanguage: String { NagramiXTranslationLanguage.base(self.presentationData.strings.baseLanguageCode) }
    private var languages: [String] {
        let query = self.searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        return supportedTranslationLanguages.filter { code in
            query.isEmpty || code.localizedCaseInsensitiveContains(query) || self.languageTitle(code).localizedCaseInsensitiveContains(query)
        }.sorted { self.languageTitle($0).localizedStandardCompare(self.languageTitle($1)) == .orderedAscending }
    }

    public init(context: AccountContext) {
        self.context = context
        self.presentationData = context.sharedContext.currentPresentationData.with { $0 }
        super.init(navigationBarPresentationData: NavigationBarPresentationData(presentationData: self.presentationData))
        self.statusBar.statusBarStyle = self.presentationData.theme.rootController.statusBarStyle.style
        self.title = "Переводчик"
        self.table.dataSource = self
        self.table.delegate = self
        self.table.rowHeight = UITableView.automaticDimension
        self.table.estimatedRowHeight = 48
        self.table.sectionHeaderHeight = UITableView.automaticDimension
        self.table.estimatedSectionHeaderHeight = 32
        self.table.contentInsetAdjustmentBehavior = .never
        self.table.keyboardDismissMode = .interactive
        self.table.backgroundColor = self.presentationData.theme.list.blocksBackgroundColor
        self.table.separatorColor = self.presentationData.theme.list.itemBlocksSeparatorColor
        self.table.tintColor = self.presentationData.theme.list.itemAccentColor
        self.table.overrideUserInterfaceStyle = self.presentationData.theme.overallDarkAppearance ? .dark : .light
        self.search.delegate = self
        self.search.placeholder = "Поиск языка"
        self.search.searchBarStyle = .minimal
        self.search.tintColor = self.presentationData.theme.list.itemAccentColor
        self.search.searchTextField.textColor = self.presentationData.theme.list.itemPrimaryTextColor
        self.premiumDisposable.set((context.engine.data.subscribe(TelegramEngine.EngineData.Item.Peer.Peer(id: context.account.peerId))
        |> deliverOnMainQueue).start(next: { [weak self] peer in
            guard let self else { return }
            self.isPremium = peer?.isPremium ?? false
            if self.isNodeLoaded { self.table.reloadData() }
        }))
        self.observer = NotificationCenter.default.addObserver(forName: NagramiXTranslationSettings.changed, object: nil, queue: .main) { [weak self] _ in
            guard let self else { return }
            if case .credential = self.page { return }
            self.table.reloadData()
        }
    }
    public required init(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    deinit { self.premiumDisposable.dispose(); if let observer { NotificationCenter.default.removeObserver(observer) } }

    public override func loadDisplayNode() {
        self.displayNode = ASDisplayNode()
        self.displayNode.backgroundColor = self.presentationData.theme.list.blocksBackgroundColor
        self.displayNode.view.addSubview(self.table)
        if case .languages = self.page { self.installSearch() }
        if case .preferred = self.page { self.installSearch() }
        self.displayNodeDidLoad()
    }
    private func installSearch() {
        self.search.sizeToFit()
        self.table.tableHeaderView = self.search
    }
    public override func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
        self.table.frame = CGRect(origin: .zero, size: layout.size)
        self.table.contentInset.top = self.navigationLayout(layout: layout).navigationFrame.maxY
        self.table.contentInset.bottom = max(layout.intrinsicInsets.bottom, layout.inputHeight ?? 0)
        self.table.scrollIndicatorInsets = self.table.contentInset
    }
    private func show(_ page: Page, title: String) {
        let controller = NagramiXTranslationSettingsController(context: self.context)
        controller.page = page
        controller.title = title
        if case let .credential(provider) = page { controller.configureFields(provider) }
        self.push(controller)
    }
    public func numberOfSections(in tableView: UITableView) -> Int {
        switch self.page {
        case .settings: return self.settingsSections.count
        case .languages: return 2
        case let .credential(provider): return provider.supportsTemperature(model: self.draftModel) ? 2 : 1
        case .preferred: return 1
        }
    }
    public func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        switch self.page {
        case .settings:
            let section = self.settingsSections[section]
            if section == 0 { return 5 }
            if section == 1 { return 1 }
            if section == 2 { return 3 }
            return 3 + (NagramiXTranslationSettings.current.provider.requiresAPIKey ? 1 : 0)
        case .languages: return section == 0 ? 1 : self.languages.count
        case .preferred: return self.languages.count
        case .credential: return section == 0 ? 3 : 1
        }
    }
    public func tableView(_ tableView: UITableView, titleForHeaderInSection section: Int) -> String? {
        switch self.page {
        case .settings: return ["ПЕРЕВОД", "TELEGRAM", "СЛОВАРИ", "ЧЕРЕЗ ИНТЕРНЕТ"][self.settingsSections[section]]
        case .languages: return section == 0 ? nil : "ДРУГОЙ ЯЗЫК"
        case .credential: return section == 0 ? "ДОСТУП И МОДЕЛЬ" : "ТЕМПЕРАТУРА"
        case .preferred: return nil
        }
    }
    public func tableView(_ tableView: UITableView, viewForHeaderInSection section: Int) -> UIView? {
        guard let text = self.tableView(tableView, titleForHeaderInSection: section) else { return nil }
        let header = UITableViewHeaderFooterView(reuseIdentifier: nil)
        var content = UIListContentConfiguration.groupedHeader()
        content.text = text
        content.textProperties.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)
        content.textProperties.color = self.presentationData.theme.list.sectionHeaderTextColor
        content.textProperties.numberOfLines = 0
        header.contentConfiguration = content
        return header
    }
    public func tableView(_ tableView: UITableView, titleForFooterInSection section: Int) -> String? {
        // No descriptive captions on the approved main settings page.
        return nil
    }
    public func tableView(_ tableView: UITableView, willDisplayFooterView view: UIView, forSection section: Int) {
        guard let footer = view as? UITableViewHeaderFooterView else { return }
        footer.textLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)
        footer.textLabel?.textColor = self.presentationData.theme.list.freeTextColor
        footer.textLabel?.numberOfLines = 0
    }
    public func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let style: UITableViewCell.CellStyle
        if case .languages = self.page, indexPath.section == 0 { style = .subtitle }
        else { style = .value1 }
        let cell = UITableViewCell(style: style, reuseIdentifier: nil)
        cell.backgroundColor = self.presentationData.theme.list.itemBlocksBackgroundColor
        cell.textLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
        cell.textLabel?.textColor = self.presentationData.theme.list.itemPrimaryTextColor
        cell.textLabel?.numberOfLines = 0
        cell.textLabel?.adjustsFontSizeToFitWidth = false
        cell.detailTextLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
        cell.detailTextLabel?.textColor = self.presentationData.theme.list.itemSecondaryTextColor
        cell.detailTextLabel?.numberOfLines = 0
        cell.tintColor = self.presentationData.theme.list.itemAccentColor
        let value = NagramiXTranslationSettings.current
        let target = value.resolvedTarget(interface: self.interfaceLanguage)
        switch self.page {
        case .settings:
            if indexPath.section == 0 {
                cell.textLabel?.text = ["Показать кнопку «Перевести»", "Переводить чаты целиком", "Язык перевода", "Не переводить", "Предпочитаемые языки"][indexPath.row]
                if indexPath.row < 2 {
                    let toggle = UISwitch()
                    toggle.tag = indexPath.row
                    toggle.isOn = indexPath.row == 0 ? value.showsTranslateButton : value.automatic
                    toggle.onTintColor = self.presentationData.theme.list.itemAccentColor
                    toggle.accessibilityLabel = cell.textLabel?.text
                    toggle.addTarget(self, action: #selector(self.toggleChanged(_:)), for: .valueChanged)
                    cell.accessoryView = toggle
                    cell.selectionStyle = .none
                } else {
                    cell.accessoryType = .disclosureIndicator
                    if indexPath.row == 2 { cell.detailTextLabel?.text = self.languageTitle(target) }
                    if indexPath.row == 3 { cell.detailTextLabel?.text = value.effectiveIgnored(interface: self.interfaceLanguage).map(self.languageTitle).joined(separator: ", ") }
                    if indexPath.row == 4 { cell.detailTextLabel?.text = value.ignored.isEmpty ? "Не выбраны" : value.ignored.map(self.languageTitle).joined(separator: ", ") }
                }
            } else if let item = self.providerRow(section: indexPath.section, row: indexPath.row) {
                let provider = item.0
                cell.imageView?.image = nagramiXServiceIcon(item.1 ? "settings" : provider.title)
                cell.textLabel?.text = item.1 ? "Настройки " + provider.title : provider.title
                cell.accessoryType = item.1 ? .disclosureIndicator : (provider == value.provider ? .checkmark : .none)
                if !item.1 && provider == value.provider { cell.accessibilityTraits.insert(.selected) }
            }
        case .languages:
            if indexPath.section == 0 {
                cell.textLabel?.text = "Как в приложении"
                cell.detailTextLabel?.text = "Сейчас: " + self.languageTitle(self.interfaceLanguage)
                cell.detailTextLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)
                cell.accessoryType = value.target.isEmpty ? .checkmark : .none
            } else {
                let code = self.languages[indexPath.row]
                cell.textLabel?.text = self.languageTitle(code)
                cell.accessoryType = !value.target.isEmpty && NagramiXTranslationLanguage.base(value.target) == NagramiXTranslationLanguage.base(code) ? .checkmark : .none
            }
        case .preferred:
            let code = self.languages[indexPath.row]
            let automatic = NagramiXTranslationLanguage.base(code) == NagramiXTranslationLanguage.base(target)
            cell.textLabel?.text = self.languageTitle(code)
            cell.accessoryType = automatic || NagramiXTranslationLanguage.isExcluded(code, ignored: value.ignored) ? .checkmark : .none
            if automatic {
                cell.detailTextLabel?.text = "Язык перевода"
                cell.selectionStyle = .none
                cell.accessibilityTraits.insert(.notEnabled)
            }
        case let .credential(provider):
            if indexPath.section == 0, indexPath.row == 0 {
                self.keyField.removeFromSuperview()
                let label = UILabel()
                label.text = "API-ключ"
                label.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
                label.textColor = self.presentationData.theme.list.itemPrimaryTextColor
                label.numberOfLines = 0
                label.setContentHuggingPriority(.required, for: .horizontal)
                let stack = UIStackView(arrangedSubviews: [label, self.keyField])
                stack.axis = .horizontal
                stack.alignment = .center
                stack.spacing = 12
                self.keyField.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
                stack.translatesAutoresizingMaskIntoConstraints = false
                cell.contentView.addSubview(stack)
                NSLayoutConstraint.activate([
                    stack.leadingAnchor.constraint(equalTo: cell.contentView.leadingAnchor, constant: 20),
                    stack.trailingAnchor.constraint(equalTo: cell.contentView.trailingAnchor, constant: -20),
                    stack.topAnchor.constraint(equalTo: cell.contentView.topAnchor, constant: 15),
                    stack.bottomAnchor.constraint(equalTo: cell.contentView.bottomAnchor, constant: -15)
                ])
                cell.selectionStyle = .none
            } else if indexPath.section == 0, indexPath.row == 1 {
                cell.textLabel?.text = "Модель"
                cell.detailTextLabel?.text = self.draftModel
                cell.accessoryType = .disclosureIndicator
            } else if indexPath.section == 0 {
                cell.textLabel?.text = provider == .gemini ? "Получить ключ в Google AI Studio" : (provider == .chatgpt ? "Получить ключ OpenAI" : "Получить ключ DeepSeek")
                cell.textLabel?.textColor = self.presentationData.theme.list.itemAccentColor
                cell.accessoryType = .disclosureIndicator
            } else { self.configureTemperature(cell, provider: provider) }
        }
        return cell
    }
    private func providerRow(section: Int, row: Int) -> (NagramiXTranslationProvider, Bool)? {
        let section = self.settingsSections[section]
        let providers: [NagramiXTranslationProvider] = section == 1 ? [.telegram] : (section == 2 ? [.apple, .google, .yandex] : [.gemini, .chatgpt, .deepseek])
        var index = 0
        for provider in providers {
            if index == row { return (provider, false) }
            index += 1
            if provider.requiresAPIKey && NagramiXTranslationSettings.current.provider == provider {
                if index == row { return (provider, true) }
                index += 1
            }
        }
        return nil
    }
    private func languageTitle(_ code: String) -> String { NagramiXTranslationLanguage.title(code, interface: self.interfaceLanguage) }
    public func searchBar(_ searchBar: UISearchBar, textDidChange searchText: String) {
        self.searchText = searchText
        self.table.reloadData()
    }
    private func alert(_ text: String) {
        let alert = UIAlertController(title: "Переводчик", message: text, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: self.presentationData.strings.Common_OK, style: .default))
        self.present(alert, animated: true)
    }
    @objc private func toggleChanged(_ sender: UISwitch) {
        if sender.tag == 1, sender.isOn, NagramiXTranslationSettings.current.provider == .telegram, self.isPremium != true {
            sender.setOn(false, animated: true)
            self.alert(self.isPremium == nil ? "Проверяем статус аккаунта. Попробуйте ещё раз." : NagramiXTranslationFailure.premiumRequired.text)
            return
        }
        if sender.tag == 1, sender.isOn, let error = nagramiXTranslationAvailability(NagramiXTranslationSettings.current) {
            sender.setOn(false, animated: true)
            self.alert(error.text)
            return
        }
        NagramiXTranslationSettings.update { value in
            if sender.tag == 0 { value.showTranslateButton = sender.isOn }
            else { value.automatic = sender.isOn }
        }
        if sender.tag == 1 && sender.isOn { NagramiXTranslationSettings.revealPanels() }
    }
    public func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        tableView.deselectRow(at: indexPath, animated: true)
        switch self.page {
        case .settings:
            if indexPath.section == 0 {
                if indexPath.row == 2 { self.show(.languages, title: "Язык перевода") }
                if indexPath.row == 3 { self.show(.preferred, title: "Не переводить") }
                if indexPath.row == 4 { self.show(.preferred, title: "Предпочитаемые языки") }
            } else if let item = self.providerRow(section: indexPath.section, row: indexPath.row) {
                if item.1 { self.show(.credential(item.0), title: item.0.title) }
                else {
                    if item.0 == .telegram, self.isPremium != true {
                        self.alert(self.isPremium == nil ? "Проверяем статус аккаунта. Попробуйте ещё раз." : NagramiXTranslationFailure.premiumRequired.text)
                        return
                    }
                    NagramiXTranslationSettings.update { $0.provider = item.0 }
                }
            }
        case .languages:
            let code = indexPath.section == 0 ? "" : self.languages[indexPath.row]
            NagramiXTranslationSettings.update { $0.target = code }
            self.dismiss()
        case .preferred:
            let code = NagramiXTranslationLanguage.base(self.languages[indexPath.row])
            let target = NagramiXTranslationSettings.current.resolvedTarget(interface: self.interfaceLanguage)
            guard code != NagramiXTranslationLanguage.base(target) else { return }
            NagramiXTranslationSettings.update { value in
                if NagramiXTranslationLanguage.isExcluded(code, ignored: value.ignored) {
                    value.ignored.removeAll { NagramiXTranslationLanguage.base($0) == code }
                } else { value.ignored.append(code) }
            }
        case let .credential(provider):
            if indexPath.section == 0, indexPath.row == 1 { self.showModelPicker(provider) }
            if indexPath.section == 0, indexPath.row == 2 {
                let path = provider == .gemini ? "https://aistudio.google.com/apikey" : (provider == .chatgpt ? "https://platform.openai.com/api-keys" : "https://platform.deepseek.com/api_keys")
                if let url = URL(string: path) { UIApplication.shared.open(url) }
            }
        }
    }
    private func configureFields(_ provider: NagramiXTranslationProvider) {
        self.keyField.text = NagramiXTranslationKeys.read(provider)?.key
        self.keyField.isSecureTextEntry = true
        self.keyField.placeholder = "Введите ключ"
        self.keyField.widthAnchor.constraint(greaterThanOrEqualToConstant: 64).isActive = true
        self.keyField.textAlignment = .right
        self.keyField.accessibilityLabel = "API-ключ"
        self.keyField.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
        self.keyField.textColor = self.presentationData.theme.list.itemPrimaryTextColor
        self.keyField.autocorrectionType = .no
        self.keyField.autocapitalizationType = .none
        self.keyField.spellCheckingType = .no
        self.keyField.smartQuotesType = .no
        self.keyField.smartDashesType = .no
        self.keyField.keyboardType = .asciiCapable
        self.keyField.clearButtonMode = .whileEditing
        self.draftModel = NagramiXTranslationSettings.current.models[provider.rawValue] ?? provider.defaultModel
        self.draftTemperature = NagramiXTranslationSettings.current.temperature(for: provider)
        self.navigationItem.rightBarButtonItem = UIBarButtonItem(title: "Сохранить", style: .done, target: self, action: #selector(self.saveCredentials))
    }
    private func showModelPicker(_ provider: NagramiXTranslationProvider) {
        self.view.endEditing(true)
        let defaults: [String]
        switch provider {
        case .gemini: defaults = ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]
        case .chatgpt: defaults = ["gpt-5.4-mini", "gpt-5.4-nano", "gpt-4.1-mini", "gpt-4o-mini"]
        case .deepseek: defaults = ["deepseek-flash", "deepseek-v4-pro"]
        default: return
        }
        let choices = defaults.contains(self.draftModel) ? defaults : [self.draftModel] + defaults
        let picker = NagramiXTranslationModelPicker(models: choices, selected: self.draftModel, presentationData: self.presentationData) { [weak self] model in
            guard let self else { return }
            self.draftModel = model
            self.table.reloadData()
        }
        self.present(picker, animated: true)
    }
    @objc private func saveCredentials() {
        guard case let .credential(provider) = self.page else { return }
        self.view.endEditing(true)
        let key = (self.keyField.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        let model = self.draftModel
        guard key.utf8.count <= 4096, !key.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }) else { self.alert("Укажите корректный API-ключ."); return }
        guard !model.isEmpty, model.count <= 128, model.range(of: "^[A-Za-z0-9._:-]+$", options: .regularExpression) != nil else { self.alert("Выберите модель."); return }
        let temperature = self.draftTemperature
        var saved = false
        // Hold the configuration lock while replacing the credential, then
        // publish one revision for the key/model/temperature combination.
        NagramiXTranslationSettings.update { value in
            guard NagramiXTranslationKeys.save(key.isEmpty ? nil : .init(key: key, folder: ""), provider: provider, notify: false) else { return }
            value.models[provider.rawValue] = model
            var temperatures = value.temperatures ?? [:]
            temperatures[provider.rawValue] = temperature
            value.temperatures = temperatures
            value.revision = UUID().uuidString
            saved = true
        }
        guard saved else { self.alert("Не удалось сохранить ключ в Keychain."); return }
        self.dismiss()
    }
    private func configureTemperature(_ cell: UITableViewCell, provider: NagramiXTranslationProvider) {
        let stack = UIStackView()
        stack.axis = .vertical
        stack.spacing = 8
        let label = UILabel()
        label.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
        label.textColor = self.presentationData.theme.list.itemPrimaryTextColor
        label.numberOfLines = 0
        let slider = UISlider()
        slider.minimumValue = 0
        slider.maximumValue = 1
        slider.value = Float(self.draftTemperature)
        slider.isEnabled = provider.supportsTemperature(model: self.draftModel)
        slider.tintColor = self.presentationData.theme.list.itemAccentColor
        slider.accessibilityLabel = "Температура"
        slider.addTarget(self, action: #selector(self.temperatureMoved(_:)), for: .valueChanged)
        stack.addArrangedSubview(label)
        stack.addArrangedSubview(slider)
        stack.translatesAutoresizingMaskIntoConstraints = false
        cell.contentView.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: cell.contentView.leadingAnchor, constant: 20),
            stack.trailingAnchor.constraint(equalTo: cell.contentView.trailingAnchor, constant: -20),
            stack.topAnchor.constraint(equalTo: cell.contentView.topAnchor, constant: 15),
            stack.bottomAnchor.constraint(equalTo: cell.contentView.bottomAnchor, constant: -15)
        ])
        cell.selectionStyle = .none
        self.temperatureSlider = slider
        self.temperatureLabel = label
        self.renderTemperature()
    }
    @objc private func temperatureMoved(_ sender: UISlider) {
        sender.value = (sender.value * 10).rounded() / 10
        self.draftTemperature = Double(sender.value)
        self.renderTemperature()
    }
    private func renderTemperature() {
        guard let slider = self.temperatureSlider else { return }
        let percent = "\(Int((slider.value * 100).rounded()))%"
        self.temperatureLabel?.text = slider.isEnabled ? "Температура: " + percent : "Температура: управляется моделью"
        slider.accessibilityValue = percent
    }
}

public func nagramiXTranslationAvailability(_ value: NagramiXTranslationConfiguration) -> NagramiXTranslationFailure? {
    if value.provider == .apple {
        if #available(iOS 18.0, *) { return nil }
        return .unavailable
    }
    if value.provider == .telegram || value.provider.isFreeWeb { return nil }
    guard let key = NagramiXTranslationKeys.read(value.provider), !key.key.isEmpty else { return .missingKey }
    return nil
}
