import NagramiXCore
import Foundation
import UIKit
import Speech
import Network
import Display
import AsyncDisplayKit
import AccountContext
import TelegramPresentationData
import ItemListUI
import TelegramCore
import SwiftSignalKit

public final class NagramiXTranscriptionSettingsController: ViewController, UITableViewDataSource, UITableViewDelegate, UIPickerViewDataSource, UIPickerViewDelegate {
    private enum Page { case settings, apple, appleLanguages, whisper, whisperLanguages, vosk, voskLanguages, credential(NagramiXTranscriptionProvider), wheel(NagramiXTranscriptionProvider), license, voskLicense }
    private struct Row { let title: String; let subtitle: String?; let action: Action }
    private enum Action { case temperature, automatic, localFallback, unavailable, provider(NagramiXTranscriptionProvider), open(Page, String), language(String), appleLanguage(String), model(NagramiXWhisperModel), key, account, voskModel(String), voskLanguage(String), wheel, cloudConsent, website(String), license }
    private let context: AccountContext
    private let presentationData: PresentationData
    private let table = UITableView(frame: .zero, style: .insetGrouped)
    private let keyField = UITextField()
    private let accountField = UITextField()
    private let picker = UIPickerView()
    private var page: Page = .settings
    private var observers: [NSObjectProtocol] = []
    private let premiumDisposable = MetaDisposable()
    private var isPremium = false
    private var appleSupported: [Locale] = []
    private var appleInstalled: Set<String> = []
    private var appleLoading: String?
    private var appleHasManagedDownloads = false
    private var selectedModel = ""
    private var catalogIdentity = ""
    private var catalogModels: [String]?
    private var catalogLoading = false
    private var catalogWantsPicker = false
    private var catalogGeneration = UUID()
    private var selectedTemperature: Double = 0.2
    private weak var temperatureLabel: UILabel?
    private var selectedConsent = false
    private var modelChosen: ((String) -> Void)?
    private var networkMonitor: NWPathMonitor?
    private let networkQueue = DispatchQueue(label: "NagramiXTranscription.Network")
    private var networkIsExpensive = false
    private var networkKnown = false
    private var sections: [(String?, [Row])] = []
    private func whisperModelTitle(_ model: NagramiXWhisperModel) -> String {
        switch model {
        case .base: return self.presentationData.strings.nagramiXUILocalized("Базовая") + " · " + model.title
        case .large_v3_turbo_q8_0: return self.presentationData.strings.nagramiXUILocalized("Максимальная") + " · " + model.title
        case .small_full: return self.presentationData.strings.nagramiXUILocalized("Средняя") + " · " + model.title
        case .medium: return (self.presentationData.strings.nagramiXUILocalized("Средняя"))
        case .large_v3: return (self.presentationData.strings.nagramiXUILocalized("Максимальная"))
        default: return self.presentationData.strings.nagramiXUILocalized(model.title)
        }
    }

