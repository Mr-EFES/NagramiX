import Foundation
import UIKit
import AsyncDisplayKit
import Display
import TelegramPresentationData
import NagramiXCore

struct NagramiXOptionSheetOption {
    let id: Int
    let title: String
    let subtitle: String
}

// Reuse Telegram's sheet presentation, scrolling, dismissal and theme.
func nagramiXOptionSheet(presentationData: PresentationData, title: String, options: [NagramiXOptionSheetOption], selectedId: Int, footnote: String, selected: @escaping (Int) -> Void) -> ActionSheetController {
    let controller = ActionSheetController(presentationData: presentationData)
    var finished = false
    controller.dismissed = { _ in finished = true }
    let close: () -> Void = { [weak controller] in
        guard let controller, !finished else { return }
        finished = true
        controller.dismissAnimated()
    }
    var items: [ActionSheetItem] = [NagramiXOptionSheetItem(kind: .header(closeTitle: presentationData.strings.nagramiXOptionSheetClose), title: title, action: close)]
    for (index, option) in options.enumerated() {
        items.append(NagramiXOptionSheetItem(kind: .option(selected: selectedId == option.id, separator: index != options.count - 1), title: option.title, subtitle: option.subtitle, action: { [weak controller] in
            guard let controller, !finished else { return }
            finished = true
            controller.dismissAnimated()
            selected(option.id)
        }))
    }
    if !footnote.isEmpty {
        items.append(NagramiXOptionSheetItem(kind: .footer, title: footnote))
    }
    controller.setItemGroups([ActionSheetItemGroup(items: items)])
    return controller
}

private final class NagramiXOptionSheetItem: ActionSheetItem {
    enum Kind {
        case header(closeTitle: String)
        case option(selected: Bool, separator: Bool)
        case footer
    }

    let kind: Kind
    let title: String
    let subtitle: String
    let action: () -> Void

    init(kind: Kind, title: String, subtitle: String = "", action: @escaping () -> Void = {}) {
        self.kind = kind
        self.title = title
        self.subtitle = subtitle
        self.action = action
    }

    func node(theme: ActionSheetControllerTheme) -> ActionSheetItemNode {
        let node = NagramiXOptionSheetItemNode(theme: theme)
        node.setItem(self)
        return node
    }

    func updateNode(_ node: ActionSheetItemNode) {
        guard let node = node as? NagramiXOptionSheetItemNode else { return }
        node.setItem(self)
        node.requestLayoutUpdate()
    }
}

private final class NagramiXOptionSheetItemNode: ActionSheetItemNode {
    private let sheetTheme: ActionSheetControllerTheme
    private var item: NagramiXOptionSheetItem?
    private let titleLabel = UILabel()
    private let subtitleLabel = UILabel()
    private let button = HighlightTrackingButton()
    private let closeButton = UIButton(type: .system)
    private let checkView = UIImageView()
    private let grabber = UIView()

