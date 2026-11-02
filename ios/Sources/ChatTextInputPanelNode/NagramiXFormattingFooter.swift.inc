    enum ExtraAction { case pullQuote, selectAll }
    struct ExtraItem {
        let action: ExtraAction
        let title: String
        let enabled: Bool
        let selected: Bool
    }
    private var extraItems: [ExtraItem] = []
    private var extraButtons: [NagramiXFormattingKey] = []
    var extraAction: ((ExtraAction) -> Void)?

    func updateExtras(_ items: [ExtraItem], accent: UIColor) {
        self.extraItems = items
        while self.extraButtons.count < items.count {
            let button = NagramiXFormattingKey(frame: .zero)
            button.addTarget(self, action: #selector(self.pressedExtra(_:)), for: .touchUpInside)
            self.scroll.addSubview(button)
            self.extraButtons.append(button)
        }
        for (index, button) in self.extraButtons.enumerated() {
            guard index < items.count else { button.isHidden = true; continue }
            let item = items[index]
            button.isHidden = false
            button.tag = index
            self.configureKey(button, title: item.title, accessibilityTitle: item.title,
                symbol: item.action == .pullQuote ? "quote.bubble" : "checkmark.rectangle",
                enabled: item.enabled, selected: item.selected, accent: accent)
        }
        self.setNeedsLayout()
    }

    private func configureKey(_ button: NagramiXFormattingKey, title: String, accessibilityTitle: String,
                              symbol: String, enabled: Bool, selected: Bool, accent: UIColor) {
        button.isEnabled = enabled
        button.isSelected = selected
        button.caption.text = title
        button.caption.font = UIFontMetrics(forTextStyle: .caption1).scaledFont(for: UIFont.systemFont(ofSize: 12), maximumPointSize: 28)
        button.caption.textColor = selected ? accent : .label
        button.glyph.image = UIImage(systemName: symbol, withConfiguration: UIImage.SymbolConfiguration(pointSize: 23, weight: .regular))?.withRenderingMode(.alwaysTemplate)
        button.glyph.tintColor = selected ? accent : .label
        let keyColor = UIColor { traits in traits.userInterfaceStyle == .dark ? UIColor(white: 0.26, alpha: 1) : .white }
        button.backgroundColor = selected ? accent.withAlphaComponent(0.18) : keyColor
        button.alpha = enabled ? 1 : 0.45
        button.accessibilityLabel = accessibilityTitle
        button.accessibilityTraits = selected ? [.button, .selected] : [.button]
        if !enabled { button.accessibilityTraits.insert(.notEnabled) }
    }

    @objc private func pressedExtra(_ button: UIButton) {
        guard button.tag >= 0, button.tag < self.extraItems.count, self.extraItems[button.tag].enabled else { return }
        self.extraAction?(self.extraItems[button.tag].action)
    }
