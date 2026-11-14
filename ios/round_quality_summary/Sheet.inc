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

func nagramiXRoundQualitySheet(presentationData: PresentationData, values: MediaEditorValues) -> ActionSheetController {
    let sheet = ActionSheetController(presentationData: presentationData)
    var finished = false
    sheet.dismissed = { _ in finished = true }
    let close: () -> Void = { [weak sheet] in
        guard let sheet, !finished else { return }
        finished = true
        sheet.dismissAnimated()
    }
    var items: [ActionSheetItem] = [NagramiXRoundQualitySheetItem(title: presentationData.strings.nagramiXLocalized("NagramiX.RoundVideo.QualitySummary.Title"), header: true, closeTitle: presentationData.strings.nagramiXOptionSheetClose, close: close)]
    let rows = nagramiXRoundQualityRows(values: values, strings: presentationData.strings)
    for (index, row) in rows.enumerated() {
        items.append(NagramiXRoundQualitySheetItem(title: row.title, value: row.value, checked: row.checked, separator: index < rows.count - 1))
    }
    sheet.setItemGroups([ActionSheetItemGroup(items: items)])
    return sheet
}

private final class NagramiXRoundQualitySheetItem: ActionSheetItem {
    let title: String
    let value: String
    let header: Bool
    let checked: Bool
    let separator: Bool
    let closeTitle: String
    let close: () -> Void

    init(title: String, value: String = "", header: Bool = false, checked: Bool = false, separator: Bool = false, closeTitle: String = "", close: @escaping () -> Void = {}) {
        self.title = title; self.value = value; self.header = header; self.checked = checked
        self.separator = separator; self.closeTitle = closeTitle; self.close = close
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

    override init(theme: ActionSheetControllerTheme) {
        self.sheetTheme = theme
        super.init(theme: theme)
        self.backgroundNode.backgroundColor = .clear
        self.hasSeparator = false
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
    @objc private func closePressed() { self.item?.close() }
    func setItem(_ item: NagramiXRoundQualitySheetItem) {
        self.item = item
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
        self.view.accessibilityTraits = item.header ? [] : .staticText
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