    override init(theme: ActionSheetControllerTheme) {
        self.sheetTheme = theme
        super.init(theme: theme)
        self.titleLabel.numberOfLines = 0
        self.subtitleLabel.numberOfLines = 0
        self.titleLabel.isUserInteractionEnabled = false
        self.subtitleLabel.isUserInteractionEnabled = false
        self.checkView.isUserInteractionEnabled = false
        self.checkView.isAccessibilityElement = false
        self.checkView.contentMode = .scaleAspectFit
        self.checkView.image = UIImage(systemName: "checkmark", withConfiguration: UIImage.SymbolConfiguration(pointSize: 19.0, weight: .semibold))
        self.checkView.tintColor = theme.controlAccentColor
        self.grabber.isUserInteractionEnabled = false
        self.grabber.isAccessibilityElement = false
        self.grabber.backgroundColor = theme.controlColor
        self.grabber.layer.cornerRadius = 2.0
        self.closeButton.setImage(UIImage(systemName: "xmark", withConfiguration: UIImage.SymbolConfiguration(pointSize: 15.0, weight: .semibold)), for: .normal)
        self.closeButton.tintColor = theme.secondaryTextColor
        self.closeButton.backgroundColor = theme.itemHighlightedBackgroundColor
        self.closeButton.layer.cornerRadius = 22.0
        self.closeButton.addTarget(self, action: #selector(self.pressed), for: .touchUpInside)
        self.button.addTarget(self, action: #selector(self.pressed), for: .touchUpInside)
        self.button.isAccessibilityElement = true
        self.button.highligthedChanged = { [weak self] highlighted in
            guard let self else { return }
            self.backgroundNode.backgroundColor = highlighted ? self.sheetTheme.itemHighlightedBackgroundColor : self.sheetTheme.itemBackgroundColor
        }
        self.view.addSubview(self.button)
        self.view.addSubview(self.titleLabel)
        self.view.addSubview(self.subtitleLabel)
        self.view.addSubview(self.checkView)
        self.view.addSubview(self.grabber)
        self.view.addSubview(self.closeButton)
    }

    func setItem(_ item: NagramiXOptionSheetItem) {
        self.item = item
        self.titleLabel.text = item.title
        self.subtitleLabel.text = item.subtitle
        self.titleLabel.textAlignment = .natural
        self.subtitleLabel.textAlignment = .natural
        self.titleLabel.textColor = self.sheetTheme.primaryTextColor
        self.subtitleLabel.textColor = self.sheetTheme.secondaryTextColor
        self.titleLabel.font = Font.regular(self.sheetTheme.baseFontSize)
        self.subtitleLabel.font = Font.regular(floor(self.sheetTheme.baseFontSize * 14.0 / 17.0))
        self.titleLabel.isAccessibilityElement = false
        self.subtitleLabel.isAccessibilityElement = false
        self.button.isHidden = true
        self.closeButton.isHidden = true
        self.checkView.isHidden = true
        self.grabber.isHidden = true
        self.subtitleLabel.isHidden = item.subtitle.isEmpty
        self.hasSeparator = false
        switch item.kind {
        case let .header(closeTitle):
            self.titleLabel.font = Font.semibold(floor(self.sheetTheme.baseFontSize * 20.0 / 17.0))
            self.titleLabel.isAccessibilityElement = true
            self.titleLabel.accessibilityTraits = .header
            self.closeButton.isHidden = false
            self.closeButton.accessibilityLabel = closeTitle
            self.grabber.isHidden = false
        case let .option(selected, separator):
            self.hasSeparator = separator
            self.button.isHidden = false
            self.button.accessibilityLabel = item.subtitle.isEmpty ? item.title : item.title + ". " + item.subtitle
            self.button.accessibilityTraits = selected ? [.button, .selected] : [.button]
            self.checkView.isHidden = !selected
        case .footer:
            self.titleLabel.font = self.subtitleLabel.font
            self.titleLabel.textColor = self.sheetTheme.secondaryTextColor
            self.titleLabel.isAccessibilityElement = true
            self.titleLabel.accessibilityTraits = .staticText
        }
    }

    override func updateLayout(constrainedSize: CGSize, transition: ContainedViewLayoutTransition) -> CGSize {
        guard let item = self.item else { return super.updateLayout(constrainedSize: constrainedSize, transition: transition) }
        let width = constrainedSize.width
        let inset: CGFloat = 20.0
        let isRTL = self.view.effectiveUserInterfaceLayoutDirection == .rightToLeft
        let height: CGFloat
        switch item.kind {
        case .header:
            let textWidth = max(1.0, width - inset * 2.0 - 52.0)
            let titleSize = self.titleLabel.sizeThatFits(CGSize(width: textWidth, height: .greatestFiniteMagnitude))
            height = max(88.0, titleSize.height + 48.0)
            self.titleLabel.frame = CGRect(x: isRTL ? inset + 52.0 : inset, y: 32.0, width: textWidth, height: titleSize.height)
            self.closeButton.frame = CGRect(x: isRTL ? inset : width - inset - 44.0, y: 28.0, width: 44.0, height: 44.0)
            self.grabber.frame = CGRect(x: floor((width - 36.0) / 2.0), y: 10.0, width: 36.0, height: 4.0)
        case .option:
            // Always reserve the same trailing column, including unselected rows.
            let textWidth = max(1.0, width - inset * 2.0 - 32.0)
            let titleSize = self.titleLabel.sizeThatFits(CGSize(width: textWidth, height: .greatestFiniteMagnitude))
            let subtitleSize = item.subtitle.isEmpty ? CGSize.zero : self.subtitleLabel.sizeThatFits(CGSize(width: textWidth, height: .greatestFiniteMagnitude))
            let gap: CGFloat = item.subtitle.isEmpty ? 0.0 : 4.0
            let contentHeight = titleSize.height + gap + subtitleSize.height
            height = max(item.subtitle.isEmpty ? 60.0 : 84.0, contentHeight + 28.0)
            let textX = isRTL ? inset + 32.0 : inset
            let textY = floor((height - contentHeight) / 2.0)
            self.titleLabel.frame = CGRect(x: textX, y: textY, width: textWidth, height: titleSize.height)
            self.subtitleLabel.frame = CGRect(x: textX, y: textY + titleSize.height + gap, width: textWidth, height: subtitleSize.height)
            self.checkView.frame = CGRect(x: isRTL ? inset : width - inset - 22.0, y: floor((height - 22.0) / 2.0), width: 22.0, height: 22.0)
        case .footer:
            let textWidth = max(1.0, width - inset * 2.0)
            let titleSize = self.titleLabel.sizeThatFits(CGSize(width: textWidth, height: .greatestFiniteMagnitude))
            height = titleSize.height + 32.0
            self.titleLabel.frame = CGRect(x: inset, y: 16.0, width: textWidth, height: titleSize.height)
        }
        let size = CGSize(width: width, height: height)
        self.button.frame = CGRect(origin: .zero, size: size)
        self.updateInternalLayout(size, constrainedSize: constrainedSize)
        return size
    }

    @objc private func pressed() {
        self.item?.action()
    }
}
