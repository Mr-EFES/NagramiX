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

private func nagramiXFontLabelHeight(_ label: UILabel, width: CGFloat) -> CGFloat {
    return ceil(label.sizeThatFits(CGSize(width: max(1, width), height: .greatestFiniteMagnitude)).height)
}

private final class NagramiXFontPreviewCard: UIView {
    private let heading = UILabel()
    private let fontName = UILabel()
    private let bubble = UIView()
    private let message = UILabel()
    private let sample = UILabel()

    override init(frame: CGRect) {
        super.init(frame: frame)
        self.layer.cornerRadius = 22
        self.bubble.layer.cornerRadius = 16
        for label in [self.heading, self.fontName, self.message, self.sample] { label.numberOfLines = 0 }
        for view in [self.heading, self.fontName, self.bubble, self.sample] { self.addSubview(view) }
        self.bubble.addSubview(self.message)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    func configure(heading: String, entry: NagramiXFontEntry, presentation: PresentationData) {
        let base = presentation.listsFontSize.itemListBaseFontSize
        let theme = presentation.theme.list
        self.backgroundColor = theme.itemBlocksBackgroundColor
        self.heading.text = heading; self.heading.font = Font.semibold(base * 0.9)
        self.heading.textColor = theme.itemPrimaryTextColor
        self.fontName.text = nagramiXFontTitle(entry, strings: presentation.strings)
        self.fontName.font = Font.regular(base * 0.8); self.fontName.textColor = theme.itemSecondaryTextColor
        self.message.text = presentation.strings.nagramiXLocalized("NagramiX.Fonts.PreviewText")
        self.message.font = NagramiXFontManager.previewFont(entry, size: base * 1.15)
        self.message.textColor = theme.itemCheckColors.foregroundColor
        self.bubble.backgroundColor = theme.itemAccentColor
        self.sample.text = presentation.strings.nagramiXLocalized("NagramiX.Fonts.Sample") + NagramiXFontNumberSample
        self.sample.font = NagramiXFontManager.previewFont(entry, size: base * 0.8)
        self.sample.textColor = theme.itemSecondaryTextColor
        self.accessibilityElements = [self.heading, self.fontName, self.message, self.sample]
    }
    @discardableResult func arrange(width: CGFloat, height: CGFloat? = nil) -> CGFloat {
        let inset: CGFloat = 16
        let inner = max(1, width - inset * 2)
        var y: CGFloat = 14
        for label in [self.heading, self.fontName] {
            let h = nagramiXFontLabelHeight(label, width: inner)
            label.frame = CGRect(x: inset, y: y, width: inner, height: h); y += h + 4
        }
        y += 10
        let messageHeight = nagramiXFontLabelHeight(self.message, width: inner - 24)
        self.bubble.frame = CGRect(x: inset, y: y, width: inner, height: messageHeight + 20)
        self.message.frame = CGRect(x: 12, y: 10, width: max(1, inner - 24), height: messageHeight)
        y += messageHeight + 32
        let sampleHeight = nagramiXFontLabelHeight(self.sample, width: inner)
        self.sample.frame = CGRect(x: inset, y: y, width: inner, height: sampleHeight)
        return max(height ?? 0, y + sampleHeight + 14)
    }
}

private final class NagramiXFontApplyNode: ASDisplayNode {
    private let button: UIButton
    init(button: UIButton) {
        self.button = button
        super.init(viewBlock: { button }, didLoad: nil)
    }
    override func calculateSizeThatFits(_ constrainedSize: CGSize) -> CGSize { return self.button.bounds.size }
}

private final class NagramiXFontRowCell: UITableViewCell {
    private let specimen = UILabel()
    private let specimenSurface = UIView()
    private let name = UILabel()
    private let detail = UILabel()
    private let titles = UIStackView()
    private let row = UIStackView()
    private let selection = UIImageView()
    private var specimenWidth: NSLayoutConstraint!

