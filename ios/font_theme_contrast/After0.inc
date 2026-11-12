import Foundation
import UIKit
import Display
import AsyncDisplayKit
import SwiftSignalKit
import AccountContext
import TelegramPresentationData
import NagramiXCore
import NagramiXMediaSettings

func nagramiXFontTitle(_ entry: NagramiXFontEntry, strings: PresentationStrings) -> String {
    if let key = entry.titleKey { return strings.nagramiXLocalized(key) }
    return entry.name
}

private final class NagramiXFontRowCell: UITableViewCell {
    let specimen = UILabel()
    let name = UILabel()
    let detail = UILabel()
    private let titles = UIStackView()
    private let row = UIStackView()
    private let tick = UIImageView(image: UIImage(systemName: "checkmark"))
    private var specimenWidth: NSLayoutConstraint!

    override init(style: UITableViewCell.CellStyle, reuseIdentifier: String?) {
        super.init(style: style, reuseIdentifier: reuseIdentifier)
        self.specimen.numberOfLines = 1
        self.specimen.textAlignment = .center
        self.specimen.setContentCompressionResistancePriority(.required, for: .horizontal)
        self.name.numberOfLines = 0
        self.detail.numberOfLines = 0
        self.titles.axis = .vertical; self.titles.spacing = 3
        self.titles.addArrangedSubview(self.name); self.titles.addArrangedSubview(self.detail)
        self.row.axis = .horizontal; self.row.alignment = .center; self.row.spacing = 16
        self.row.addArrangedSubview(self.specimen); self.row.addArrangedSubview(self.titles)
        self.row.translatesAutoresizingMaskIntoConstraints = false
        self.tick.translatesAutoresizingMaskIntoConstraints = false
        self.tick.contentMode = .scaleAspectFit
        self.contentView.addSubview(self.row); self.contentView.addSubview(self.tick)
        self.specimenWidth = self.specimen.widthAnchor.constraint(equalToConstant: 74)
        NSLayoutConstraint.activate([
            self.row.leadingAnchor.constraint(equalTo: self.contentView.leadingAnchor, constant: 20),
            self.row.topAnchor.constraint(equalTo: self.contentView.topAnchor, constant: 14),
            self.row.bottomAnchor.constraint(equalTo: self.contentView.bottomAnchor, constant: -14),
            self.row.trailingAnchor.constraint(equalTo: self.tick.leadingAnchor, constant: -12),
            self.tick.trailingAnchor.constraint(equalTo: self.contentView.trailingAnchor, constant: -20),
            self.tick.centerYAnchor.constraint(equalTo: self.contentView.centerYAnchor),
            self.tick.widthAnchor.constraint(equalToConstant: 20), self.tick.heightAnchor.constraint(equalToConstant: 20),
            self.contentView.heightAnchor.constraint(greaterThanOrEqualToConstant: 64)
        ])
        self.isAccessibilityElement = true
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    func configure(_ entry: NagramiXFontEntry, presentation: PresentationData, selected: Bool, sample: String) {
        let base = presentation.listsFontSize.itemListBaseFontSize
        self.backgroundColor = presentation.theme.list.itemBlocksBackgroundColor
        self.name.text = nagramiXFontTitle(entry, strings: presentation.strings)
        self.name.font = Font.regular(base); self.name.textColor = presentation.theme.list.itemPrimaryTextColor
        self.specimen.text = sample
        self.specimen.font = NagramiXFontManager.previewFont(entry, size: base * 1.3)
        self.specimen.textColor = presentation.theme.list.itemPrimaryTextColor
        self.detail.font = Font.regular(base * 0.78); self.detail.textColor = presentation.theme.list.itemSecondaryTextColor
        if entry.kind == .system { self.detail.text = entry.name }
        else if NagramiXFontManager.missingCharacters(entry, sample: sample) { self.detail.text = presentation.strings.nagramiXLocalized("NagramiX.Fonts.Missing") }
        else { self.detail.text = nil }
        self.detail.isHidden = self.detail.text == nil
        self.tick.tintColor = presentation.theme.list.itemAccentColor; self.tick.alpha = selected ? 1 : 0
        let stacked = self.traitCollection.preferredContentSizeCategory.isAccessibilityCategory || base > 23 || self.specimen.intrinsicContentSize.width > 110
        self.row.axis = stacked ? .vertical : .horizontal; self.row.alignment = stacked ? .leading : .center
        self.specimenWidth.isActive = !stacked
        if !stacked { self.specimenWidth.constant = max(74, ceil(self.specimen.intrinsicContentSize.width) + 8) }
        self.separatorInset = UIEdgeInsets(top: 0, left: stacked ? 20 : self.specimenWidth.constant + 36, bottom: 0, right: 20)
        self.accessibilityLabel = [self.name.text, self.detail.text].compactMap { $0 }.joined(separator: ", ")
        self.accessibilityTraits = selected ? [.button, .selected] : [.button]
    }
}

public final class NagramiXFontsController: ViewController, UITableViewDataSource, UITableViewDelegate {
    private let context: AccountContext
    private var presentation: PresentationData
    private let table = UITableView(frame: .zero, style: .insetGrouped)
    private let segment = UISegmentedControl(items: [])
    private let header = UIView()
    private let footer = UIView()
    private let licenseButton = UIButton(type: .system)
    private let presentationDisposable = MetaDisposable()
    private var observer: NSObjectProtocol?
    private var groups: [[NagramiXFontEntry]] = []

