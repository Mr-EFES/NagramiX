import UIKit
import NagramiXCore

private final class NagramiXFormattingKey: UIButton {
    let glyph = UIImageView()
    let caption = UILabel()
    override init(frame: CGRect) {
        super.init(frame: frame)
        self.addSubview(self.glyph)
        self.addSubview(self.caption)
        self.glyph.contentMode = .scaleAspectFit
        self.caption.textAlignment = .center
        self.caption.numberOfLines = 1
        self.caption.lineBreakMode = .byClipping
        self.caption.adjustsFontSizeToFitWidth = true
        self.caption.minimumScaleFactor = 0.9
        self.caption.adjustsFontForContentSizeCategory = true
        self.caption.isAccessibilityElement = false
        self.glyph.isAccessibilityElement = false
        self.isAccessibilityElement = true
        self.layer.cornerRadius = 10
        self.layer.cornerCurve = .continuous
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    override var isHighlighted: Bool {
        didSet { self.alpha = self.isEnabled ? (self.isHighlighted ? 0.7 : 1.0) : 0.45 }
    }
    override func layoutSubviews() {
        super.layoutSubviews()
        let glyphHeight: CGFloat = 26
        let textHeight = ceil(self.caption.font.lineHeight)
        let groupHeight = glyphHeight + 8 + textHeight
        let top = max(4, floor((self.bounds.height - groupHeight) / 2))
        self.glyph.frame = CGRect(x: max(0, (self.bounds.width - 30) / 2), y: top, width: min(30, self.bounds.width), height: glyphHeight)
        self.caption.frame = CGRect(x: 2, y: top + glyphHeight + 8, width: max(0, self.bounds.width - 4), height: textHeight)
    }
}

final class NagramiXFormattingKeyboard: UIInputView {
    struct Item {
        let action: NagramiXFormattingAction
        let title: String
        let accessibilityTitle: String
        let symbol: String
        let enabled: Bool
        let selected: Bool
    }
    private let heading = UILabel()
    private let scroll = UIScrollView()
    private var buttons: [NagramiXFormattingKey] = []
    private var items: [Item] = []
    private var preferredHeight: CGFloat
    var action: ((NagramiXFormattingAction) -> Void)?