    override init(style: UITableViewCell.CellStyle, reuseIdentifier: String?) {
        super.init(style: style, reuseIdentifier: reuseIdentifier)
        self.specimen.numberOfLines = 0; self.specimen.textAlignment = .center
        self.specimen.translatesAutoresizingMaskIntoConstraints = false
        self.specimenSurface.layer.cornerRadius = 12
        self.specimenSurface.addSubview(self.specimen)
        self.name.numberOfLines = 0; self.detail.numberOfLines = 0
        self.titles.axis = .vertical; self.titles.spacing = 3
        self.titles.addArrangedSubview(self.name); self.titles.addArrangedSubview(self.detail)
        self.row.axis = .horizontal; self.row.alignment = .center; self.row.spacing = 14
        self.row.addArrangedSubview(self.specimenSurface); self.row.addArrangedSubview(self.titles)
        self.row.translatesAutoresizingMaskIntoConstraints = false
        self.selection.translatesAutoresizingMaskIntoConstraints = false
        self.selection.contentMode = .scaleAspectFit
        self.contentView.addSubview(self.row); self.contentView.addSubview(self.selection)
        self.specimenWidth = self.specimenSurface.widthAnchor.constraint(equalToConstant: 78)
        NSLayoutConstraint.activate([
            self.specimenSurface.widthAnchor.constraint(lessThanOrEqualTo: self.row.widthAnchor),
            self.titles.widthAnchor.constraint(lessThanOrEqualTo: self.row.widthAnchor),
            self.specimen.leadingAnchor.constraint(equalTo: self.specimenSurface.leadingAnchor, constant: 12),
            self.specimen.trailingAnchor.constraint(equalTo: self.specimenSurface.trailingAnchor, constant: -12),
            self.specimen.topAnchor.constraint(equalTo: self.specimenSurface.topAnchor, constant: 10),
            self.specimen.bottomAnchor.constraint(equalTo: self.specimenSurface.bottomAnchor, constant: -10),
            self.row.leadingAnchor.constraint(equalTo: self.contentView.leadingAnchor, constant: 16),
            self.row.topAnchor.constraint(equalTo: self.contentView.topAnchor, constant: 12),
            self.row.bottomAnchor.constraint(equalTo: self.contentView.bottomAnchor, constant: -12),
            self.row.trailingAnchor.constraint(equalTo: self.selection.leadingAnchor, constant: -12),
            self.selection.trailingAnchor.constraint(equalTo: self.contentView.trailingAnchor, constant: -16),
            self.selection.centerYAnchor.constraint(equalTo: self.contentView.centerYAnchor),
            self.selection.widthAnchor.constraint(equalToConstant: 24), self.selection.heightAnchor.constraint(equalToConstant: 24),
            self.contentView.heightAnchor.constraint(greaterThanOrEqualToConstant: 72)
        ])
        self.isAccessibilityElement = true
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    func configure(_ entry: NagramiXFontEntry, presentation: PresentationData, selected: Bool, sample: String) {
        let base = presentation.listsFontSize.itemListBaseFontSize
        let theme = presentation.theme.list
        self.backgroundColor = theme.itemBlocksBackgroundColor
        self.name.text = nagramiXFontTitle(entry, strings: presentation.strings)
        self.name.font = Font.regular(base); self.name.textColor = theme.itemPrimaryTextColor
        self.specimen.text = sample
        self.specimen.font = NagramiXFontManager.previewFont(entry, size: base * 1.15)
        self.specimen.textColor = theme.itemPrimaryTextColor
        self.specimenSurface.backgroundColor = theme.itemSecondaryTextColor.withAlphaComponent(0.15)
        self.detail.font = Font.regular(base * 0.78); self.detail.textColor = theme.itemSecondaryTextColor
        if entry.kind == .system { self.detail.text = entry.name }
        else if NagramiXFontManager.missingCharacters(entry, sample: sample) { self.detail.text = presentation.strings.nagramiXLocalized("NagramiX.Fonts.Missing") }
        else { self.detail.text = nil }
        self.detail.isHidden = self.detail.text == nil
        self.selection.image = UIImage(systemName: selected ? "largecircle.fill.circle" : "circle")
        self.selection.tintColor = selected ? theme.itemAccentColor : theme.itemSecondaryTextColor
        let stacked = self.traitCollection.preferredContentSizeCategory.isAccessibilityCategory || base > 23
        self.row.axis = stacked ? .vertical : .horizontal; self.row.alignment = stacked ? .leading : .center
        self.specimenWidth.isActive = !stacked
        if !stacked { self.specimenWidth.constant = 78 }
        self.separatorInset = UIEdgeInsets(top: 0, left: 16, bottom: 0, right: 16)
        self.accessibilityLabel = [self.name.text, self.detail.text].compactMap { $0 }.joined(separator: ", ")
        self.accessibilityTraits = selected ? [.button, .selected] : [.button]
    }
}

/// A bounded comparison scroller keeps all text accessible on short/large-text
/// screens; ordinary portrait layouts show both complete cards without scrolling.
private func nagramiXFontComparisonViewport(content: CGFloat, available: CGFloat, fixed: CGFloat) -> CGFloat {
    return max(0, min(content, max(0, available - fixed - 72), available * 0.48))
}

public final class NagramiXFontsController: ViewController, UITableViewDataSource, UITableViewDelegate {
    private let context: AccountContext
    private var presentation: PresentationData
    private var draft = NagramiXFontSelectionDraft(NagramiXFontSettings.current)
    private let content = UIScrollView()
    private let table = UITableView(frame: .zero, style: .grouped)
    private let comparisonTitle = UILabel()
    private let listTitle = UILabel()
    private let comparison = UIScrollView()
    private let currentCard = NagramiXFontPreviewCard()
    private let previewCard = NagramiXFontPreviewCard()
    private let measuringCard = NagramiXFontPreviewCard()
    private let segment = UISegmentedControl(items: [])
    private let applyButton = UIButton(type: .system)
    private var applyNode: ASDisplayNode?
    private let licenseButton = UIButton(type: .system)
    private let licenseTitle = UILabel()
    private let licenseIcon = UIImageView(image: UIImage(systemName: "doc.text"))
    private let licenseArrow = UIImageView(image: UIImage(systemName: "chevron.right"))
    private let presentationDisposable = MetaDisposable()
    private var observer: NSObjectProtocol?
    private var entries: [NagramiXFontEntry] = []
    private var validLayout: ContainerViewLayout?

