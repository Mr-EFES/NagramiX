import Foundation
import UIKit
import AsyncDisplayKit
import Display
import TelegramPresentationData
import NagramiXCore
import MediaEditor

struct NagramiXRoundQualityRow: Equatable {
    let title: String
    let value: String
    let checked: Bool
}

func nagramiXRoundQualityRows(values: MediaEditorValues, strings: PresentationStrings) -> [NagramiXRoundQualityRow] {
    guard let tuning = values.nagramiXRoundTuning, tuning.count == 4 else {
        return [NagramiXRoundQualityRow(title: strings.UserInfo_NotificationsDefault + " Telegram", value: strings.nagramiXLocalized("NagramiX.RoundVideo.QualitySummary.DefaultInfo"), checked: true)]
    }
    let locale = Locale(identifier: strings.primaryComponent.languageCode)
    func label(_ source: String) -> String {
        let text = strings.nagramiXUILocalized(source).lowercased(with: locale)
        return text.prefix(1).uppercased(with: locale) + text.dropFirst()
    }
    let preset: String
    switch tuning[0] {
    case 512: preset = strings.nagramiXUILocalized("Высокое")
    case 640: preset = strings.nagramiXUILocalized("Максимум")
    default: preset = strings.nagramiXUILocalized("Стандарт")
    }
    let formatter = NumberFormatter()
    formatter.locale = locale
    formatter.numberStyle = .decimal
    formatter.minimumFractionDigits = 1
    formatter.maximumFractionDigits = 1
    formatter.usesGroupingSeparator = false
    let number = formatter.string(from: NSNumber(value: Double(tuning[3]) / 1_000_000.0)) ?? String(Double(tuning[3]) / 1_000_000.0)
    let rate = String(format: strings.nagramiXLocalized("NagramiX.RoundVideo.QualitySummary.Rate"), locale: locale, arguments: [number])
    return [
        NagramiXRoundQualityRow(title: strings.nagramiXLocalized("NagramiX.RoundVideo.QualitySummary.Preset"), value: preset, checked: false),
        NagramiXRoundQualityRow(title: strings.nagramiXLocalized("NagramiX.RoundVideo.QualitySummary.Resolution"), value: "\(tuning[0]) × \(tuning[0])", checked: false),
        NagramiXRoundQualityRow(title: strings.nagramiXUILocalized("Битрейт"), value: rate, checked: false),
        NagramiXRoundQualityRow(title: label("КОДЕК"), value: tuning[2] == 0 ? "H.264 / AVC" : "H.265 / HEVC", checked: false),
        NagramiXRoundQualityRow(title: label("ЧАСТОТА КАДРОВ"), value: strings.nagramiXUILocalized("\(tuning[1]) кадров/с"), checked: false)
    ]
}

func nagramiXRoundQualitySheet(presentationData: PresentationData, values: MediaEditorValues, updated: @escaping ([Int]) -> Void) -> ActionSheetController {
    let sheet = ActionSheetController(presentationData: presentationData)
    let selection = NagramiXRoundQualitySelection(presentationData: presentationData, values: values, updated: updated)
    selection.sheet = sheet
    sheet.dismissed = { _ in selection.finished = true }
    selection.showRoot()
    return sheet
}

// This selection belongs only to one gallery attachment. It never writes camera defaults.
private final class NagramiXRoundQualitySelection {
    weak var sheet: ActionSheetController?
    let presentationData: PresentationData
    let values: MediaEditorValues
    let updated: ([Int]) -> Void
    var tuning: [Int]
    var finished = false

    init(presentationData: PresentationData, values: MediaEditorValues, updated: @escaping ([Int]) -> Void) {
        self.presentationData = presentationData
        self.values = values
        self.updated = updated
        self.tuning = chatMediaEditorRoundVideoTuning(values.nagramiXRoundTuning)
    }

    private func title(_ text: String) -> String { self.presentationData.strings.nagramiXUILocalized(text) }
    private func bitRateTitle(_ index: Int) -> String {
        self.presentationData.strings.nagramiXLocalized("NagramiX.RoundVideo.Bitrate." + ["Standard", "Medium", "High", "Maximum"][index])
    }
    private func header(title: String? = nil, back: (() -> Void)? = nil) -> NagramiXRoundQualitySheetItem {
        return NagramiXRoundQualitySheetItem(
            title: title ?? self.presentationData.strings.nagramiXLocalized("NagramiX.RoundVideo.QualitySummary.Title"),
            kind: .header,
            closeTitle: self.presentationData.strings.nagramiXOptionSheetClose,
            close: { [weak self] in self?.close() },
            backTitle: self.presentationData.strings.Common_Back,
            back: back
        )
    }