    private static let whisperLanguages = "en zh de es ru ko fr ja pt tr pl ca nl ar sv it id hi fi vi he uk el ms cs ro da hu ta no th ur hr bg lt la mi ml cy sk te fa lv bn sr az sl kn et mk br eu is hy ne mn bs kk sq sw gl mr pa si km sn yo so af oc ka be tg sd gu am yi lo uz fo ht ps tk nn mt sa lb my bo tl mg as tt haw ln ha ba jw su yue".split(separator: " ").map(String.init)
    private func label(_ code: String) -> String {
        if code == "auto" { return self.presentationData.strings.nagramiXUILocalized("Автоопределение") }
        let locale = Locale(identifier: self.presentationData.strings.baseLanguageCode)
        return (locale.localizedString(forIdentifier: code == "cn" ? "zh" : code) ?? code).capitalized(with: locale)
    }
    private static func geminiSupportsTemperature(_ model: String) -> Bool {
        return ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro", "gemini-3.1-flash-lite"].contains(model)
    }
    public init(context: AccountContext) {
        self.context = context; self.presentationData = context.sharedContext.currentPresentationData.with { $0 }
        super.init(navigationBarPresentationData: NavigationBarPresentationData(presentationData: self.presentationData))
        self.title = self.presentationData.strings.nagramiXUILocalized("Расшифровка")
        self.premiumDisposable.set((context.engine.data.subscribe(TelegramEngine.EngineData.Item.Peer.Peer(id: context.account.peerId)) |> deliverOnMainQueue).start(next: { [weak self] peer in
            guard let self else { return }
            self.isPremium = peer?.isPremium ?? false
            if self.isNodeLoaded { self.refresh() }
        }))
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
        self.keyField.placeholder = self.presentationData.strings.nagramiXUILocalized("Введите ключ"); self.keyField.isSecureTextEntry = true
        self.keyField.textAlignment = .right; self.keyField.clearButtonMode = .whileEditing
        self.keyField.autocorrectionType = .no; self.keyField.autocapitalizationType = .none; self.keyField.spellCheckingType = .no
        for name in [NagramiXTranscriptionSettings.changed, NagramiXWhisperModels.changed, NagramiXVoskModels.changed] {
            self.observers.append(NotificationCenter.default.addObserver(forName: name, object: nil, queue: .main) { [weak self] _ in self?.settingsChanged() })
        }
    }
    public required init(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    deinit { self.premiumDisposable.dispose(); for observer in self.observers { NotificationCenter.default.removeObserver(observer) }; self.networkMonitor?.cancel() }
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
            if provider == .cloudflare {
                if let data = controller.keyField.text?.data(using: .utf8), let credential = try? JSONDecoder().decode(NagramiXCloudflareTranscriptionCredential.self, from: data) {
                    controller.keyField.text = credential.token
                    controller.accountField.text = credential.account
                } else { controller.keyField.text = nil }
                controller.accountField.font = controller.keyField.font
                controller.accountField.textColor = controller.keyField.textColor
                controller.accountField.placeholder = self.presentationData.strings.nagramiXUILocalized("Введите ID")
                controller.accountField.textAlignment = .right
                controller.keyField.placeholder = self.presentationData.strings.nagramiXUILocalized("Введите токен")
                controller.accountField.autocorrectionType = .no
                controller.accountField.autocapitalizationType = .none
                controller.accountField.spellCheckingType = .no
            }
            controller.selectedTemperature = NagramiXTranscriptionSettings.current.temperatures?[provider.rawValue] ?? 0.2
            controller.selectedModel = NagramiXTranscriptionSettings.current.models[provider.rawValue] ?? provider.defaultModel
            controller.selectedConsent = NagramiXTranscriptionSettings.current.cloudAllowed[provider.rawValue] == true
            controller.navigationItem.rightBarButtonItem = UIBarButtonItem(title: self.presentationData.strings.nagramiXUILocalized("Сохранить"), style: .done, target: controller, action: #selector(saveCredential))
        }
        if case .wheel = page {
            controller.selectedModel = selectedModel ?? ""
            controller.navigationItem.rightBarButtonItem = UIBarButtonItem(title: self.presentationData.strings.nagramiXUILocalized("Готово"), style: .done, target: controller, action: #selector(finishWheel))
        }
        if case .apple = page { controller.loadAppleLocales() }
        if case .appleLanguages = page { controller.loadAppleLocales() }
        if case .whisper = page { controller.monitorNetwork() }
        if case .vosk = page { controller.monitorNetwork() }
        self.push(controller)
        if case let .credential(provider) = page { controller.loadCatalog(provider, openPicker: false) }
        return controller
    }
    private func loadCatalog(_ provider: NagramiXTranscriptionProvider, openPicker: Bool) {
        let key = (self.keyField.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        let account = (self.accountField.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        let identity = provider.rawValue + "|" + account + "|" + key
        if identity == self.catalogIdentity, let models = self.catalogModels {
            if openPicker { self.presentCatalog(models) }
            return
        }
        if identity == self.catalogIdentity && self.catalogLoading { self.catalogWantsPicker = self.catalogWantsPicker || openPicker; return }
        self.catalogIdentity = identity; self.catalogModels = nil; self.catalogWantsPicker = openPicker
        let generation = UUID(); self.catalogGeneration = generation
        if key.isEmpty && !openPicker { self.catalogLoading = false; return }
        self.catalogLoading = true
        if self.isNodeLoaded { self.table.cellForRow(at: IndexPath(row: provider == .cloudflare ? 2 : 1, section: 0))?.detailTextLabel?.text = self.presentationData.strings.nagramiXUILocalized("Загрузка…") }
        NagramiXRemoteModelCatalog.fetch(provider: provider.rawValue, speech: true, key: key, account: account) { [weak self] result in
            DispatchQueue.main.async { [weak self] in
                guard let self, self.catalogGeneration == generation else { return }
                let currentKey = (self.keyField.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
                let currentAccount = (self.accountField.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
                guard identity == provider.rawValue + "|" + currentAccount + "|" + currentKey else { self.catalogLoading = false; self.catalogModels = nil; return }
                self.catalogLoading = false
                let show = self.catalogWantsPicker; self.catalogWantsPicker = false
                if self.isNodeLoaded { self.table.cellForRow(at: IndexPath(row: provider == .cloudflare ? 2 : 1, section: 0))?.detailTextLabel?.text = self.selectedModel }
                switch result {
                case let .success(models): self.catalogModels = models; if show { self.presentCatalog(models) }
                case let .failure(error): self.catalogModels = nil; if show { self.alert(NagramiXRemoteModelCatalog.message(error)) }
                }
            }
        }
    }
    private func presentCatalog(_ models: [String]) {
        guard self.view.window != nil, !models.isEmpty else { return }
        let picker = NagramiXTranscriptionModelPicker(models: models, selected: self.selectedModel, presentationData: self.presentationData) { [weak self] model in
            guard let self else { return }; self.selectedModel = model; self.sections = self.makeSections(); self.table.reloadData()
        }
        self.present(picker, animated: true)
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
            var local: [Row] = []; for provider in [NagramiXTranscriptionProvider.apple, .whisper, .vosk] {
                local.append(Row(title: provider.title, subtitle: nil, action: .provider(provider)))
                if value.provider == provider && provider != .apple { local.append(Row(title: self.presentationData.strings.nagramiXUILocalized("Настройки ") + provider.title, subtitle: nil, action: .open(provider == .apple ? .apple : (provider == .vosk ? .vosk : .whisper), self.presentationData.strings.nagramiXUILocalized("Настройки ") + provider.title))) }
            }
            var cloud: [Row] = []; let providers: [NagramiXTranscriptionProvider] = [.gemini, .chatgpt, .grok, .cloudflare]
            for provider in providers {
                cloud.append(Row(title: provider.title, subtitle: nil, action: .provider(provider)))
                if value.provider == provider { cloud.append(Row(title: self.presentationData.strings.nagramiXUILocalized("Настройки ") + provider.title, subtitle: nil, action: .open(.credential(provider), provider.title))) }
            }
            return [(nil,[Row(title: self.presentationData.strings.nagramiXUILocalized("Авторасшифровка"), subtitle:nil,action:.automatic), Row(title:self.presentationData.strings.nagramiXUILocalized("Резервный способ"),subtitle:nil,action:.localFallback)])] + (self.isPremium ? [("TELEGRAM",[Row(title:"Telegram Premium",subtitle:nil,action:.provider(.telegram))])] : []) + [(self.presentationData.strings.nagramiXUILocalized("НА УСТРОЙСТВЕ"),local), (self.presentationData.strings.nagramiXUILocalized("ЧЕРЕЗ ИНТЕРНЕТ"),cloud)]
        case .apple:
            let installed = self.appleSupported.filter { self.appleHas($0.identifier) }.map { Row(title: self.label($0.identifier), subtitle:self.appleHasManagedDownloads ? self.presentationData.strings.nagramiXUILocalized("Загружен") : self.presentationData.strings.nagramiXUILocalized("Доступен на устройстве"),action:.language($0.identifier)) }
            return [(self.presentationData.strings.nagramiXUILocalized("ЯЗЫК РЕЧИ"),[Row(title:self.presentationData.strings.nagramiXUILocalized("Автоопределение"),subtitle:self.presentationData.strings.nagramiXUILocalized("Не поддерживается Apple"),action:.unavailable),Row(title:self.label(value.language),subtitle:nil,action:.open(.appleLanguages,self.presentationData.strings.nagramiXUILocalized("Языки Apple")))]),(self.presentationData.strings.nagramiXUILocalized("ЯЗЫКИ APPLE"),installed + [Row(title:self.presentationData.strings.nagramiXUILocalized("Выбрать и загрузить язык"),subtitle:nil,action:.open(.appleLanguages,self.presentationData.strings.nagramiXUILocalized("Языки Apple")))])]
        case .appleLanguages:
            let ordered = self.appleSupported.sorted { self.label($0.identifier).localizedCaseInsensitiveCompare(self.label($1.identifier)) == .orderedAscending }
            return [(self.presentationData.strings.nagramiXUILocalized("ДОСТУПНЫЕ ЯЗЫКИ"),ordered.map { Row(title:self.label($0.identifier),subtitle:self.appleLoading == $0.identifier ? self.presentationData.strings.nagramiXUILocalized("Загрузка…") : (self.appleHas($0.identifier) ? (self.appleHasManagedDownloads ? self.presentationData.strings.nagramiXUILocalized("Загружен") : self.presentationData.strings.nagramiXUILocalized("Доступен на устройстве")) : self.presentationData.strings.nagramiXUILocalized("Загрузить")),action:.appleLanguage($0.identifier)) })]
        case .whisper:
            return [(self.presentationData.strings.nagramiXUILocalized("ЯЗЫК РЕЧИ"),[Row(title:self.label(value.whisperLanguage ?? value.language),subtitle:nil,action:.open(.whisperLanguages,self.presentationData.strings.nagramiXUILocalized("Язык речи")))]),(self.presentationData.strings.nagramiXUILocalized("МОДЕЛИ"),NagramiXLocalInferenceMemory.whisperModels.map { Row(title:self.whisperModelTitle($0),subtitle:NagramiXWhisperModels.shared.status($0),action:.model($0)) }), (nil,[Row(title:self.presentationData.strings.nagramiXUILocalized("Лицензия Whisper"),subtitle:nil,action:.license)])]
        case .vosk:
            let code = NagramiXTranscriptionVosk.model(value)?.lang ?? "ru"
            let models = NagramiXLocalInferenceMemory.voskModels(language: code)
            return [(self.presentationData.strings.nagramiXUILocalized("ЯЗЫК РЕЧИ"),[Row(title:self.label(code),subtitle:nil,action:.open(.voskLanguages,self.presentationData.strings.nagramiXUILocalized("Язык речи")))]),(self.presentationData.strings.nagramiXUILocalized("ЯЗЫКОВЫЕ МОДЕЛИ"),models.map { Row(title:$0.name == "vosk-model-ru-0.10-lgraph" ? self.presentationData.strings.nagramiXLocalized("NagramiX.Transcription.Vosk.Alternative") : $0.title,subtitle:NagramiXVoskModels.shared.status($0),action:.voskModel($0.name)) }), (nil,[Row(title:self.presentationData.strings.nagramiXUILocalized("Лицензия Vosk · Apache 2.0"),subtitle:nil,action:.open(.voskLicense,self.presentationData.strings.nagramiXUILocalized("Лицензия Vosk")))])]
        case .voskLanguages:
            let codes = NagramiXLocalInferenceMemory.voskLanguages.sorted { self.label($0).localizedCaseInsensitiveCompare(self.label($1)) == .orderedAscending }
            return [(self.presentationData.strings.nagramiXUILocalized("ЯЗЫК РЕЧИ"),codes.map { Row(title:self.label($0),subtitle:nil,action:.voskLanguage($0)) })]
        case .whisperLanguages:
            let names = (value.whisper.englishOnly ? ["en"] : Self.whisperLanguages).sorted { self.label($0).localizedCaseInsensitiveCompare(self.label($1)) == .orderedAscending }
            return [(nil, (value.whisper.englishOnly ? [] : [Row(title:self.presentationData.strings.nagramiXUILocalized("Автоопределение"),subtitle:nil,action:.language("auto"))]) + names.map { Row(title:self.label($0),subtitle:nil,action:.language($0)) })]
        case let .credential(provider):
            if provider == .cloudflare {
                return [(self.presentationData.strings.nagramiXUILocalized("ДОСТУП И МОДЕЛЬ"),[Row(title:self.presentationData.strings.nagramiXUILocalized("API-токен"),subtitle:nil,action:.key),Row(title:self.presentationData.strings.nagramiXUILocalized("Account ID"),subtitle:nil,action:.account),Row(title:self.presentationData.strings.nagramiXUILocalized("Модель"),subtitle:self.selectedModel,action:.wheel),Row(title:self.presentationData.strings.nagramiXUILocalized("Получить данные CloudFlare"),subtitle:nil,action:.website("https://dash.cloudflare.com/?to=/:account/ai/workers-ai"))])]
            }
            let url: String
            switch provider {
            case .gemini: url = "https://aistudio.google.com/apikey"
            case .chatgpt: url = "https://platform.openai.com/api-keys"
            case .grok: url = "https://console.x.ai/"
            default: url = ""
            }
            let linkTitle = provider == .gemini ? self.presentationData.strings.nagramiXUILocalized("Получить ключ в Google AI Studio") : (provider == .chatgpt ? self.presentationData.strings.nagramiXUILocalized("Получить ключ OpenAI") : self.presentationData.strings.nagramiXUILocalized("Получить ключ xAI"))
            let access = (self.presentationData.strings.nagramiXUILocalized("ДОСТУП И МОДЕЛЬ") as String?, [Row(title:self.presentationData.strings.nagramiXUILocalized("API-ключ"),subtitle:nil,action:.key),Row(title:self.presentationData.strings.nagramiXUILocalized("Модель"),subtitle:self.selectedModel,action:.wheel),Row(title:linkTitle,subtitle:nil,action:.website(url))])
            if provider == .gemini && Self.geminiSupportsTemperature(self.selectedModel) { return [access, (self.presentationData.strings.nagramiXUILocalized("ТЕМПЕРАТУРА"), [Row(title:self.presentationData.strings.nagramiXUILocalized("Температура"),subtitle:nil,action:.temperature)])] }
            return [access]
        case .wheel: return [(nil,[Row(title:"",subtitle:nil,action:.wheel)])]
        case .license: return [(nil,[Row(title:NagramiXWhisperLicense.text,subtitle:nil,action:.license)])]
        case .voskLicense: return [(nil,[Row(title:NagramiXVoskLicense.text,subtitle:nil,action:.license)])]
        }
    }
    public func numberOfSections(in tableView: UITableView) -> Int { return self.sections.count }
    public func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int { return self.sections[section].1.count }
    public func tableView(_ tableView: UITableView, titleForHeaderInSection section: Int) -> String? { return self.sections[section].0 }
    public func tableView(_ tableView: UITableView, titleForFooterInSection section: Int) -> String? {
        switch self.page {
        case .apple: return section == 0 ? self.presentationData.strings.nagramiXUILocalized("Для Apple выберите язык речи из доступных на устройстве.") : nil
        case .whisper:
            guard section == 1 else { return nil }
            return self.presentationData.strings.nagramiXUILocalized("Модель") + ": " + NagramiXTranscriptionSettings.current.whisper.title
        case .vosk:
            guard section == 1, let model = NagramiXTranscriptionVosk.model(NagramiXTranscriptionSettings.current) else { return nil }
            return self.presentationData.strings.nagramiXUILocalized("Модель") + ": " + model.name
        case .credential: return nil
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
        cell.textLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize); cell.textLabel?.textColor = self.presentationData.theme.list.itemPrimaryTextColor; cell.textLabel?.numberOfLines = 0; cell.textLabel?.text = self.presentationData.strings.nagramiXUILocalized(row.title)
        cell.detailTextLabel?.text = row.subtitle.map { self.presentationData.strings.nagramiXUILocalized($0) }; cell.detailTextLabel?.textColor = self.presentationData.theme.list.itemSecondaryTextColor
        cell.detailTextLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)
        cell.detailTextLabel?.numberOfLines = 0
        cell.tintColor = self.presentationData.theme.list.itemAccentColor
        switch row.action {
        case .temperature:
            cell.textLabel?.text = nil
            let label = UILabel(); label.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize); label.textColor = self.presentationData.theme.list.itemPrimaryTextColor
            label.text = self.presentationData.strings.nagramiXUILocalized("Температура: \(Int((self.selectedTemperature * 100).rounded()))%"); self.temperatureLabel = label
            let slider = UISlider(); slider.minimumValue = 0; slider.maximumValue = 1; slider.value = Float(self.selectedTemperature); slider.tintColor = self.presentationData.theme.list.itemAccentColor
            slider.accessibilityLabel = self.presentationData.strings.nagramiXUILocalized("Температура"); slider.addTarget(self, action: #selector(temperatureChanged(_:)), for: .valueChanged)
            let stack = UIStackView(arrangedSubviews: [label, slider]); stack.axis = .vertical; stack.spacing = 8; stack.translatesAutoresizingMaskIntoConstraints = false; cell.contentView.addSubview(stack)
            NSLayoutConstraint.activate([stack.leadingAnchor.constraint(equalTo:cell.contentView.layoutMarginsGuide.leadingAnchor),stack.trailingAnchor.constraint(equalTo:cell.contentView.layoutMarginsGuide.trailingAnchor),stack.topAnchor.constraint(equalTo:cell.contentView.topAnchor,constant:15),stack.bottomAnchor.constraint(equalTo:cell.contentView.bottomAnchor,constant:-15)])
            cell.selectionStyle = .none
        case .unavailable:
            cell.textLabel?.textColor = self.presentationData.theme.list.itemSecondaryTextColor; cell.selectionStyle = .none
        case .automatic, .localFallback, .cloudConsent:
            let toggle = UISwitch(); toggle.onTintColor = self.presentationData.theme.list.itemAccentColor
            if case .automatic = row.action { toggle.isOn = value.automatic; toggle.tag = 1 }
            else if case .localFallback = row.action { toggle.isOn = value.localFallback ?? false; toggle.tag = 3 }
            else { toggle.isOn = self.selectedConsent; toggle.tag = 2 }
            toggle.accessibilityLabel = self.presentationData.strings.nagramiXUILocalized(row.title); toggle.addTarget(self, action:#selector(toggleChanged(_:)), for:.valueChanged); cell.accessoryView = toggle; cell.selectionStyle = .none
        case let .provider(provider): cell.accessoryType = value.provider == provider ? .checkmark : .none
        case let .language(code):
            let selectedLanguage: String
            if case .whisperLanguages = self.page { selectedLanguage = value.whisperLanguage ?? value.language } else { selectedLanguage = value.language }
            let selected = selectedLanguage.replacingOccurrences(of:"_",with:"-").lowercased()
            let choice = code.replacingOccurrences(of:"_",with:"-").lowercased()
            let matches: Bool
            if case .whisperLanguages = self.page { matches = selected.split(separator:"-").first == choice.split(separator:"-").first }
            else { matches = selected == choice }
            cell.accessoryType = matches ? .checkmark : .none
        case let .appleLanguage(code): cell.accessoryType = value.language.replacingOccurrences(of:"_",with:"-").lowercased() == code.replacingOccurrences(of:"_",with:"-").lowercased() && self.appleHas(code) ? .checkmark : .disclosureIndicator
        case let .model(model): cell.accessoryType = value.whisper == model && NagramiXWhisperModels.shared.installed(model) ? .checkmark : .none
        case let .voskModel(id):
            if let model = NagramiXVoskModel.all.first(where: { $0.name == id }) { cell.accessoryType = NagramiXTranscriptionVosk.model(value)?.name == id && NagramiXVoskModels.shared.installed(model) ? .checkmark : .none }
        case let .voskLanguage(code): cell.accessoryType = NagramiXTranscriptionVosk.model(value)?.lang == code ? .checkmark : .none
        case .account:
            cell.textLabel?.text = nil
            self.accountField.removeFromSuperview(); self.accountField.translatesAutoresizingMaskIntoConstraints = false; cell.contentView.addSubview(self.accountField)
            NSLayoutConstraint.activate([self.accountField.leadingAnchor.constraint(equalTo:cell.contentView.layoutMarginsGuide.leadingAnchor),self.accountField.trailingAnchor.constraint(equalTo:cell.contentView.layoutMarginsGuide.trailingAnchor),self.accountField.topAnchor.constraint(equalTo:cell.contentView.topAnchor,constant:15),self.accountField.bottomAnchor.constraint(equalTo:cell.contentView.bottomAnchor,constant:-15)])
        case .key:
            cell.textLabel?.text = nil
            self.keyField.removeFromSuperview()
            let label = UILabel(); if case .credential(.cloudflare) = self.page { label.text = self.presentationData.strings.nagramiXUILocalized("API-токен") } else { label.text = self.presentationData.strings.nagramiXUILocalized("API-ключ") }; label.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
            label.textColor = self.presentationData.theme.list.itemPrimaryTextColor
            label.setContentHuggingPriority(.required, for: .horizontal)
            self.keyField.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
            let stack = UIStackView(arrangedSubviews: [label, self.keyField]); stack.axis = .horizontal; stack.alignment = .center; stack.spacing = 12
            stack.translatesAutoresizingMaskIntoConstraints = false; cell.contentView.addSubview(stack)
            NSLayoutConstraint.activate([stack.leadingAnchor.constraint(equalTo:cell.contentView.layoutMarginsGuide.leadingAnchor),stack.trailingAnchor.constraint(equalTo:cell.contentView.layoutMarginsGuide.trailingAnchor),stack.topAnchor.constraint(equalTo:cell.contentView.topAnchor,constant:15),stack.bottomAnchor.constraint(equalTo:cell.contentView.bottomAnchor,constant:-15)])
        case .wheel:
            if case .wheel = self.page {
                self.picker.dataSource = self; self.picker.delegate = self; self.picker.removeFromSuperview(); self.picker.translatesAutoresizingMaskIntoConstraints = false; cell.contentView.addSubview(self.picker)
                NSLayoutConstraint.activate([self.picker.leadingAnchor.constraint(equalTo:cell.contentView.leadingAnchor), self.picker.trailingAnchor.constraint(equalTo:cell.contentView.trailingAnchor), self.picker.topAnchor.constraint(equalTo:cell.contentView.topAnchor), self.picker.bottomAnchor.constraint(equalTo:cell.contentView.bottomAnchor), self.picker.heightAnchor.constraint(equalToConstant:200)])
                if let index = (self.catalogModels ?? []).firstIndex(of:self.selectedModel) { self.picker.selectRow(index,inComponent:0,animated:false) }
            } else { cell.accessoryType = .disclosureIndicator }
        case .open:
            cell.accessoryType = .disclosureIndicator
        case .website:
            cell.textLabel?.textColor = self.presentationData.theme.list.itemAccentColor
            cell.accessoryType = .disclosureIndicator
        case .license:
            if case .whisper = self.page { cell.accessoryType = .disclosureIndicator }
            else { cell.textLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize); cell.selectionStyle = .none }
        }
        return cell
    }
    @objc private func temperatureChanged(_ sender: UISlider) {
        sender.value = (sender.value * 10).rounded() / 10
        self.selectedTemperature = Double(sender.value)
        self.temperatureLabel?.text = self.presentationData.strings.nagramiXUILocalized("Температура: \(Int((self.selectedTemperature * 100).rounded()))%")
    }
    @objc private func toggleChanged(_ sender: UISwitch) {
        if sender.tag == 1 { NagramiXTranscriptionSettings.update { $0.automatic = sender.isOn } }
        else if sender.tag == 3 { NagramiXTranscriptionSettings.update { $0.localFallback = sender.isOn } }
        else { self.selectedConsent = sender.isOn }
    }
    @objc private func saveCredential() {
        guard case let .credential(provider) = self.page else { return }
        guard !self.selectedModel.isEmpty else { self.alert(self.presentationData.strings.nagramiXUILocalized("Выберите доступную модель.")); return }
        let token = (self.keyField.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        let stored: String
        if provider == .cloudflare && !token.isEmpty {
            let credential = NagramiXCloudflareTranscriptionCredential(token: token, account: (self.accountField.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines))
            guard credential.valid, let data = try? JSONEncoder().encode(credential), let value = String(data: data, encoding: .utf8) else { self.alert(self.presentationData.strings.nagramiXUILocalized("Введите API-токен и Account ID из кабинета CloudFlare.")); return }
            stored = value
        } else { stored = token }
        var saved = false
        NagramiXTranscriptionSettings.update { value in
            guard NagramiXTranscriptionKeys.save(stored,provider:provider,notify:false) else { return }
            value.models[provider.rawValue] = self.selectedModel
            if provider == .gemini { var values = value.temperatures ?? [:]; values[provider.rawValue] = self.selectedTemperature; value.temperatures = values }
            value.cloudAllowed[provider.rawValue] = true
            value.credentialRevision = UUID().uuidString
            saved = true
        }
        guard saved else { self.alert(self.presentationData.strings.nagramiXUILocalized("Не удалось сохранить ключ.")); return }
        self.view.endEditing(true); self.navigationController?.popViewController(animated:true)
    }
    @objc private func finishWheel() { self.modelChosen?(self.selectedModel); self.navigationController?.popViewController(animated:true) }
    public func numberOfComponents(in pickerView: UIPickerView) -> Int { return 1 }
    public func pickerView(_ pickerView: UIPickerView, numberOfRowsInComponent component: Int) -> Int { if case .wheel = self.page { return (self.catalogModels ?? []).count }; return 0 }
    public func pickerView(_ pickerView: UIPickerView, titleForRow row: Int, forComponent component: Int) -> String? { if case .wheel = self.page { return (self.catalogModels ?? [])[row] }; return nil }
    public func pickerView(_ pickerView: UIPickerView, didSelectRow row: Int, inComponent component: Int) { if case .wheel = self.page { self.selectedModel = (self.catalogModels ?? [])[row] } }
    public func tableView(_ tableView: UITableView, didSelectRowAt path: IndexPath) {
        tableView.deselectRow(at:path,animated:true); guard path.section < self.sections.count && path.row < self.sections[path.section].1.count else { return }
        let action = self.sections[path.section].1[path.row].action
        switch action {
        case let .provider(provider):
            if provider == .telegram && !self.isPremium { return }
            NagramiXTranscriptionSettings.update { $0.provider = provider; if provider.cloud { $0.cloudAllowed[provider.rawValue] = true }; if provider == .apple && $0.language == "auto" { $0.language = Locale.current.identifier.replacingOccurrences(of: "_", with: "-") } }
            if provider == .apple && SFSpeechRecognizer.authorizationStatus() == .notDetermined {
                #if compiler(>=6.2)
                if #available(iOS 26.0, *), SpeechTranscriber.isAvailable { return }
                #endif
                SFSpeechRecognizer.requestAuthorization { _ in }
            }
        case let .open(page,title): _ = self.show(page,title)
        case let .website(address): if let url = URL(string: address), url.scheme == "https" { UIApplication.shared.open(url) }
        case let .voskLanguage(code):
            NagramiXTranscriptionSettings.update { $0.language = code; $0.voskModelID = NagramiXVoskModel.all.first(where: { $0.lang == code && $0.type == "small" })?.name ?? NagramiXVoskModel.all.first(where: { $0.lang == code })?.name }
            self.navigationController?.popViewController(animated:true)
        case let .voskModel(id):
            guard let model = NagramiXVoskModel.all.first(where: { $0.name == id }) else { return }
            if NagramiXVoskModels.shared.isDownloading(model) { NagramiXVoskModels.shared.cancel(model); return }
            if NagramiXVoskModels.shared.installed(model) { NagramiXTranscriptionSettings.update { $0.voskModelID = id; $0.language = model.lang }; return }
            let revision = NagramiXTranscriptionSettings.current.revision
            let start = { [weak self] in
                NagramiXVoskModels.shared.download(model) { result in
                    switch result {
                    case .success:
                        if NagramiXTranscriptionSettings.current.revision == revision { NagramiXTranscriptionSettings.update { $0.voskModelID = id; $0.language = model.lang } }
                    case let .failure(error): if error != .cancelled { self?.alert(error.text) }
                    }
                }
            }
            guard self.networkKnown else { self.alert(self.presentationData.strings.nagramiXUILocalized("Проверяем подключение. Попробуйте ещё раз.")); return }
            if self.networkIsExpensive {
                let alert = UIAlertController(title:self.presentationData.strings.nagramiXUILocalized("Загрузка модели"),message:self.presentationData.strings.nagramiXUILocalized("Модель занимает много места. Можно подключить Wi‑Fi или продолжить через текущую сеть."),preferredStyle:.alert)
                alert.addAction(UIAlertAction(title:self.presentationData.strings.nagramiXUILocalized("Продолжить"),style:.default,handler:{ _ in start() })); alert.addAction(UIAlertAction(title:self.presentationData.strings.nagramiXUILocalized("Отмена"),style:.cancel)); self.present(alert,animated:true)
            } else { start() }
        case let .language(code):
            if case .whisperLanguages = self.page { NagramiXTranscriptionSettings.update { $0.whisperLanguage = code.replacingOccurrences(of:"_",with:"-") }; self.navigationController?.popViewController(animated:true) }
            else { NagramiXTranscriptionSettings.update { $0.language = code.replacingOccurrences(of:"_",with:"-") } }
        case let .appleLanguage(code): self.selectApple(code)
        case let .model(model):
            if NagramiXWhisperModels.shared.isDownloading(model) { NagramiXWhisperModels.shared.downloadOrCancel(model) }
            else if NagramiXWhisperModels.shared.installed(model) { NagramiXTranscriptionSettings.update { $0.whisper = model; if model.englishOnly { $0.language = "en" } } }
            else { self.download(model) }
        case .wheel:
            if case let .credential(provider) = self.page { self.view.endEditing(true); self.loadCatalog(provider, openPicker: true) }
        case .license: if case .whisper = self.page { _ = self.show(.license,self.presentationData.strings.nagramiXUILocalized("Лицензия Whisper")) }
        case .temperature, .automatic, .localFallback, .cloudConsent, .key, .account, .unavailable: break
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
        guard self.networkKnown else { self.alert(self.presentationData.strings.nagramiXUILocalized("Проверяем подключение. Попробуйте ещё раз.")); return }
        guard self.networkIsExpensive else { start(); return }
        let alert = UIAlertController(title:self.presentationData.strings.nagramiXUILocalized("Загрузка через мобильную сеть"), message:self.presentationData.strings.nagramiXUILocalized("Модель занимает много места. Подключите Wi‑Fi в настройках iPhone или продолжите загрузку."),preferredStyle:.alert)
        alert.addAction(UIAlertAction(title:self.presentationData.strings.nagramiXUILocalized("Продолжить"),style:.default,handler:{ _ in start() })); alert.addAction(UIAlertAction(title:self.presentationData.strings.nagramiXUILocalized("Отмена"),style:.cancel))
        self.present(alert,animated:true)
    }
    public func tableView(_ tableView: UITableView, trailingSwipeActionsConfigurationForRowAt indexPath: IndexPath) -> UISwipeActionsConfiguration? {
        if indexPath.section < self.sections.count, indexPath.row < self.sections[indexPath.section].1.count,
           case let .voskModel(id) = self.sections[indexPath.section].1[indexPath.row].action,
           let model = NagramiXVoskModel.all.first(where: { $0.name == id }) {
            let remove = UIContextualAction(style:.destructive,title:self.presentationData.strings.nagramiXUILocalized("Удалить")) { [weak self] _,_,finish in
                let removed = NagramiXVoskModels.shared.remove(model)
                if !removed { NagramiXVoskModels.shared.cancel(model); if let self { self.alert(self.presentationData.strings.nagramiXUILocalized("Модель используется или загружается. Повторите удаление после завершения.")) } }
                finish(removed)
            }
            return UISwipeActionsConfiguration(actions:[remove])
        }
        guard indexPath.section < self.sections.count, indexPath.row < self.sections[indexPath.section].1.count,
              case let .model(model) = self.sections[indexPath.section].1[indexPath.row].action,
              NagramiXWhisperModels.shared.installed(model) else { return nil }
        let remove = UIContextualAction(style:.destructive,title:self.presentationData.strings.nagramiXUILocalized("Удалить")) { [weak self] _,_,completion in
            let success = NagramiXWhisperModels.shared.remove(model); completion(success)
            if !success, let self { self.alert(self.presentationData.strings.nagramiXUILocalized("Модель используется или загружается. Попробуйте позже.")) }
        }
        return UISwipeActionsConfiguration(actions:[remove])
    }
    private func refresh() {
        guard self.isNodeLoaded else { return }
        if case let .credential(provider) = self.page {
            let initial = self.sections.isEmpty
            self.sections = self.makeSections()
            if initial { self.table.reloadData() }
            else if let cell = self.table.cellForRow(at: IndexPath(row:provider == .cloudflare ? 2 : 1,section:0)) { cell.detailTextLabel?.text = self.catalogLoading ? self.presentationData.strings.nagramiXUILocalized("Загрузка…") : self.selectedModel }
            return
        }
        self.sections = self.makeSections(); self.table.reloadData()
    }
    private func alert(_ text: String) {
        let alert = UIAlertController(title:self.presentationData.strings.nagramiXUILocalized("Транскрибация"),message:self.presentationData.strings.nagramiXUILocalized(text),preferredStyle:.alert)
        alert.addAction(UIAlertAction(title:self.presentationData.strings.Common_OK,style:.default)); self.present(alert,animated:true)
    }
}
