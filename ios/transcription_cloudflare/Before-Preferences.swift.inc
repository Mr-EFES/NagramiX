import Foundation
import UIKit
import Speech
import Network
import Display
import AsyncDisplayKit
import AccountContext
import TelegramPresentationData
import ItemListUI

public final class NagramiXTranscriptionSettingsController: ViewController, UITableViewDataSource, UITableViewDelegate, UIPickerViewDataSource, UIPickerViewDelegate {
    private enum Page { case settings, apple, appleLanguages, whisper, whisperLanguages, credential(NagramiXTranscriptionProvider), wheel(NagramiXTranscriptionProvider), license }
    private struct Row { let title: String; let subtitle: String?; let action: Action }
    private enum Action { case automatic, localFallback, unavailable, provider(NagramiXTranscriptionProvider), open(Page, String), language(String), appleLanguage(String), model(NagramiXWhisperModel), key, wheel, cloudConsent, website(String), license }
    private let context: AccountContext
    private let presentationData: PresentationData
    private let table = UITableView(frame: .zero, style: .insetGrouped)
    private let keyField = UITextField()
    private let picker = UIPickerView()
    private var page: Page = .settings
    private var observers: [NSObjectProtocol] = []
    private var appleSupported: [Locale] = []
    private var appleInstalled: Set<String> = []
    private var appleLoading: String?
    private var appleHasManagedDownloads = false
    private var selectedModel = ""
    private var selectedConsent = false
    private var modelChosen: ((String) -> Void)?
    private var networkMonitor: NWPathMonitor?
    private let networkQueue = DispatchQueue(label: "NagramiXTranscription.Network")
    private var networkIsExpensive = false
    private var networkKnown = false
    private var sections: [(String?, [Row])] = []
    private func whisperModelTitle(_ model: NagramiXWhisperModel) -> String {
        let russian = self.presentationData.strings.baseLanguageCode.lowercased().hasPrefix("ru")
        switch model {
        case .base_full: return russian ? "Базовая" : "Basic"
        case .small_full: return russian ? "Малая" : "Small"
        case .medium: return russian ? "Средняя" : "Medium"
        case .large_v3: return russian ? "Максимальная" : "Maximum"
        default: return model.title
        }
    }
    private static let whisperLanguages = "en zh de es ru ko fr ja pt tr pl ca nl ar sv it id hi fi vi he uk el ms cs ro da hu ta no th ur hr bg lt la mi ml cy sk te fa lv bn sr az sl kn et mk br eu is hy ne mn bs kk sq sw gl mr pa si km sn yo so af oc ka be tg sd gu am yi lo uz fo ht ps tk nn mt sa lb my bo tl mg as tt haw ln ha ba jw su yue".split(separator: " ").map(String.init)
    private static func label(_ code: String) -> String {
        if code == "auto" { return "Автоопределение" }
        let locale = Locale(identifier: "ru_RU")
        return (locale.localizedString(forIdentifier: code) ?? code).capitalized(with: locale)
    }
    private static func modelChoices(_ provider: NagramiXTranscriptionProvider) -> [String] {
        switch provider {
        case .gemini: return ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]
        case .chatgpt: return ["gpt-transcribe", "gpt-4o-mini-transcribe", "gpt-4o-transcribe", "whisper-1"]
        case .grok: return ["grok-voice-transcribe-2.0"]
        case .groq: return ["whisper-large-v3-turbo", "whisper-large-v3"]
        default: return []
        }
    }
    public init(context: AccountContext) {
        self.context = context; self.presentationData = context.sharedContext.currentPresentationData.with { $0 }
        super.init(navigationBarPresentationData: NavigationBarPresentationData(presentationData: self.presentationData))
        self.title = "Транскрибация"
        self.statusBar.statusBarStyle = self.presentationData.theme.rootController.statusBarStyle.style
        self.table.dataSource = self; self.table.delegate = self
        self.table.rowHeight = UITableView.automaticDimension; self.table.estimatedRowHeight = 58
        self.table.sectionHeaderHeight = UITableView.automaticDimension; self.table.estimatedSectionHeaderHeight = 36
        self.table.contentInsetAdjustmentBehavior = .never
        self.table.backgroundColor = self.presentationData.theme.list.blocksBackgroundColor
        self.table.separatorColor = self.presentationData.theme.list.itemBlocksSeparatorColor
        self.table.overrideUserInterfaceStyle = self.presentationData.theme.overallDarkAppearance ? .dark : .light
        self.keyField.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
        self.keyField.textColor = self.presentationData.theme.list.itemPrimaryTextColor
        self.keyField.placeholder = "API-ключ"; self.keyField.isSecureTextEntry = true
        self.keyField.autocorrectionType = .no; self.keyField.autocapitalizationType = .none; self.keyField.spellCheckingType = .no
        for name in [NagramiXTranscriptionSettings.changed, NagramiXWhisperModels.changed] {
            self.observers.append(NotificationCenter.default.addObserver(forName: name, object: nil, queue: .main) { [weak self] _ in self?.settingsChanged() })
        }
    }
    public required init(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    deinit { for observer in self.observers { NotificationCenter.default.removeObserver(observer) }; self.networkMonitor?.cancel() }
    public override func loadDisplayNode() {
        self.displayNode = ASDisplayNode(); self.displayNode.backgroundColor = self.presentationData.theme.list.blocksBackgroundColor
        self.displayNode.view.addSubview(self.table); self.displayNodeDidLoad()
        self.refresh()
    }
    public override func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
        self.table.frame = CGRect(origin: .zero, size: layout.size)
        self.table.contentInset.top = self.navigationLayout(layout: layout).navigationFrame.maxY
        self.table.contentInset.bottom = max(layout.intrinsicInsets.bottom, layout.inputHeight ?? 0)
        self.table.scrollIndicatorInsets = self.table.contentInset
    }
    private func show(_ page: Page, _ title: String, selectedModel: String? = nil) -> NagramiXTranscriptionSettingsController {
        let controller = NagramiXTranscriptionSettingsController(context: self.context); controller.page = page; controller.title = title
        if case let .credential(provider) = page {
            controller.keyField.text = NagramiXTranscriptionKeys.read(provider)
            controller.selectedModel = NagramiXTranscriptionSettings.current.models[provider.rawValue] ?? provider.defaultModel
            controller.selectedConsent = NagramiXTranscriptionSettings.current.cloudAllowed[provider.rawValue] == true
            controller.navigationItem.rightBarButtonItem = UIBarButtonItem(title: "Сохранить", style: .done, target: controller, action: #selector(saveCredential))
        }
        if case .wheel = page {
            controller.selectedModel = selectedModel ?? ""
            controller.navigationItem.rightBarButtonItem = UIBarButtonItem(title: "Готово", style: .done, target: controller, action: #selector(finishWheel))
        }
        if case .apple = page { controller.loadAppleLocales() }
        if case .appleLanguages = page { controller.loadAppleLocales() }
        if case .whisper = page { controller.monitorNetwork() }
        self.push(controller); return controller
    }
    private func wheelChoices(_ provider: NagramiXTranscriptionProvider) -> [String] {
        var choices = Self.modelChoices(provider)
        if !self.selectedModel.isEmpty && !choices.contains(self.selectedModel) { choices.insert(self.selectedModel, at: 0) }
        return choices
    }
    private func settingsChanged() {
        if case .apple = self.page { self.loadAppleLocales() } else { self.refresh() }
    }
    private func monitorNetwork() {
        let monitor = NWPathMonitor(); self.networkMonitor = monitor
        monitor.pathUpdateHandler = { [weak self] path in
            let expensive = path.isExpensive
            DispatchQueue.main.async { [weak self] in self?.networkKnown = true; self?.networkIsExpensive = expensive }
        }
        monitor.start(queue: self.networkQueue)
    }
    private func loadAppleLocales() {
        #if compiler(>=6.2)
        if #available(iOS 26.0, *) {
            self.appleHasManagedDownloads = true
            NagramiXTranscriptionAnalyzer.locales { [weak self] available, installed in
                DispatchQueue.main.async { [weak self] in self?.appleSupported = available; self?.appleInstalled = Set(installed.map { $0.identifier }); self?.refresh() }
            }
            return
        }
        #endif
        self.appleSupported = SFSpeechRecognizer.supportedLocales().filter { SFSpeechRecognizer(locale: $0)?.supportsOnDeviceRecognition == true }
        self.appleInstalled = Set(self.appleSupported.map { $0.identifier })
        self.refresh()
    }
    private func appleHas(_ code: String) -> Bool { self.appleInstalled.contains { $0.replacingOccurrences(of:"_",with:"-").lowercased() == code.replacingOccurrences(of:"_",with:"-").lowercased() } }
    private func makeSections() -> [(String?, [Row])] {
        let value = NagramiXTranscriptionSettings.current
        switch self.page {
        case .settings:
            var local: [Row] = []; for provider in [NagramiXTranscriptionProvider.apple, .whisper] {
                local.append(Row(title: provider.title, subtitle: nil, action: .provider(provider)))
                if value.provider == provider { local.append(Row(title: "Настройки " + provider.title, subtitle: nil, action: .open(provider == .apple ? .apple : .whisper, "Настройки " + provider.title))) }
            }
            var cloud: [Row] = []; var providers: [NagramiXTranscriptionProvider] = [.gemini, .chatgpt, .grok]
            if value.provider == .groq { providers.append(.groq) }
            for provider in providers {
                cloud.append(Row(title: provider.title, subtitle: nil, action: .provider(provider)))
                if value.provider == provider { cloud.append(Row(title: "Настройки " + provider.title, subtitle: nil, action: .open(.credential(provider), "Настройки " + provider.title))) }
            }
            return [(nil,[Row(title: "Автоматическая расшифровка", subtitle:nil,action:.automatic), Row(title:"Резервный способ",subtitle:nil,action:.localFallback)]), ("TELEGRAM",[Row(title:"Telegram",subtitle:"Штатная квота аккаунта",action:.provider(.telegram))]), ("НА УСТРОЙСТВЕ",local), ("ЧЕРЕЗ ИНТЕРНЕТ",cloud)]
        case .apple:
            let installed = self.appleSupported.filter { self.appleHas($0.identifier) }.map { Row(title: Self.label($0.identifier), subtitle:self.appleHasManagedDownloads ? "Загружен" : "Доступен на устройстве",action:.language($0.identifier)) }
            return [("ЯЗЫК РЕЧИ",[Row(title:"Автоопределение",subtitle:"Не поддерживается Apple",action:.unavailable),Row(title:Self.label(value.language),subtitle:nil,action:.open(.appleLanguages,"Языки Apple"))]),("ЯЗЫКИ APPLE",installed + [Row(title:"Выбрать и загрузить язык",subtitle:nil,action:.open(.appleLanguages,"Языки Apple"))])]
        case .appleLanguages:
            let ordered = self.appleSupported.sorted { Self.label($0.identifier).localizedCaseInsensitiveCompare(Self.label($1.identifier)) == .orderedAscending }
            return [("ДОСТУПНЫЕ ЯЗЫКИ",ordered.map { Row(title:Self.label($0.identifier),subtitle:self.appleLoading == $0.identifier ? "Загрузка…" : (self.appleHas($0.identifier) ? (self.appleHasManagedDownloads ? "Загружен" : "Доступен на устройстве") : "Загрузить"),action:.appleLanguage($0.identifier)) })]
        case .whisper:
            return [("ЯЗЫК РЕЧИ",[Row(title:Self.label(value.language),subtitle:nil,action:.open(.whisperLanguages,"Язык речи"))]),("МОДЕЛИ",[NagramiXWhisperModel.base_full, .small_full, .medium, .large_v3].map { Row(title:self.whisperModelTitle($0),subtitle:NagramiXWhisperModels.shared.status($0),action:.model($0)) }), (nil,[Row(title:"Лицензия Whisper",subtitle:nil,action:.license)])]
        case .whisperLanguages:
            let names = (value.whisper.englishOnly ? ["en"] : Self.whisperLanguages).sorted { Self.label($0).localizedCaseInsensitiveCompare(Self.label($1)) == .orderedAscending }
            return [(nil, (value.whisper.englishOnly ? [] : [Row(title:"Автоопределение",subtitle:nil,action:.language("auto"))]) + names.map { Row(title:Self.label($0),subtitle:nil,action:.language($0)) })]
        case let .credential(provider):
            let url: String
            switch provider {
            case .gemini: url = "https://aistudio.google.com/apikey"
            case .chatgpt: url = "https://platform.openai.com/api-keys"
            case .grok: url = "https://console.x.ai/"
            case .groq: url = "https://console.groq.com/keys"
            default: url = ""
            }
            return [("ДОСТУП И МОДЕЛЬ",[Row(title:"API-ключ",subtitle:nil,action:.key),Row(title:"Модель",subtitle:self.selectedModel,action:.wheel),Row(title:"Получить API-ключ",subtitle:nil,action:.website(url))])]
        case .wheel: return [(nil,[Row(title:"",subtitle:nil,action:.wheel)])]
        case .license: return [(nil,[Row(title:NagramiXWhisperLicense.text,subtitle:nil,action:.license)])]
        }
    }
    public func numberOfSections(in tableView: UITableView) -> Int { return self.sections.count }
    public func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int { return self.sections[section].1.count }
    public func tableView(_ tableView: UITableView, titleForHeaderInSection section: Int) -> String? { return self.sections[section].0 }
    public func tableView(_ tableView: UITableView, titleForFooterInSection section: Int) -> String? {
        switch self.page {
        case .apple: return section == 0 ? "Для Apple выберите язык речи из доступных на устройстве." : nil
        case .whisper: return section == 1 ? "Модели загружаются отдельно. Большие модели требуют больше места, памяти и времени." : nil
        case let .credential(provider): return "Аудио выбранного сообщения будет отправлено в " + provider.title + ". Доступ и стоимость зависят от вашего ключа и тарифа."
        default: return nil
        }
    }
    public func tableView(_ tableView: UITableView, willDisplayFooterView view: UIView, forSection section: Int) {
        guard let footer = view as? UITableViewHeaderFooterView else { return }
        footer.textLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)
        footer.textLabel?.textColor = self.presentationData.theme.list.freeTextColor; footer.textLabel?.numberOfLines = 0
    }
    public func tableView(_ tableView: UITableView, viewForHeaderInSection section: Int) -> UIView? {
        guard let text = self.sections[section].0 else { return nil }
        let view = UITableViewHeaderFooterView(reuseIdentifier:nil); var config = UIListContentConfiguration.groupedHeader()
        config.text = text; config.textProperties.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)
        config.textProperties.color = self.presentationData.theme.list.sectionHeaderTextColor; config.textProperties.numberOfLines = 0
        view.contentConfiguration = config; return view
    }
    public func tableView(_ tableView: UITableView, cellForRowAt path: IndexPath) -> UITableViewCell {
        let row = self.sections[path.section].1[path.row]; let value = NagramiXTranscriptionSettings.current
        let cell = UITableViewCell(style:.value1, reuseIdentifier:nil)
        cell.backgroundColor = self.presentationData.theme.list.itemBlocksBackgroundColor
        cell.textLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize); cell.textLabel?.textColor = self.presentationData.theme.list.itemPrimaryTextColor; cell.textLabel?.numberOfLines = 0; cell.textLabel?.text = row.title
        cell.detailTextLabel?.text = row.subtitle; cell.detailTextLabel?.textColor = self.presentationData.theme.list.itemSecondaryTextColor
        cell.tintColor = self.presentationData.theme.list.itemAccentColor
        switch row.action {
        case .unavailable:
            cell.textLabel?.textColor = self.presentationData.theme.list.itemSecondaryTextColor; cell.selectionStyle = .none
        case .automatic, .localFallback, .cloudConsent:
            let toggle = UISwitch(); toggle.onTintColor = self.presentationData.theme.list.itemAccentColor
            if case .automatic = row.action { toggle.isOn = value.automatic; toggle.tag = 1 }
            else if case .localFallback = row.action { toggle.isOn = value.localFallback ?? false; toggle.tag = 3 }
            else { toggle.isOn = self.selectedConsent; toggle.tag = 2 }
            toggle.accessibilityLabel = row.title; toggle.addTarget(self, action:#selector(toggleChanged(_:)), for:.valueChanged); cell.accessoryView = toggle; cell.selectionStyle = .none
        case let .provider(provider): cell.accessoryType = value.provider == provider ? .checkmark : .none
        case let .language(code):
            let selected = value.language.replacingOccurrences(of:"_",with:"-").lowercased()
            let choice = code.replacingOccurrences(of:"_",with:"-").lowercased()
            let matches: Bool
            if case .whisperLanguages = self.page { matches = selected.split(separator:"-").first == choice.split(separator:"-").first }
            else { matches = selected == choice }
            cell.accessoryType = matches ? .checkmark : .none
        case let .appleLanguage(code): cell.accessoryType = value.language.replacingOccurrences(of:"_",with:"-").lowercased() == code.replacingOccurrences(of:"_",with:"-").lowercased() && self.appleHas(code) ? .checkmark : .disclosureIndicator
        case let .model(model): cell.accessoryType = value.whisper == model && NagramiXWhisperModels.shared.installed(model) ? .checkmark : .none
        case .key:
            cell.textLabel?.text = nil
            self.keyField.removeFromSuperview(); self.keyField.translatesAutoresizingMaskIntoConstraints = false; cell.contentView.addSubview(self.keyField)
            NSLayoutConstraint.activate([self.keyField.leadingAnchor.constraint(equalTo:cell.contentView.layoutMarginsGuide.leadingAnchor),self.keyField.trailingAnchor.constraint(equalTo:cell.contentView.layoutMarginsGuide.trailingAnchor),self.keyField.topAnchor.constraint(equalTo:cell.contentView.topAnchor,constant:15),self.keyField.bottomAnchor.constraint(equalTo:cell.contentView.bottomAnchor,constant:-15)])
        case .wheel:
            if case let .wheel(provider) = self.page {
                self.picker.dataSource = self; self.picker.delegate = self; self.picker.removeFromSuperview(); self.picker.translatesAutoresizingMaskIntoConstraints = false; cell.contentView.addSubview(self.picker)
                NSLayoutConstraint.activate([self.picker.leadingAnchor.constraint(equalTo:cell.contentView.leadingAnchor), self.picker.trailingAnchor.constraint(equalTo:cell.contentView.trailingAnchor), self.picker.topAnchor.constraint(equalTo:cell.contentView.topAnchor), self.picker.bottomAnchor.constraint(equalTo:cell.contentView.bottomAnchor), self.picker.heightAnchor.constraint(equalToConstant:200)])
                if let index = self.wheelChoices(provider).firstIndex(of:self.selectedModel) { self.picker.selectRow(index,inComponent:0,animated:false) }
            } else { cell.accessoryType = .disclosureIndicator }
        case .open, .website: cell.accessoryType = .disclosureIndicator
        case .license: cell.accessoryType = .disclosureIndicator
        }
        return cell
    }
    @objc private func toggleChanged(_ sender: UISwitch) {
        if sender.tag == 1 { NagramiXTranscriptionSettings.update { $0.automatic = sender.isOn } }
        else if sender.tag == 3 { NagramiXTranscriptionSettings.update { $0.localFallback = sender.isOn } }
        else { self.selectedConsent = sender.isOn }
    }
    @objc private func saveCredential() {
        guard case let .credential(provider) = self.page else { return }
        guard !self.selectedModel.isEmpty else { self.alert("Выберите доступную модель."); return }
        guard NagramiXTranscriptionKeys.save(self.keyField.text?.trimmingCharacters(in:.whitespacesAndNewlines),provider:provider) else { self.alert("Не удалось сохранить ключ."); return }
        NagramiXTranscriptionSettings.update { $0.models[provider.rawValue] = self.selectedModel; $0.cloudAllowed[provider.rawValue] = true }
        self.view.endEditing(true); self.navigationController?.popViewController(animated:true)
    }
    @objc private func finishWheel() { self.modelChosen?(self.selectedModel); self.navigationController?.popViewController(animated:true) }
    public func numberOfComponents(in pickerView: UIPickerView) -> Int { return 1 }
    public func pickerView(_ pickerView: UIPickerView, numberOfRowsInComponent component: Int) -> Int { if case let .wheel(p) = self.page { return self.wheelChoices(p).count }; return 0 }
    public func pickerView(_ pickerView: UIPickerView, titleForRow row: Int, forComponent component: Int) -> String? { if case let .wheel(p) = self.page { return self.wheelChoices(p)[row] }; return nil }
    public func pickerView(_ pickerView: UIPickerView, didSelectRow row: Int, inComponent component: Int) { if case let .wheel(p) = self.page { self.selectedModel = self.wheelChoices(p)[row] } }
    public func tableView(_ tableView: UITableView, didSelectRowAt path: IndexPath) {
        tableView.deselectRow(at:path,animated:true); guard path.section < self.sections.count && path.row < self.sections[path.section].1.count else { return }
        let action = self.sections[path.section].1[path.row].action
        switch action {
        case let .provider(provider): NagramiXTranscriptionSettings.update { $0.provider = provider; if provider.cloud { $0.cloudAllowed[provider.rawValue] = true }; if provider == .apple && $0.language == "auto" { $0.language = "ru-RU" } }
        case let .open(page,title): _ = self.show(page,title)
        case let .website(address): if let url = URL(string: address), url.scheme == "https" { UIApplication.shared.open(url) }
        case let .language(code): NagramiXTranscriptionSettings.update { $0.language = code.replacingOccurrences(of:"_",with:"-") }; if case .whisperLanguages = self.page { self.navigationController?.popViewController(animated:true) }
        case let .appleLanguage(code): self.selectApple(code)
        case let .model(model):
            if NagramiXWhisperModels.shared.isDownloading(model) { NagramiXWhisperModels.shared.downloadOrCancel(model) }
            else if NagramiXWhisperModels.shared.installed(model) { NagramiXTranscriptionSettings.update { $0.whisper = model; if model.englishOnly { $0.language = "en" } } }
            else { self.download(model) }
        case .wheel:
            if case let .credential(provider) = self.page {
                let child = self.show(.wheel(provider),"Выбор модели", selectedModel: self.selectedModel)
                child.modelChosen = { [weak self] value in self?.selectedModel = value; self?.refresh() }
            }
        case .license: if case .whisper = self.page { _ = self.show(.license,"Лицензия Whisper") }
        case .automatic, .localFallback, .cloudConsent, .key, .unavailable: break
        }
    }
    private func selectApple(_ code: String) {
        if self.appleHas(code) { NagramiXTranscriptionSettings.update { $0.language = code.replacingOccurrences(of:"_",with:"-") }; self.navigationController?.popViewController(animated:true); return }
        #if compiler(>=6.2)
        if #available(iOS 26.0, *) {
            guard self.appleLoading == nil else { return }; self.appleLoading = code; self.refresh()
            NagramiXTranscriptionAnalyzer.install(language:code) { [weak self] result in DispatchQueue.main.async { [weak self] in
                guard let self else { return }; self.appleLoading = nil
                switch result { case .success: NagramiXTranscriptionSettings.update { $0.language = code.replacingOccurrences(of:"_",with:"-") }; NotificationCenter.default.post(name: NagramiXTranscriptionSettings.changed, object: nil); self.navigationController?.popViewController(animated:true)
                case let .failure(error): self.alert(error.text); self.refresh() }
            } }; return
        }
        #endif
        // Legacy recognizer manages any assets itself; only supported on-device locales are listed.
        NagramiXTranscriptionSettings.update { $0.language = code.replacingOccurrences(of:"_",with:"-") }; self.navigationController?.popViewController(animated:true)
    }
    private func download(_ model: NagramiXWhisperModel) {
        let start = { NagramiXWhisperModels.shared.downloadOrCancel(model, activateWhenInstalled:true) }
        guard self.networkKnown else { self.alert("Проверяем подключение. Попробуйте ещё раз."); return }
        guard self.networkIsExpensive else { start(); return }
        let alert = UIAlertController(title:"Загрузка через мобильную сеть", message:"Модель занимает много места. Подключите Wi‑Fi в настройках iPhone или продолжите загрузку.",preferredStyle:.alert)
        alert.addAction(UIAlertAction(title:"Продолжить",style:.default,handler:{ _ in start() })); alert.addAction(UIAlertAction(title:"Отмена",style:.cancel))
        self.present(alert,animated:true)
    }
    public func tableView(_ tableView: UITableView, trailingSwipeActionsConfigurationForRowAt indexPath: IndexPath) -> UISwipeActionsConfiguration? {
        guard indexPath.section < self.sections.count, indexPath.row < self.sections[indexPath.section].1.count,
              case let .model(model) = self.sections[indexPath.section].1[indexPath.row].action,
              NagramiXWhisperModels.shared.installed(model) else { return nil }
        let remove = UIContextualAction(style:.destructive,title:"Удалить") { [weak self] _,_,completion in
            let success = NagramiXWhisperModels.shared.remove(model); completion(success)
            if !success { self?.alert("Модель используется или загружается. Попробуйте позже.") }
        }
        return UISwipeActionsConfiguration(actions:[remove])
    }
    private func refresh() {
        guard self.isNodeLoaded else { return }
        if case .credential = self.page {
            let initial = self.sections.isEmpty
            self.sections = self.makeSections()
            if initial { self.table.reloadData() }
            else if let cell = self.table.cellForRow(at: IndexPath(row:1,section:0)) { cell.detailTextLabel?.text = self.selectedModel }
            return
        }
        self.sections = self.makeSections(); self.table.reloadData()
    }
    private func alert(_ text: String) {
        let alert = UIAlertController(title:"Транскрибация",message:text,preferredStyle:.alert)
        alert.addAction(UIAlertAction(title:"OK",style:.default)); self.present(alert,animated:true)
    }
}
