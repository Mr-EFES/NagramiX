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
    private func header() -> NagramiXRoundQualitySheetItem {
        return NagramiXRoundQualitySheetItem(title: self.presentationData.strings.nagramiXLocalized("NagramiX.RoundVideo.QualitySummary.Title"), header: true,
            closeTitle: self.presentationData.strings.nagramiXOptionSheetClose, close: { [weak self] in self?.close() })
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
        let labels = [rows[0].value + " · " + rows[1].value, self.bitRateTitle((self.tuning[3] - 1_000_000) / 100_000), rows[3].value, rows[4].value]
        for index in fields.indices {
            items.append(NagramiXRoundQualitySheetItem(title: titles[index], value: labels[index], separator: true, action: { [weak self] in self?.showOptions(field: fields[index]) }))
        }
        items.append(NagramiXRoundQualitySheetItem(title: self.presentationData.strings.Appearance_TextSize_Apply, action: { [weak self] in self?.apply() }))
        self.sheet?.setItemGroups([ActionSheetItemGroup(items: items)])
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
        var items: [ActionSheetItem] = [self.header()]
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
            items.append(NagramiXRoundQualitySheetItem(title: text, value: detail, checked: self.tuning[field] == value, separator: true, action: { [weak self] in
                guard let self, !self.finished else { return }
                self.tuning[field] = value
                self.showRoot()
            }))
        }
        items.append(NagramiXRoundQualitySheetItem(title: self.presentationData.strings.Common_Back, action: { [weak self] in self?.showRoot() }))
        self.sheet?.setItemGroups([ActionSheetItemGroup(items: items)])
    }
}

private final class NagramiXRoundQualitySheetItem: ActionSheetItem {
    let title: String
    let value: String
    let header: Bool
    let checked: Bool
    let separator: Bool
    let closeTitle: String
    let close: () -> Void
    let action: (() -> Void)?