    public init(context: AccountContext) {
        self.context = context
        self.presentation = context.sharedContext.currentPresentationData.with { $0 }
        super.init(navigationBarPresentationData: NavigationBarPresentationData(presentationData: self.presentation))
        self.segment.insertSegment(withTitle: nil, at: 0, animated: false); self.segment.insertSegment(withTitle: nil, at: 1, animated: false)
        self.segment.selectedSegmentIndex = NagramiXFontEntry.entry(self.draft.fontId).kind == .ios ? 1 : 0
        self.segment.addTarget(self, action: #selector(segmentChanged), for: .valueChanged)
        self.content.contentInsetAdjustmentBehavior = .never
        self.table.dataSource = self; self.table.delegate = self
        self.table.register(NagramiXFontRowCell.self, forCellReuseIdentifier: "font")
        self.table.rowHeight = UITableView.automaticDimension; self.table.estimatedRowHeight = 82
        self.table.sectionHeaderHeight = 0; self.table.sectionFooterHeight = 0
        self.table.sectionHeaderTopPadding = 0
        self.table.contentInsetAdjustmentBehavior = .never
        self.table.layer.cornerRadius = 22; self.table.clipsToBounds = true
        self.comparison.addSubview(self.currentCard); self.comparison.addSubview(self.previewCard)
        self.comparison.contentInsetAdjustmentBehavior = .never
        self.comparisonTitle.numberOfLines = 0; self.listTitle.numberOfLines = 0
        self.applyButton.addTarget(self, action: #selector(applyTapped), for: .touchUpInside)
        self.applyButton.layer.cornerRadius = 20
        let applyNode = NagramiXFontApplyNode(button: self.applyButton)
        self.applyNode = applyNode
        self.navigationItem.rightBarButtonItem = UIBarButtonItem(customDisplayNode: applyNode)
        self.licenseButton.addTarget(self, action: #selector(openLicenses), for: .touchUpInside)
        self.licenseButton.layer.cornerRadius = 20
        self.licenseTitle.numberOfLines = 0
        self.licenseTitle.isUserInteractionEnabled = false
        self.licenseIcon.contentMode = .scaleAspectFit; self.licenseArrow.contentMode = .scaleAspectFit
        for view in [self.licenseTitle, self.licenseIcon, self.licenseArrow] { self.licenseButton.addSubview(view) }
        self.observer = NotificationCenter.default.addObserver(forName: NagramiXFontSettings.changed, object: nil, queue: .main) { [weak self] _ in
            guard let self else { return }
            self.draft.synchronize(NagramiXFontSettings.current)
            self.refresh()
        }
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
        for view in [self.comparisonTitle, self.comparison, self.segment, self.listTitle, self.table, self.licenseButton] { self.content.addSubview(view) }
        self.displayNode.view.addSubview(self.content)
        self.displayNodeDidLoad()
        self.refresh()
    }
    public override func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
        self.validLayout = layout
        self.arrange()
    }
    private func arrange() {
        guard let layout = self.validLayout else { return }
        let inset = max(20, layout.safeInsets.left + 16, layout.safeInsets.right + 16)
        let width = max(1, layout.size.width - inset * 2)
        let base = self.presentation.listsFontSize.itemListBaseFontSize
        let stacked = width < 280 || base > 23
        let cardWidth = stacked ? width : (width - 10) * 0.5
        let currentHeight = self.currentCard.arrange(width: cardWidth)
        let previewHeight = self.previewCard.arrange(width: cardWidth)
        // Reserve the same comparison height for every candidate, so changing
        // the preview never pushes the list or the license row up and down.
        var cardHeight = max(currentHeight, previewHeight)
        for entry in NagramiXFontEntry.catalog where NagramiXFontManager.available(entry) {
            for heading in ["NagramiX.Fonts.Current", "NagramiX.Fonts.Preview"] {
                self.measuringCard.configure(heading: self.presentation.strings.nagramiXLocalized(heading), entry: entry, presentation: self.presentation)
                cardHeight = max(cardHeight, self.measuringCard.arrange(width: cardWidth))
            }
        }
        self.currentCard.frame = CGRect(x: 0, y: 0, width: cardWidth, height: cardHeight)
        self.previewCard.frame = CGRect(x: stacked ? 0 : cardWidth + 10, y: stacked ? cardHeight + 10 : 0, width: cardWidth, height: cardHeight)
        let contentHeight = stacked ? cardHeight * 2 + 10 : cardHeight
        self.comparison.contentSize = CGSize(width: width, height: contentHeight)
        let headingHeight = nagramiXFontLabelHeight(self.comparisonTitle, width: width - 20)
        let listHeadingHeight = nagramiXFontLabelHeight(self.listTitle, width: width - 20)
        let segmentHeight = max(36, ceil(Font.medium(base).lineHeight) + 14)
        let licenseHeight = max(54, nagramiXFontLabelHeight(self.licenseTitle, width: width - 102) + 28)
        let top = self.navigationLayout(layout: layout).navigationFrame.maxY + 12
        let visibleHeight = max(0, layout.size.height - max(layout.intrinsicInsets.bottom, layout.safeInsets.bottom) - 12 - top)
        let fixed = headingHeight + listHeadingHeight + segmentHeight + licenseHeight + 70
        // Keep the normal page pinned. In very short windows / large text,
        // allow the entire content to scroll instead of hiding any control.
        let bottom = fixed + 72 > visibleHeight ? fixed + 72 + min(160, contentHeight) : visibleHeight
        self.content.frame = CGRect(x: 0, y: top, width: layout.size.width, height: visibleHeight)
        self.content.contentSize = CGSize(width: layout.size.width, height: bottom)
        self.content.isScrollEnabled = bottom > visibleHeight
        if !self.content.isScrollEnabled { self.content.contentOffset = .zero }
        var y: CGFloat = 0
        let viewport = nagramiXFontComparisonViewport(content: contentHeight, available: bottom, fixed: fixed)
        self.comparisonTitle.frame = CGRect(x: inset + 10, y: y, width: width - 20, height: headingHeight); y += headingHeight + 10
        self.comparison.frame = CGRect(x: inset, y: y, width: width, height: viewport); y += viewport + 18
        self.segment.frame = CGRect(x: inset, y: y, width: width, height: segmentHeight); y += segmentHeight + 18
        self.listTitle.frame = CGRect(x: inset + 10, y: y, width: width - 20, height: listHeadingHeight); y += listHeadingHeight + 10
        self.licenseButton.frame = CGRect(x: inset, y: bottom - licenseHeight, width: width, height: licenseHeight)
        self.licenseIcon.frame = CGRect(x: 20, y: (licenseHeight - 25) * 0.5, width: 24, height: 25)
        self.licenseTitle.frame = CGRect(x: 58, y: 14, width: max(1, width - 102), height: licenseHeight - 28)
        self.licenseArrow.frame = CGRect(x: width - 32, y: (licenseHeight - 18) * 0.5, width: 12, height: 18)
        self.table.frame = CGRect(x: inset, y: y, width: width, height: max(0, bottom - licenseHeight - 14 - y))
        self.table.contentInset = .zero; self.table.scrollIndicatorInsets = .zero
    }
    @objc private func segmentChanged() { self.refresh() }
    @objc private func openLicenses() { self.push(NagramiXFontLicensesController(context: self.context)) }
    @objc private func applyTapped() {
        guard self.draft.canApply, NagramiXFontManager.available(NagramiXFontEntry.entry(self.draft.fontId)) else { return }
        let proposed = self.draft.proposed
        NagramiXFontSettings.update { $0 = proposed }
        self.draft.synchronize(NagramiXFontSettings.current)
        self.refresh()
    }
    private func refresh() {
        self.statusBar.statusBarStyle = self.presentation.theme.rootController.statusBarStyle.style
        let strings = self.presentation.strings
        let theme = self.presentation.theme.list
        let base = self.presentation.listsFontSize.itemListBaseFontSize
        self.title = strings.nagramiXLocalized("NagramiX.Fonts.Title")
        self.comparisonTitle.text = strings.nagramiXLocalized("NagramiX.Fonts.Comparison").uppercased()
        self.listTitle.text = strings.nagramiXLocalized("NagramiX.Fonts.Choose").uppercased()
        for label in [self.comparisonTitle, self.listTitle] { label.font = Font.medium(base * 0.75); label.textColor = theme.itemSecondaryTextColor }
        self.currentCard.configure(heading: strings.nagramiXLocalized("NagramiX.Fonts.Current"), entry: NagramiXFontEntry.entry(self.draft.applied.enabled ? self.draft.applied.fontId : "system"), presentation: self.presentation)
        self.previewCard.configure(heading: strings.nagramiXLocalized("NagramiX.Fonts.Preview"), entry: NagramiXFontEntry.entry(self.draft.fontId), presentation: self.presentation)
        self.segment.setTitle(strings.nagramiXLocalized("NagramiX.Fonts.SystemTab"), forSegmentAt: 0)
        self.segment.setTitle(NagramiXFontPlatformName, forSegmentAt: 1)
        self.segment.setTitleTextAttributes([.font: Font.medium(base), .foregroundColor: theme.itemPrimaryTextColor], for: .normal)
        self.segment.setTitleTextAttributes([.font: Font.medium(base), .foregroundColor: theme.itemPrimaryTextColor], for: .selected)
        self.entries = NagramiXFontEntry.catalog.filter { NagramiXFontManager.available($0) && (self.segment.selectedSegmentIndex == 0 ? $0.kind != .ios : $0.kind == .ios) }
        self.table.backgroundColor = theme.itemBlocksBackgroundColor
        self.table.separatorColor = theme.itemBlocksSeparatorColor
        self.applyButton.setTitle(strings.Theme_Context_Apply, for: .normal)
        self.applyButton.titleLabel?.font = Font.semibold(17)
        self.applyButton.setTitleColor(theme.itemCheckColors.foregroundColor, for: .normal)
        self.applyButton.backgroundColor = theme.itemAccentColor
        self.applyButton.isEnabled = self.draft.canApply
        self.applyButton.alpha = self.draft.canApply ? 1 : 0.5
        self.applyButton.sizeToFit()
        self.applyButton.bounds.size = CGSize(width: self.applyButton.bounds.width + 28, height: max(40, ceil(Font.semibold(17).lineHeight) + 16))
        self.applyNode?.frame = self.applyButton.bounds
        if let applyNode = self.applyNode {
            applyNode.invalidateCalculatedLayout()
            let item = UIBarButtonItem(customDisplayNode: applyNode)
            item?.staysInRow = true
            self.navigationItem.rightBarButtonItem = item
        }
        self.applyButton.layer.cornerRadius = self.applyButton.bounds.height * 0.5
        self.licenseTitle.text = strings.nagramiXLocalized("NagramiX.Fonts.Licenses")
        self.licenseTitle.font = Font.regular(base); self.licenseTitle.textColor = theme.itemAccentColor
        self.licenseButton.backgroundColor = theme.itemBlocksBackgroundColor
        self.licenseButton.accessibilityLabel = self.licenseTitle.text
        self.licenseButton.isAccessibilityElement = true
        self.licenseIcon.tintColor = theme.itemAccentColor; self.licenseArrow.tintColor = theme.itemSecondaryTextColor
        for view in [self.table, self.comparison, self.segment, self.licenseButton] { view.overrideUserInterfaceStyle = self.presentation.theme.overallDarkAppearance ? .dark : .light }
        if self.isNodeLoaded { self.displayNode.backgroundColor = theme.blocksBackgroundColor }
        self.table.reloadData()
        self.arrange()
    }
    public func numberOfSections(in tableView: UITableView) -> Int { return 1 }
    public func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int { return self.entries.count }
    public func tableView(_ tableView: UITableView, heightForHeaderInSection section: Int) -> CGFloat { return .leastNormalMagnitude }
    public func tableView(_ tableView: UITableView, heightForFooterInSection section: Int) -> CGFloat { return .leastNormalMagnitude }
    public func tableView(_ tableView: UITableView, cellForRowAt path: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "font", for: path) as! NagramiXFontRowCell
        let entry = self.entries[path.row]
        cell.configure(entry, presentation: self.presentation, selected: self.draft.fontId == entry.id, sample: self.presentation.strings.nagramiXLocalized("NagramiX.Fonts.Sample"))
        return cell
    }
    public func tableView(_ tableView: UITableView, didSelectRowAt path: IndexPath) {
        tableView.deselectRow(at: path, animated: true)
        guard self.entries.indices.contains(path.row) else { return }
        let entry = self.entries[path.row]
        guard NagramiXFontManager.available(entry) else { return }
        self.draft.select(entry.id)
        self.refresh()
    }
}

private let NagramiXFontPlatformName = "iOS"
private let NagramiXFontNumberSample = " · 12345"

private final class NagramiXFontLicensesController: ViewController {
    private let text = UITextView()
    private var presentation: PresentationData
    private let presentationDisposable = MetaDisposable()
    init(context: AccountContext) {
        self.presentation = context.sharedContext.currentPresentationData.with { $0 }
        super.init(navigationBarPresentationData: NavigationBarPresentationData(presentationData: self.presentation))
        self.text.isEditable = false; self.text.isSelectable = true
        self.text.contentInsetAdjustmentBehavior = .never
        self.text.layer.cornerRadius = 24; self.text.clipsToBounds = true
        self.text.textContainerInset = UIEdgeInsets(top: 24, left: 20, bottom: 24, right: 20)
        self.presentationDisposable.set((context.sharedContext.presentationData |> deliverOnMainQueue).start(next: { [weak self] value in
            guard let self else { return }
            self.presentation = value
            self.navigationBar?.updatePresentationData(NavigationBarPresentationData(presentationData: value), transition: .immediate)
            self.refreshLicense()
        }))
        self.refreshLicense()
    }
    required init(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    deinit { self.presentationDisposable.dispose() }
    private func refreshLicense() {
        let presentation = self.presentation
        self.statusBar.statusBarStyle = presentation.theme.rootController.statusBarStyle.style
        self.title = presentation.strings.nagramiXLocalized("NagramiX.Fonts.Licenses")
        let base = max(16, presentation.listsFontSize.itemListBaseFontSize)
        let theme = presentation.theme.list
        let result = NSMutableAttributedString(string: "")
        for document in NagramiXFontManager.licenseDocuments {
            let heading = NSMutableParagraphStyle(); heading.paragraphSpacing = 18; heading.paragraphSpacingBefore = result.length == 0 ? 0 : 28
            result.append(NSAttributedString(string: document.name + "\n\n", attributes: [.font: Font.bold(base * 1.3), .foregroundColor: theme.itemPrimaryTextColor, .paragraphStyle: heading]))
            for paragraph in NagramiXFontLicenseLayout.paragraphs(document.text) {
                let style = NSMutableParagraphStyle(); style.lineSpacing = 4; style.paragraphSpacing = 14
                let isHeading = paragraph.count < 100 && paragraph == paragraph.uppercased()
                result.append(NSAttributedString(string: paragraph + "\n\n", attributes: [.font: isHeading ? Font.semibold(base) : Font.regular(base), .foregroundColor: theme.itemPrimaryTextColor, .paragraphStyle: style]))
            }
        }
        let offset = self.text.contentOffset
        self.text.attributedText = result
        self.text.contentOffset = offset
        self.text.backgroundColor = theme.itemBlocksBackgroundColor
        self.text.tintColor = theme.itemAccentColor
        self.text.overrideUserInterfaceStyle = presentation.theme.overallDarkAppearance ? .dark : .light
        if self.isNodeLoaded { self.displayNode.backgroundColor = theme.blocksBackgroundColor }
    }
    override func loadDisplayNode() {
        self.displayNode = ASDisplayNode()
        self.displayNode.view.addSubview(self.text); self.displayNodeDidLoad()
        self.refreshLicense()
    }
    override func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
        let inset = max(20, layout.safeInsets.left + 16, layout.safeInsets.right + 16)
        let top = self.navigationLayout(layout: layout).navigationFrame.maxY + 12
        self.text.frame = CGRect(x: inset, y: top, width: max(1, layout.size.width - inset * 2), height: max(0, layout.size.height - top - max(layout.intrinsicInsets.bottom, layout.safeInsets.bottom) - 12))
        self.text.contentInset = .zero; self.text.scrollIndicatorInsets = .zero
    }
}