    init(title: String, height: CGFloat) {
        self.preferredHeight = height
        super.init(frame: CGRect(x: 0, y: 0, width: 0, height: height), inputViewStyle: .keyboard)
        // UIInputView owns the native keyboard material. Do not paint a settings
        // list color over it or add a second bottom safe-area inset to its height.
        self.allowsSelfSizing = true
        self.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        self.addSubview(self.heading)
        self.addSubview(self.scroll)
        self.heading.text = title
        self.heading.textAlignment = .center
        self.heading.accessibilityTraits = .header
        self.heading.adjustsFontForContentSizeCategory = true
        self.scroll.contentInsetAdjustmentBehavior = .never
        self.scroll.alwaysBounceVertical = false
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    override var intrinsicContentSize: CGSize {
        return CGSize(width: UIView.noIntrinsicMetric, height: self.preferredHeight)
    }
    func updateHeight(_ height: CGFloat) {
        guard height.isFinite, height > 0, abs(self.preferredHeight - height) > 0.5 else { return }
        self.preferredHeight = height
        self.frame.size.height = height
        self.invalidateIntrinsicContentSize()
        self.setNeedsLayout()
    }
    func update(title: String, items: [Item], appearance: UIKeyboardAppearance, accent: UIColor) {
        switch appearance {
        case .dark: self.overrideUserInterfaceStyle = .dark
        case .light: self.overrideUserInterfaceStyle = .light
        default: self.overrideUserInterfaceStyle = .unspecified
        }
        self.heading.text = title
        self.heading.font = UIFont.preferredFont(forTextStyle: .headline)
        self.heading.textColor = .label
        self.items = items
        while self.buttons.count < items.count {
            let button = NagramiXFormattingKey(frame: .zero)
            button.addTarget(self, action: #selector(self.pressed(_:)), for: .touchUpInside)
            self.scroll.addSubview(button)
            self.buttons.append(button)
        }
        let font = UIFontMetrics(forTextStyle: .caption1).scaledFont(for: UIFont.systemFont(ofSize: 12), maximumPointSize: 28)
        let keyColor = UIColor { traits in
            traits.userInterfaceStyle == .dark ? UIColor(white: 0.26, alpha: 1) : .white
        }
        for (index, button) in self.buttons.enumerated() {
            guard index < items.count else { button.isHidden = true; continue }
            let item = items[index]
            button.isHidden = false
            button.tag = index
            button.isEnabled = item.enabled
            button.isSelected = item.selected
            button.caption.text = item.title
            button.caption.font = font
            button.caption.textColor = item.selected ? accent : .label
            button.glyph.image = UIImage(systemName: item.symbol, withConfiguration: UIImage.SymbolConfiguration(pointSize: 23, weight: .regular))?.withRenderingMode(.alwaysTemplate)
            button.glyph.tintColor = item.selected ? accent : .label
            button.backgroundColor = item.selected ? accent.withAlphaComponent(0.18) : keyColor
            button.alpha = item.enabled ? 1 : 0.45
            button.accessibilityLabel = item.accessibilityTitle
            button.accessibilityTraits = item.selected ? [.button, .selected] : [.button]
            if !item.enabled { button.accessibilityTraits.insert(.notEnabled) }
        }
        self.setNeedsLayout()
    }
    override func layoutSubviews() {
        super.layoutSubviews()
        let inset: CGFloat = 8
        let headingHeight = max(36, self.heading.font.lineHeight + 8)
        let left = inset + self.safeAreaInsets.left
        let right = inset + self.safeAreaInsets.right
        let contentWidth = max(0, self.bounds.width - left - right)
        self.heading.frame = CGRect(x: left, y: 4, width: contentWidth, height: headingHeight)
        let top = headingHeight + 12
        self.scroll.frame = CGRect(x: left, y: top, width: contentWidth, height: max(0, self.bounds.height - top - self.safeAreaInsets.bottom - 8))
        let font = self.buttons.first?.caption.font ?? UIFont.systemFont(ofSize: 12)
        let minimumFont = font.withSize(font.pointSize * 0.9)
        let minimumLabelWidth = self.items.map { ($0.title as NSString).size(withAttributes: [.font: minimumFont]).width }.max() ?? 0
        let grid = NagramiXFormattingGrid.layout(size: self.scroll.bounds.size, count: self.items.count,
            minimumLabelWidth: ceil(minimumLabelWidth), minimumKeyHeight: font.lineHeight + 50,
            accessibility: self.traitCollection.preferredContentSizeCategory.isAccessibilityCategory)
        for (index, button) in self.buttons.enumerated() where index < grid.frames.count {
            button.frame = grid.frames[index]
        }
        self.scroll.contentSize = grid.contentSize
    }
    override func didMoveToWindow() {
        super.didMoveToWindow()
        self.heading.layer.removeAllAnimations()
        self.scroll.layer.removeAllAnimations()
        self.heading.alpha = 1
        self.scroll.alpha = 1
        guard self.window != nil, !UIAccessibility.isReduceMotionEnabled else { return }
        // Keep the native keyboard backdrop and geometry stationary; only its
        // new content fades in. UIKit owns replacement of the keyboard itself.
        self.heading.alpha = 0
        self.scroll.alpha = 0
        UIView.animate(withDuration: 0.16, delay: 0, options: [.beginFromCurrentState, .allowUserInteraction, .curveEaseInOut], animations: {
            self.heading.alpha = 1
            self.scroll.alpha = 1
        })
    }
    @objc private func pressed(_ button: UIButton) {
        guard button.tag >= 0, button.tag < self.items.count, self.items[button.tag].enabled else { return }
        self.action?(self.items[button.tag].action)
    }
}