    init(title: String, value: String = "", header: Bool = false, checked: Bool = false, separator: Bool = false, closeTitle: String = "", close: @escaping () -> Void = {}, action: (() -> Void)? = nil) {
        self.title = title; self.value = value; self.header = header; self.checked = checked
        self.separator = separator; self.closeTitle = closeTitle; self.close = close; self.action = action
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
    private let titleLabel = UILabel()
    private let valueLabel = UILabel()
    private let closeButton = UIButton(type: .system)
    private let checkView = UIImageView()
    private let separatorView = UIView()
    private let rowGesture = UITapGestureRecognizer()

    override init(theme: ActionSheetControllerTheme) {
        self.sheetTheme = theme
        super.init(theme: theme)
        self.backgroundNode.backgroundColor = .clear
        self.hasSeparator = false
        self.rowGesture.addTarget(self, action: #selector(self.rowPressed))
        self.view.addGestureRecognizer(self.rowGesture)
        for label in [self.titleLabel, self.valueLabel] {
            label.numberOfLines = 0
            label.isAccessibilityElement = false
            label.isUserInteractionEnabled = false
            self.view.addSubview(label)
        }
        self.checkView.isAccessibilityElement = false
        self.checkView.isUserInteractionEnabled = false
        self.checkView.contentMode = .scaleAspectFit
        self.checkView.tintColor = theme.controlAccentColor
        self.checkView.image = UIImage(systemName: "checkmark.circle.fill", withConfiguration: UIImage.SymbolConfiguration(pointSize: 25, weight: .regular))
        self.separatorView.isAccessibilityElement = false
        self.separatorView.isUserInteractionEnabled = false
        self.separatorView.backgroundColor = theme.controlColor.withAlphaComponent(0.25)
        self.closeButton.setImage(UIImage(systemName: "xmark", withConfiguration: UIImage.SymbolConfiguration(pointSize: 15, weight: .semibold)), for: .normal)
        self.closeButton.tintColor = theme.secondaryTextColor
        self.closeButton.backgroundColor = theme.itemHighlightedBackgroundColor
        self.closeButton.layer.cornerRadius = 22
        self.closeButton.addTarget(self, action: #selector(self.closePressed), for: .touchUpInside)
        self.view.addSubview(self.checkView)
        self.view.addSubview(self.separatorView)
        self.view.addSubview(self.closeButton)
    }
    @objc private func rowPressed() { self.item?.action?() }
    override func accessibilityActivate() -> Bool {
        guard let action = self.item?.action else { return false }; action(); return true
    }
    @objc private func closePressed() { self.item?.close() }
    func setItem(_ item: NagramiXRoundQualitySheetItem) {
        self.item = item
        self.rowGesture.isEnabled = item.action != nil
        self.titleLabel.text = item.title
        self.valueLabel.text = item.value
        self.titleLabel.font = item.header ? Font.semibold(self.sheetTheme.baseFontSize * 20 / 17) : Font.regular(self.sheetTheme.baseFontSize)
        self.valueLabel.font = Font.regular(self.sheetTheme.baseFontSize * (item.checked ? 14 : 17) / 17)
        self.titleLabel.textColor = self.sheetTheme.primaryTextColor
        self.valueLabel.textColor = item.checked ? self.sheetTheme.secondaryTextColor : self.sheetTheme.primaryTextColor
        self.titleLabel.textAlignment = .natural
        self.titleLabel.isAccessibilityElement = item.header
        self.titleLabel.accessibilityTraits = item.header ? .header : []
        self.closeButton.isHidden = !item.header
        self.closeButton.accessibilityLabel = item.closeTitle
        self.checkView.isHidden = !item.checked
        self.separatorView.isHidden = !(item.header || item.separator)
        self.view.isAccessibilityElement = !item.header
        self.view.accessibilityLabel = [item.title, item.value].filter { !$0.isEmpty }.joined(separator: ", ")
        self.view.accessibilityTraits = item.header ? [] : (item.action == nil ? .staticText : (item.checked ? [.button, .selected] : .button))
    }
    override func updateLayout(constrainedSize: CGSize, transition: ContainedViewLayoutTransition) -> CGSize {
        guard let item = self.item else { return .zero }
        let width = constrainedSize.width
        let inset: CGFloat = 20
        let contentWidth = max(1, width - inset * 2)
        let rtl = self.view.effectiveUserInterfaceLayoutDirection == .rightToLeft
        let height: CGFloat
        if item.header {
            let available = max(1, contentWidth - 52)
            let title = self.titleLabel.sizeThatFits(CGSize(width: available, height: .greatestFiniteMagnitude))
            height = max(68, title.height + 32)
            self.titleLabel.frame = CGRect(x: rtl ? inset + 52 : inset, y: floor((height - title.height) / 2), width: available, height: title.height)
            self.closeButton.frame = CGRect(x: rtl ? inset : width - inset - 44, y: floor((height - 44) / 2), width: 44, height: 44)
        } else if item.checked {
            let textWidth = max(1, contentWidth - 40)
            let title = self.titleLabel.sizeThatFits(CGSize(width: textWidth, height: .greatestFiniteMagnitude))
            let value = self.valueLabel.sizeThatFits(CGSize(width: textWidth, height: .greatestFiniteMagnitude))
            height = max(80, title.height + value.height + 36)
            let x = rtl ? inset : inset + 40
            self.titleLabel.frame = CGRect(x: x, y: 16, width: textWidth, height: title.height)
            self.valueLabel.textAlignment = .natural
            self.valueLabel.frame = CGRect(x: x, y: 22 + title.height, width: textWidth, height: value.height)
            self.checkView.frame = CGRect(x: rtl ? width - inset - 28 : inset, y: floor((height - 28) / 2), width: 28, height: 28)
        } else {
            let titleWidth = max(1, (contentWidth - 16) * 0.46)
            let valueWidth = max(1, contentWidth - 16 - titleWidth)
            let title = self.titleLabel.sizeThatFits(CGSize(width: titleWidth, height: .greatestFiniteMagnitude))
            let value = self.valueLabel.sizeThatFits(CGSize(width: valueWidth, height: .greatestFiniteMagnitude))
            height = max(52, max(title.height, value.height) + 28)
            self.titleLabel.frame = CGRect(x: rtl ? width - inset - titleWidth : inset, y: floor((height - title.height) / 2), width: titleWidth, height: title.height)
            self.valueLabel.textAlignment = rtl ? .left : .right
            self.valueLabel.frame = CGRect(x: rtl ? inset : width - inset - valueWidth, y: floor((height - value.height) / 2), width: valueWidth, height: value.height)
        }
        self.separatorView.frame = CGRect(x: inset, y: height - UIScreenPixel, width: max(0, width - inset * 2), height: UIScreenPixel)
        let size = CGSize(width: width, height: height)
        self.updateInternalLayout(size, constrainedSize: constrainedSize)
        return size
    }
}
