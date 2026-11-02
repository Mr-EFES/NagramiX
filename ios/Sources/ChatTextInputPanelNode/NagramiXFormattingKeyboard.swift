import UIKit
import NagramiXCore

final class NagramiXFormattingKeyboard: UIInputView {
    struct Item {
        let action: NagramiXFormattingAction
        let title: String
        let symbol: String
        let enabled: Bool
        let selected: Bool
    }
    private let heading = UILabel()
    private let scroll = UIScrollView()
    private var buttons: [UIButton] = []
    private var items: [Item] = []
    var action: ((NagramiXFormattingAction) -> Void)?
    init(title: String) {
        super.init(frame: CGRect(x: 0, y: 0, width: 0, height: 300), inputViewStyle: .keyboard)
        self.allowsSelfSizing = true
        self.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        self.addSubview(self.heading)
        self.addSubview(self.scroll)
        self.heading.textAlignment = .center
        self.heading.text = title
        self.heading.accessibilityTraits = .header
        self.heading.font = UIFont.preferredFont(forTextStyle: .headline)
        self.heading.adjustsFontForContentSizeCategory = true
        self.scroll.alwaysBounceVertical = false
        self.scroll.contentInsetAdjustmentBehavior = .never
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    override var intrinsicContentSize: CGSize {
        return CGSize(width: UIView.noIntrinsicMetric, height: UIScreen.main.bounds.height < 500 ? 216 : 320)
    }
    func update(title: String, items: [Item], background: UIColor, foreground: UIColor, accent: UIColor) {
        self.heading.text = title
        self.heading.textColor = foreground
        self.backgroundColor = background
        self.items = items
        while self.buttons.count < items.count {
            let button = UIButton(type: .system)
            button.layer.cornerRadius = 14
            button.titleLabel?.font = UIFont.preferredFont(forTextStyle: .caption1)
            button.titleLabel?.adjustsFontForContentSizeCategory = true
            button.titleLabel?.numberOfLines = 0
            button.titleLabel?.textAlignment = .center
            button.addTarget(self, action: #selector(self.pressed(_:)), for: .touchUpInside)
            self.scroll.addSubview(button); self.buttons.append(button)
        }
        for (index, button) in self.buttons.enumerated() {
            guard index < items.count else { button.isHidden = true; continue }
            let item = items[index]
            button.isHidden = false; button.tag = index; button.isEnabled = item.enabled
            var configuration = UIButton.Configuration.plain()
            configuration.title = item.title
            configuration.image = UIImage(systemName: item.symbol, withConfiguration: UIImage.SymbolConfiguration(pointSize: 22, weight: .medium))
            configuration.imagePlacement = .top; configuration.imagePadding = 10
            configuration.titleLineBreakMode = .byWordWrapping
            configuration.baseForegroundColor = item.selected ? accent : foreground
            configuration.titleTextAttributesTransformer = UIConfigurationTextAttributesTransformer { attributes in
                var attributes = attributes
                attributes.font = UIFont.preferredFont(forTextStyle: .caption1)
                return attributes
            }
            button.configuration = configuration
            button.backgroundColor = item.selected ? accent.withAlphaComponent(0.15) : .clear
            button.alpha = item.enabled ? 1 : 0.35
            button.accessibilityLabel = item.title
            button.accessibilityTraits = item.selected ? [.button, .selected] : [.button]
            if !item.enabled { button.accessibilityTraits.insert(.notEnabled) }
        }
        self.setNeedsLayout()
    }
    override func layoutSubviews() {
        super.layoutSubviews()
        let inset: CGFloat = 10
        let headingHeight = max(36, self.heading.font.lineHeight + 8)
        let scrollTop = headingHeight + 14
        self.heading.frame = CGRect(x: inset, y: 8, width: max(0, self.bounds.width - inset * 2), height: headingHeight)
        self.scroll.frame = CGRect(x: inset, y: scrollTop, width: max(0, self.bounds.width - inset * 2), height: max(0, self.bounds.height - scrollTop - self.safeAreaInsets.bottom))
        let columns: Int
        if self.traitCollection.preferredContentSizeCategory.isAccessibilityCategory {
            columns = max(2, min(5, Int(self.bounds.width / 145)))
        } else {
            columns = self.bounds.width >= 360 ? 5 : 4
        }
        let width = self.scroll.bounds.width / CGFloat(columns)
        let rows = max(1, (self.items.count + columns - 1) / columns)
        let labelHeight = UIFont.preferredFont(forTextStyle: .caption1).lineHeight * 3
        let height = max(labelHeight + 44, min(120, self.scroll.bounds.height / CGFloat(rows)))
        for (index, button) in self.buttons.enumerated() {
            button.frame = CGRect(x: CGFloat(index % columns) * width + 3, y: CGFloat(index / columns) * height + 3, width: max(0, width - 6), height: height - 6)
        }
        self.scroll.contentSize = CGSize(width: self.scroll.bounds.width, height: height * CGFloat(rows))
    }
    @objc private func pressed(_ button: UIButton) {
        guard button.tag >= 0, button.tag < self.items.count, self.items[button.tag].enabled else { return }
        self.action?(self.items[button.tag].action)
    }
}