    private func show(_ items: [ActionSheetItem]) {
        guard let sheet = self.sheet else { return }
        sheet.setItemGroups([ActionSheetItemGroup(items: items)])
        // Replacing the group creates rows with no frames until the sheet lays out again.
        sheet.requestLayout(transition: .immediate)
    }

    func close() {
        guard !self.finished else { return }
        self.finished = true
        self.sheet?.dismissAnimated()
    }
    func apply() {
        guard !self.finished else { return }
        self.finished = true
        self.updated(self.tuning)
        self.sheet?.dismissAnimated()
    }
    func showRoot() {
        guard !self.finished else { return }
        let rows = nagramiXRoundQualityRows(values: self.values.withUpdatedNagramiXRoundTuning(self.tuning), strings: self.presentationData.strings)
        var items: [ActionSheetItem] = [self.header()]
        let fields = [0, 3, 2, 1]
        let titles = [rows[1].title, rows[2].title, rows[3].title, rows[4].title]
        let labels = [rows[0].value + "\n" + rows[1].value, self.bitRateTitle((self.tuning[3] - 1_000_000) / 100_000), rows[3].value, rows[4].value]
        for index in fields.indices {
            items.append(NagramiXRoundQualitySheetItem(title: titles[index], value: labels[index], kind: .parameter, action: { [weak self] in self?.showOptions(field: fields[index]) }))
        }
        items.append(NagramiXRoundQualitySheetItem(title: self.presentationData.strings.Appearance_TextSize_Apply, kind: .apply, action: { [weak self] in self?.apply() }))
        self.show(items)
    }
    func showOptions(field: Int) {
        guard !self.finished, [0, 1, 2, 3].contains(field) else { return }
        let choices: [Int]
        switch field {
        case 0: choices = [480, 512, 640]
        case 1: choices = [30, 60]
        case 2: choices = [0, 1]
        default: choices = [1_000_000, 1_100_000, 1_200_000, 1_300_000]
        }
        let rows = nagramiXRoundQualityRows(values: self.values.withUpdatedNagramiXRoundTuning(self.tuning), strings: self.presentationData.strings)
        let optionTitles = [rows[1].title, rows[4].title, rows[3].title, rows[2].title]
        var items: [ActionSheetItem] = [self.header(title: optionTitles[field], back: { [weak self] in self?.showRoot() })]
        for (index, value) in choices.enumerated() {
            let text: String
            let detail: String
            switch field {
            case 0:
                text = self.title(["Стандарт", "Высокое", "Максимум"][index])
                detail = "\(value) × \(value)"
            case 1: text = self.title("\(value) кадров/с"); detail = ""
            case 2: text = value == 0 ? "H.264 / AVC" : "H.265 / HEVC"; detail = ""
            default: text = self.bitRateTitle(index); detail = ""
            }
            items.append(NagramiXRoundQualitySheetItem(title: text, value: detail, kind: .option, selected: self.tuning[field] == value, action: { [weak self] in
                guard let self, !self.finished else { return }
                self.tuning[field] = value
                self.showRoot()
            }))
        }
        self.show(items)
    }
}

private final class NagramiXRoundQualitySheetItem: ActionSheetItem {
    enum Kind {
        case header
        case parameter
        case option
        case apply
    }

    let title: String
    let value: String
    let kind: Kind
    let selected: Bool
    let closeTitle: String
    let close: (() -> Void)?
    let backTitle: String
    let back: (() -> Void)?
    let action: (() -> Void)?

    init(title: String, value: String = "", kind: Kind, selected: Bool = false,
         closeTitle: String = "", close: (() -> Void)? = nil,
         backTitle: String = "", back: (() -> Void)? = nil, action: (() -> Void)? = nil) {
        self.title = title
        self.value = value
        self.kind = kind
        self.selected = selected
        self.closeTitle = closeTitle
        self.close = close
        self.backTitle = backTitle
        self.back = back
        self.action = action
    }

    func node(theme: ActionSheetControllerTheme) -> ActionSheetItemNode {
        let node = NagramiXRoundQualitySheetNode(theme: theme)
        node.setItem(self)
        return node
    }

    func updateNode(_ node: ActionSheetItemNode) {
        guard let node = node as? NagramiXRoundQualitySheetNode else { return }
        node.setItem(self)
        node.requestLayoutUpdate()
    }
}