    public init(context: AccountContext) {
        self.context = context
        self.presentation = context.sharedContext.currentPresentationData.with { $0 }
        super.init(navigationBarPresentationData: NavigationBarPresentationData(presentationData: self.presentation))
        let selected = NagramiXFontEntry.entry(NagramiXFontSettings.current.fontId)
        self.segment.insertSegment(withTitle: nil, at: 0, animated: false); self.segment.insertSegment(withTitle: nil, at: 1, animated: false)
        self.segment.selectedSegmentIndex = selected.kind == .ios ? 1 : 0
        self.segment.addTarget(self, action: #selector(segmentChanged), for: .valueChanged)
        self.header.addSubview(self.segment); self.table.tableHeaderView = self.header
        self.table.dataSource = self; self.table.delegate = self
        self.table.register(NagramiXFontRowCell.self, forCellReuseIdentifier: "font")
        self.table.rowHeight = UITableView.automaticDimension; self.table.estimatedRowHeight = 76
        self.table.contentInsetAdjustmentBehavior = .never
        self.licenseButton.addTarget(self, action: #selector(openLicenses), for: .touchUpInside)
        self.licenseButton.titleLabel?.numberOfLines = 0
        self.licenseButton.titleLabel?.textAlignment = .center
        self.footer.addSubview(self.licenseButton)
        self.table.tableFooterView = self.footer
        self.observer = NotificationCenter.default.addObserver(forName: NagramiXFontSettings.changed, object: nil, queue: .main) { [weak self] _ in self?.refresh() }
        self.presentationDisposable.set((context.sharedContext.presentationData |> deliverOnMainQueue).start(next: { [weak self] value in
            guard let self else { return }
            self.presentation = value
            self.navigationBar?.updatePresentationData(NavigationBarPresentationData(presentationData: value), transition: .immediate)
            self.refresh()
        }))
        self.refresh()
    }
    public required init(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    deinit { self.presentationDisposable.dispose(); if let observer { NotificationCenter.default.removeObserver(observer) } }

    public override func loadDisplayNode() {
        self.displayNode = ASDisplayNode()
        self.displayNode.view.addSubview(self.table)
        self.displayNodeDidLoad()
        self.refresh()
    }
    public override func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
        self.table.frame = CGRect(origin: .zero, size: layout.size)
        self.table.contentInset.top = self.navigationLayout(layout: layout).navigationFrame.maxY
        self.table.contentInset.bottom = layout.intrinsicInsets.bottom
        self.table.scrollIndicatorInsets = self.table.contentInset
        self.updateAccessories()
    }
    private func updateAccessories() {
        let width = self.table.bounds.width
        guard width > 0 else { return }
        let font = Font.medium(self.presentation.listsFontSize.itemListBaseFontSize)
        self.segment.setTitleTextAttributes([.font: font], for: .normal)
        self.segment.setTitleTextAttributes([.font: font], for: .selected)
        let segmentHeight = max(36, ceil(font.lineHeight) + 16)
        self.header.frame = CGRect(x: 0, y: 0, width: width, height: segmentHeight + 24)
        self.segment.frame = CGRect(x: 20, y: 12, width: max(0, width - 40), height: segmentHeight)
        self.table.tableHeaderView = self.header
        let textHeight = self.licenseButton.titleLabel?.sizeThatFits(CGSize(width: max(1, width - 40), height: CGFloat.greatestFiniteMagnitude)).height ?? 0
        let footerHeight = max(54, ceil(textHeight) + 24)
        self.footer.frame = CGRect(x: 0, y: 0, width: width, height: footerHeight)
        self.licenseButton.frame = CGRect(x: 20, y: 0, width: max(0, width - 40), height: footerHeight)
        self.table.tableFooterView = self.footer
    }
    @objc private func segmentChanged() { self.refresh() }
    @objc private func openLicenses() { self.push(NagramiXFontLicensesController(context: self.context)) }

    private func refresh() {
        self.statusBar.statusBarStyle = self.presentation.theme.rootController.statusBarStyle.style
        let strings = self.presentation.strings
        self.title = strings.nagramiXLocalized("NagramiX.Fonts.Title")
        self.segment.setTitle(strings.nagramiXLocalized("NagramiX.Fonts.SystemTab"), forSegmentAt: 0)
        self.segment.setTitle(NagramiXFontPlatformName, forSegmentAt: 1)
        let entries = NagramiXFontEntry.catalog.filter { NagramiXFontManager.available($0) }
        self.groups = self.segment.selectedSegmentIndex == 0 ? [entries.filter { $0.kind == .system }, entries.filter { $0.kind == .bundled }] : [entries.filter { $0.kind == .ios }]
        self.groups.removeAll(where: { $0.isEmpty })
        self.table.backgroundColor = self.presentation.theme.list.blocksBackgroundColor
        self.table.separatorColor = self.presentation.theme.list.itemBlocksSeparatorColor
        self.table.overrideUserInterfaceStyle = self.presentation.theme.overallDarkAppearance ? .dark : .light
        self.licenseButton.setTitle(strings.nagramiXLocalized("NagramiX.Fonts.Licenses"), for: .normal)
        self.licenseButton.titleLabel?.font = Font.regular(self.presentation.listsFontSize.itemListBaseFontSize)
        self.licenseButton.tintColor = self.presentation.theme.list.itemAccentColor
        if self.isNodeLoaded { self.displayNode.backgroundColor = self.presentation.theme.list.blocksBackgroundColor }
        self.table.reloadData()
        self.updateAccessories()
    }
    public func numberOfSections(in tableView: UITableView) -> Int { return 1 + self.groups.count }
    public func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int { return section == 0 ? 1 : self.groups[section - 1].count }
    public func tableView(_ tableView: UITableView, titleForHeaderInSection section: Int) -> String? {
        if section == 0 { return self.presentation.strings.nagramiXLocalized("NagramiX.Fonts.Preview") }
        guard let entry = self.groups[section - 1].first else { return nil }
        switch entry.kind {
        case .system: return self.presentation.strings.nagramiXLocalized("NagramiX.Fonts.SystemTab")
        case .bundled: return self.presentation.strings.nagramiXLocalized("NagramiX.Fonts.Bundled")
        case .ios: return NagramiXFontPlatformName
        }
    }
    public func tableView(_ tableView: UITableView, cellForRowAt path: IndexPath) -> UITableViewCell {
        let strings = self.presentation.strings
        let selected = NagramiXFontEntry.entry(NagramiXFontSettings.current.fontId)
        let sample = strings.nagramiXLocalized("NagramiX.Fonts.Sample")
        if path.section != 0 {
            let cell = tableView.dequeueReusableCell(withIdentifier: "font", for: path) as! NagramiXFontRowCell
            let entry = self.groups[path.section - 1][path.row]
            cell.configure(entry, presentation: self.presentation, selected: selected.id == entry.id, sample: sample)
            return cell
        }
        let cell = UITableViewCell(style: .default, reuseIdentifier: nil)
        cell.backgroundColor = self.presentation.theme.list.itemBlocksBackgroundColor; cell.selectionStyle = .none
        let message = UILabel(); message.numberOfLines = 0
        message.text = strings.nagramiXLocalized("NagramiX.Fonts.PreviewText")
        message.font = NagramiXFontManager.previewFont(selected, size: self.presentation.listsFontSize.itemListBaseFontSize * 1.2)
        message.textColor = self.presentation.theme.list.itemPrimaryTextColor
        let example = UILabel(); example.numberOfLines = 0
        example.text = sample + NagramiXFontLatinSample
        example.font = NagramiXFontManager.previewFont(selected, size: self.presentation.listsFontSize.itemListBaseFontSize * 0.85)
        example.textColor = self.presentation.theme.list.itemSecondaryTextColor
        let bubble = UIView(); bubble.layer.cornerRadius = 16
        bubble.backgroundColor = self.presentation.theme.list.itemAccentColor.withAlphaComponent(0.15)
        message.translatesAutoresizingMaskIntoConstraints = false; bubble.addSubview(message)
        NSLayoutConstraint.activate([message.leadingAnchor.constraint(equalTo: bubble.leadingAnchor, constant: 12), message.trailingAnchor.constraint(equalTo: bubble.trailingAnchor, constant: -12), message.topAnchor.constraint(equalTo: bubble.topAnchor, constant: 10), message.bottomAnchor.constraint(equalTo: bubble.bottomAnchor, constant: -10)])
        let stack = UIStackView(arrangedSubviews: [bubble, example]); stack.axis = .vertical; stack.alignment = .leading; stack.spacing = 12; stack.translatesAutoresizingMaskIntoConstraints = false
        bubble.widthAnchor.constraint(lessThanOrEqualTo: stack.widthAnchor).isActive = true
        example.widthAnchor.constraint(lessThanOrEqualTo: stack.widthAnchor).isActive = true
        cell.contentView.addSubview(stack)
        NSLayoutConstraint.activate([stack.leadingAnchor.constraint(equalTo: cell.contentView.leadingAnchor, constant: 20), stack.trailingAnchor.constraint(equalTo: cell.contentView.trailingAnchor, constant: -20), stack.topAnchor.constraint(equalTo: cell.contentView.topAnchor, constant: 18), stack.bottomAnchor.constraint(equalTo: cell.contentView.bottomAnchor, constant: -18)])
        return cell
    }
    public func tableView(_ tableView: UITableView, didSelectRowAt path: IndexPath) {
        tableView.deselectRow(at: path, animated: true)
        guard path.section > 0 else { return }
        let entry = self.groups[path.section - 1][path.row]
        guard NagramiXFontManager.available(entry) else { return }
        NagramiXFontSettings.update { $0.enabled = true; $0.fontId = entry.id }
    }
}

private let NagramiXFontPlatformName = "iOS"
private let NagramiXFontLatinSample = " · Aa Bb · 0123456789"

private final class NagramiXFontLicensesController: ViewController {
    private let text = UITextView()
    init(context: AccountContext) {
        let presentation = context.sharedContext.currentPresentationData.with { $0 }
        super.init(navigationBarPresentationData: NavigationBarPresentationData(presentationData: presentation))
        self.statusBar.statusBarStyle = presentation.theme.rootController.statusBarStyle.style
        self.title = presentation.strings.nagramiXLocalized("NagramiX.Fonts.Licenses")
        self.text.text = NagramiXFontManager.licenseText
        self.text.isEditable = false; self.text.isSelectable = true
        self.text.font = Font.monospace(max(14, presentation.listsFontSize.itemListBaseFontSize * 0.85))
        self.text.backgroundColor = presentation.theme.list.blocksBackgroundColor
        self.text.textColor = presentation.theme.list.itemPrimaryTextColor
        self.text.textContainerInset = UIEdgeInsets(top: 20, left: 20, bottom: 20, right: 20)
    }
    required init(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    override func loadDisplayNode() {
        self.displayNode = ASDisplayNode()
        self.displayNode.view.addSubview(self.text); self.displayNodeDidLoad()
    }
    override func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
        self.text.frame = CGRect(origin: .zero, size: layout.size)
        self.text.contentInset.top = self.navigationLayout(layout: layout).navigationFrame.maxY
        self.text.contentInset.bottom = layout.intrinsicInsets.bottom
        self.text.scrollIndicatorInsets = self.text.contentInset
    }
}