private final class NagramiXRoundQualitySheetNode: ActionSheetItemNode, NagramiXGlassActionSheetItem {
    var nagramiXUsesFloatingGlass: Bool { true }
    private let sheetTheme: ActionSheetControllerTheme
    private var item: NagramiXRoundQualitySheetItem?
    private let rowHighlightView = UIView()
    private let rowButton = HighlightTrackingButton()
    private let backButton = UIButton(type: .system)
    private let closeButton = UIButton(type: .system)
    private let titleLabel = UILabel()
    private let valueLabel = UILabel()
    private let chevronView = UIImageView()
    private let radioView = UIView()
    private let radioDotView = UIView()
    private let separatorView = UIView()

    override init(theme: ActionSheetControllerTheme) {
        self.sheetTheme = theme
        super.init(theme: theme)
        self.backgroundNode.backgroundColor = .clear
        self.hasSeparator = false

        self.rowHighlightView.layer.cornerRadius = 10
        for label in [self.titleLabel, self.valueLabel] {
            label.numberOfLines = 0
        }
        self.chevronView.image = UIImage(systemName: "chevron.right")?.imageFlippedForRightToLeftLayoutDirection()
        self.chevronView.tintColor = theme.secondaryTextColor
        self.chevronView.contentMode = .scaleAspectFit
        self.radioView.layer.cornerRadius = 9
        self.radioDotView.frame = CGRect(x: 6, y: 6, width: 6, height: 6)
        self.radioDotView.layer.cornerRadius = 3
        self.radioDotView.backgroundColor = .white
        self.radioView.addSubview(self.radioDotView)
        self.separatorView.backgroundColor = theme.controlColor.withAlphaComponent(0.25)
        for view in [self.rowHighlightView, self.titleLabel, self.valueLabel, self.chevronView, self.radioView, self.separatorView] as [UIView] {
            view.isAccessibilityElement = false
            view.isUserInteractionEnabled = false
            self.view.addSubview(view)
        }

        self.rowButton.addTarget(self, action: #selector(self.rowPressed), for: .touchUpInside)
        self.rowButton.highligthedChanged = { [weak self] highlighted in
            self?.updateRowHighlight(highlighted)
        }
        self.view.addSubview(self.rowButton)

        let configuration = UIImage.SymbolConfiguration(pointSize: 15, weight: .semibold)
        self.backButton.setImage(UIImage(systemName: "chevron.left", withConfiguration: configuration)?.imageFlippedForRightToLeftLayoutDirection(), for: .normal)
        self.closeButton.setImage(UIImage(systemName: "xmark", withConfiguration: configuration), for: .normal)
        self.backButton.addTarget(self, action: #selector(self.backPressed), for: .touchUpInside)
        self.closeButton.addTarget(self, action: #selector(self.closePressed), for: .touchUpInside)
        for button in [self.backButton, self.closeButton] {
            button.tintColor = theme.secondaryTextColor
            button.backgroundColor = theme.itemHighlightedBackgroundColor
            button.layer.cornerRadius = 22
            self.view.addSubview(button)
        }
    }

    @objc private func rowPressed() { self.item?.action?() }
    @objc private func backPressed() { self.item?.back?() }
    @objc private func closePressed() { self.item?.close?() }

    private func updateRowHighlight(_ highlighted: Bool) {
        self.rowHighlightView.backgroundColor = highlighted
            ? self.sheetTheme.itemHighlightedBackgroundColor
            : self.item?.selected == true ? self.sheetTheme.controlAccentColor.withAlphaComponent(0.12) : .clear
    }

    func setItem(_ item: NagramiXRoundQualitySheetItem) {
        self.item = item
        self.titleLabel.text = item.title
        self.valueLabel.text = item.value
        let fontSize = self.sheetTheme.baseFontSize
        switch item.kind {
        case .header:
            self.titleLabel.font = Font.semibold(fontSize * 20 / 17)
        case .apply:
            self.titleLabel.font = Font.semibold(fontSize)
        case .parameter, .option:
            self.titleLabel.font = Font.regular(fontSize)
        }
        self.titleLabel.textColor = item.kind == .apply ? self.sheetTheme.controlAccentColor : self.sheetTheme.primaryTextColor
        self.valueLabel.font = Font.regular(fontSize * 15 / 17)
        self.valueLabel.textColor = self.sheetTheme.secondaryTextColor
        self.titleLabel.isAccessibilityElement = item.kind == .header
        self.titleLabel.accessibilityTraits = item.kind == .header ? .header : []
        self.backButton.isHidden = item.back == nil
        self.backButton.accessibilityLabel = item.backTitle
        self.closeButton.isHidden = item.close == nil
        self.closeButton.accessibilityLabel = item.closeTitle
        self.chevronView.isHidden = item.kind != .parameter
        self.radioView.isHidden = item.kind != .option
        self.radioView.layer.borderWidth = item.selected ? 0 : 1
        self.radioView.layer.borderColor = self.sheetTheme.secondaryTextColor.cgColor
        self.radioView.backgroundColor = item.selected ? self.sheetTheme.controlAccentColor : .clear
        self.radioDotView.isHidden = !item.selected
        self.separatorView.isHidden = item.kind == .apply
        self.rowButton.isHidden = item.action == nil
        self.rowButton.isEnabled = item.action != nil
        self.rowButton.isAccessibilityElement = item.action != nil
        self.rowButton.accessibilityLabel = item.title
        self.rowButton.accessibilityValue = item.value.isEmpty ? nil : item.value
        self.rowButton.accessibilityTraits = item.selected ? [.button, .selected] : .button
        self.updateRowHighlight(false)
    }

    override func updateLayout(constrainedSize: CGSize, transition: ContainedViewLayoutTransition) -> CGSize {
        guard let item = self.item else { return .zero }
        let width = constrainedSize.width
        let inset: CGFloat = 18
        let isRTL = self.view.effectiveUserInterfaceLayoutDirection == .rightToLeft
        let contentWidth = max(1, width - inset * 2)
        func origin(leading: CGFloat, width itemWidth: CGFloat) -> CGFloat {
            return isRTL ? width - leading - itemWidth : leading
        }
        func labelHeight(_ label: UILabel, width: CGFloat) -> CGFloat {
            return ceil(label.sizeThatFits(CGSize(width: width, height: .greatestFiniteMagnitude)).height)
        }

        self.titleLabel.textAlignment = item.kind == .apply ? .center : .natural
        self.valueLabel.textAlignment = isRTL ? .left : .right
        let height: CGFloat
        switch item.kind {
        case .header:
            let backSpace: CGFloat = item.back == nil ? 0 : 52
            let titleWidth = max(1, contentWidth - 52 - backSpace)
            let titleHeight = labelHeight(self.titleLabel, width: titleWidth)
            height = max(68, titleHeight + 24)
            self.titleLabel.frame = CGRect(x: origin(leading: inset + backSpace, width: titleWidth), y: floor((height - titleHeight) / 2), width: titleWidth, height: titleHeight)
            self.backButton.frame = CGRect(x: origin(leading: inset, width: 44), y: floor((height - 44) / 2), width: 44, height: 44)
            self.closeButton.frame = CGRect(x: origin(leading: width - inset - 44, width: 44), y: floor((height - 44) / 2), width: 44, height: 44)

        case .parameter, .option:
            let markerWidth: CGFloat = item.kind == .parameter ? 12 : 18
            let textWidth = max(1, contentWidth - markerWidth - 10)
            let valueWidth = item.value.isEmpty ? 0 : max(1, floor(textWidth * 0.46))
            let titleWidth = max(1, textWidth - valueWidth - (item.value.isEmpty ? 0 : 8))
            let titleHeight = labelHeight(self.titleLabel, width: titleWidth)
            let valueHeight = item.value.isEmpty ? 0 : labelHeight(self.valueLabel, width: valueWidth)
            height = max(52, max(titleHeight, valueHeight) + 20)
            self.titleLabel.frame = CGRect(x: origin(leading: inset, width: titleWidth), y: floor((height - titleHeight) / 2), width: titleWidth, height: titleHeight)
            self.valueLabel.frame = CGRect(x: origin(leading: width - inset - markerWidth - 10 - valueWidth, width: valueWidth), y: floor((height - valueHeight) / 2), width: valueWidth, height: valueHeight)
            let markerFrame = CGRect(x: origin(leading: width - inset - markerWidth, width: markerWidth), y: floor((height - markerWidth) / 2), width: markerWidth, height: markerWidth)
            self.chevronView.frame = markerFrame
            self.radioView.frame = markerFrame

        case .apply:
            let titleHeight = labelHeight(self.titleLabel, width: contentWidth)
            height = max(52, titleHeight + 24)
            self.titleLabel.frame = CGRect(x: inset, y: floor((height - titleHeight) / 2), width: contentWidth, height: titleHeight)
        }
        self.rowHighlightView.frame = CGRect(x: 6, y: 3, width: max(0, width - 12), height: max(0, height - 6))
        self.separatorView.frame = CGRect(x: inset, y: height - UIScreenPixel, width: max(0, width - inset * 2), height: UIScreenPixel)
        let size = CGSize(width: width, height: height)
        self.rowButton.frame = CGRect(origin: .zero, size: size)
        self.updateInternalLayout(size, constrainedSize: constrainedSize)
        return size
    }
}
