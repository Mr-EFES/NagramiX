import NagramiXCore
import Foundation
import UIKit
import Display
import AsyncDisplayKit
import SwiftSignalKit
import TelegramCore
import AccountContext
import TelegramPresentationData
import ItemListUI

public final class NagramiXMessageTranslationController: ViewController {
    private let context: AccountContext
    private let presentationData: PresentationData
    private let text: String
    private let entities: [MessageTextEntity]
    private let canCopy: Bool
    private let closed: (() -> Void)?
    private var source: String
    private var target: String
    private let dim = UIControl()
    private let card = UIView()
    private let scroll = UIScrollView()
    private let stack = UIStackView()
    private let original = UITextView()
    private let result = UITextView()
    private let status = UILabel()
    private let sourceButton = UIButton(type: .system)
    private let targetButton = UIButton(type: .system)
    private let copyButton = UIButton(type: .system)
    private let retryButton = UIButton(type: .system)
    private let request = MetaDisposable()
    private var generation = UUID()
    private var closing = false
    private var didAnimate = false
    private var observer: NSObjectProtocol?
    private var interface: String { NagramiXTranslationLanguage.base(self.presentationData.strings.baseLanguageCode) }

    public init(context: AccountContext, text: String, entities: [MessageTextEntity], canCopy: Bool,
                source: String?, target: String?, closed: (() -> Void)? = nil) {
        self.context = context; self.text = text; self.entities = entities; self.canCopy = canCopy; self.closed = closed
        self.presentationData = context.sharedContext.currentPresentationData.with { $0 }
        self.source = source ?? nagramiXTranslationSource(text, interface: "") ?? ""
        let settings = NagramiXTranslationSettings.current
        self.target = target ?? (settings.target.isEmpty ? NagramiXTranslationLanguage.base(self.presentationData.strings.baseLanguageCode) : settings.target)
        super.init(navigationBarPresentationData: nil)
        self.statusBar.statusBarStyle = .Ignore
        self.observer = NotificationCenter.default.addObserver(forName: NagramiXTranslationSettings.changed, object: nil, queue: .main) { [weak self] _ in self?.translate() }
    }
    public required init(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    deinit { self.request.dispose(); if let observer { NotificationCenter.default.removeObserver(observer) } }

    public override func loadDisplayNode() {
        self.displayNode = ASDisplayNode()
        let theme = self.presentationData.theme
        self.dim.backgroundColor = UIColor.black.withAlphaComponent(0.35)
        self.dim.addTarget(self, action: #selector(self.close), for: .touchUpInside)
        self.displayNode.view.addSubview(self.dim)
        self.card.backgroundColor = theme.list.itemBlocksBackgroundColor
        self.card.layer.cornerRadius = 24; self.card.layer.maskedCorners = [.layerMinXMinYCorner, .layerMaxXMinYCorner]
        self.card.clipsToBounds = true
        self.displayNode.view.addSubview(self.card)
        self.scroll.translatesAutoresizingMaskIntoConstraints = false; self.card.addSubview(self.scroll)
        self.stack.axis = .vertical; self.stack.spacing = 18; self.stack.translatesAutoresizingMaskIntoConstraints = false
        self.scroll.addSubview(self.stack)
        NSLayoutConstraint.activate([
            self.scroll.leadingAnchor.constraint(equalTo: self.card.leadingAnchor), self.scroll.trailingAnchor.constraint(equalTo: self.card.trailingAnchor),
            self.scroll.topAnchor.constraint(equalTo: self.card.topAnchor), self.scroll.bottomAnchor.constraint(equalTo: self.card.bottomAnchor),
            self.stack.leadingAnchor.constraint(equalTo: self.scroll.contentLayoutGuide.leadingAnchor, constant: 20),
            self.stack.trailingAnchor.constraint(equalTo: self.scroll.contentLayoutGuide.trailingAnchor, constant: -20),
            self.stack.topAnchor.constraint(equalTo: self.scroll.contentLayoutGuide.topAnchor, constant: 18),
            self.stack.bottomAnchor.constraint(equalTo: self.scroll.contentLayoutGuide.bottomAnchor, constant: -32),
            self.stack.widthAnchor.constraint(equalTo: self.scroll.frameLayoutGuide.widthAnchor, constant: -40)
        ])
        let grabberContainer = UIView()
        grabberContainer.heightAnchor.constraint(equalToConstant: 8).isActive = true
        let grabber = UIView(); grabber.backgroundColor = theme.list.itemSecondaryTextColor.withAlphaComponent(0.5)
        grabber.layer.cornerRadius = 2; grabber.translatesAutoresizingMaskIntoConstraints = false
        grabberContainer.addSubview(grabber)
        NSLayoutConstraint.activate([grabber.widthAnchor.constraint(equalToConstant: 36), grabber.heightAnchor.constraint(equalToConstant: 4),
            grabber.centerXAnchor.constraint(equalTo: grabberContainer.centerXAnchor), grabber.topAnchor.constraint(equalTo: grabberContainer.topAnchor)])
        self.stack.addArrangedSubview(grabberContainer)
        let title = UILabel(); title.text = self.presentationData.strings.nagramiXUILocalized("Перевод"); title.font = Font.semibold(self.presentationData.listsFontSize.itemListBaseFontSize + 2)
        title.textColor = theme.list.itemPrimaryTextColor
        let close = UIButton(type: .system); close.setTitle("×", for: .normal); close.titleLabel?.font = Font.regular(30)
        close.tintColor = theme.list.itemSecondaryTextColor; close.accessibilityLabel = self.presentationData.strings.nagramiXUILocalized("Закрыть")
        close.addTarget(self, action: #selector(self.close), for: .touchUpInside)
        close.widthAnchor.constraint(equalToConstant: 44).isActive = true
        let header = UIStackView(arrangedSubviews: [title, close]); header.axis = .horizontal
        header.addGestureRecognizer(UIPanGestureRecognizer(target: self, action: #selector(self.panHeader(_:))))
        grabberContainer.addGestureRecognizer(UIPanGestureRecognizer(target: self, action: #selector(self.panHeader(_:))))
        self.stack.addArrangedSubview(header)
        let arrow = UILabel(); arrow.text = "→"; arrow.textColor = theme.list.itemSecondaryTextColor
        let languages = UIStackView(arrangedSubviews: [self.sourceButton, arrow, self.targetButton]); languages.axis = .horizontal; languages.spacing = 12
        self.sourceButton.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        self.targetButton.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        for button in [self.sourceButton, self.targetButton] {
            button.tintColor = theme.list.itemAccentColor; button.titleLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
            button.titleLabel?.numberOfLines = 0; button.heightAnchor.constraint(greaterThanOrEqualToConstant: 44).isActive = true
        }
        self.sourceButton.addTarget(self, action: #selector(self.chooseSource), for: .touchUpInside)
        self.targetButton.addTarget(self, action: #selector(self.chooseTarget), for: .touchUpInside)
        self.stack.addArrangedSubview(languages)
        for view in [self.original, self.result] {
            view.isEditable = false; view.isSelectable = self.canCopy; view.isScrollEnabled = false
            view.backgroundColor = .clear; view.textContainerInset = .zero; view.textContainer.lineFragmentPadding = 0
            view.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
            view.textColor = theme.list.itemPrimaryTextColor
            view.adjustsFontForContentSizeCategory = true
        }
        self.stack.addArrangedSubview(self.section(self.presentationData.strings.nagramiXUILocalized("ОРИГИНАЛ"))); self.stack.addArrangedSubview(self.original)
        let divider = UIView(); divider.backgroundColor = theme.list.itemBlocksSeparatorColor
        divider.heightAnchor.constraint(equalToConstant: UIScreenPixel).isActive = true; self.stack.addArrangedSubview(divider)
        self.stack.addArrangedSubview(self.section(self.presentationData.strings.nagramiXUILocalized("ПЕРЕВОД"))); self.stack.addArrangedSubview(self.result)
        self.status.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)
        self.status.textColor = theme.list.itemSecondaryTextColor; self.status.numberOfLines = 0; self.stack.addArrangedSubview(self.status)
        self.retryButton.setTitle(self.presentationData.strings.nagramiXUILocalized("Повторить перевод"), for: .normal); self.retryButton.tintColor = theme.list.itemAccentColor
        self.retryButton.titleLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
        self.retryButton.addTarget(self, action: #selector(self.retry), for: .touchUpInside)
        self.retryButton.heightAnchor.constraint(greaterThanOrEqualToConstant: 44).isActive = true; self.stack.addArrangedSubview(self.retryButton)
        self.copyButton.setTitle(self.presentationData.strings.nagramiXUILocalized("Скопировать перевод"), for: .normal); self.copyButton.backgroundColor = theme.list.itemAccentColor
        self.copyButton.setTitleColor(theme.list.itemCheckColors.foregroundColor, for: .normal)
        self.copyButton.titleLabel?.font = Font.semibold(self.presentationData.listsFontSize.itemListBaseFontSize)
        self.copyButton.titleLabel?.numberOfLines = 0; self.copyButton.layer.cornerRadius = 12
        self.copyButton.heightAnchor.constraint(greaterThanOrEqualToConstant: 50).isActive = true
        self.copyButton.addTarget(self, action: #selector(self.copyResult), for: .touchUpInside)
        self.stack.addArrangedSubview(self.copyButton)
        self.original.attributedText = self.attributed(self.text, entities: self.entities)
        self.displayNodeDidLoad(); self.translate()
    }
    private func section(_ text: String) -> UILabel {
        let label = UILabel(); label.text = text
        label.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)
        label.textColor = self.presentationData.theme.list.sectionHeaderTextColor
        return label
    }
    private func attributed(_ text: String, entities: [MessageTextEntity]) -> NSAttributedString {
        let size = self.presentationData.listsFontSize.itemListBaseFontSize
        let value = NSMutableAttributedString(string: text, attributes: [.font: Font.regular(size), .foregroundColor: self.presentationData.theme.list.itemPrimaryTextColor])
        for entity in entities {
            guard entity.range.lowerBound >= 0, entity.range.upperBound <= value.length else { continue }
            let range = NSRange(location: entity.range.lowerBound, length: entity.range.count)
            switch entity.type {
            case .Bold: value.addAttribute(.font, value: Font.semibold(size), range: range)
            case .Italic: value.addAttribute(.font, value: UIFont.italicSystemFont(ofSize: size), range: range)
            case .Code, .Pre: value.addAttribute(.font, value: UIFont.monospacedSystemFont(ofSize: size, weight: .regular), range: range)
            case .Underline: value.addAttribute(.underlineStyle, value: NSUnderlineStyle.single.rawValue, range: range)
            case .Strikethrough: value.addAttribute(.strikethroughStyle, value: NSUnderlineStyle.single.rawValue, range: range)
            case .Url: value.addAttribute(.link, value: (text as NSString).substring(with: range), range: range)
            case let .TextUrl(url): value.addAttribute(.link, value: url, range: range)
            default: break
            }
        }
        return value
    }
    public override func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
        self.dim.frame = CGRect(origin: .zero, size: layout.size)
        let width = min(layout.size.width, 640)
        let height = min(layout.size.height - max(layout.insets(options: []).top, 12), max(480, layout.size.height * 0.65))
        self.card.frame = CGRect(x: (layout.size.width - width) / 2, y: layout.size.height - height, width: width, height: height)
        self.scroll.contentInset.bottom = layout.intrinsicInsets.bottom
    }
    public override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        guard !self.didAnimate else { return }; self.didAnimate = true
        if !UIAccessibility.isReduceMotionEnabled {
            self.card.transform = CGAffineTransform(translationX: 0, y: self.card.bounds.height); self.dim.alpha = 0
            UIView.animate(withDuration: 0.25) { self.card.transform = .identity; self.dim.alpha = 1 }
        }
    }
    private func translate() {
        guard self.isNodeLoaded, !self.closing else { return }
        self.request.set(nil)
        self.generation = UUID(); let generation = self.generation
        let configuration = NagramiXTranslationSettings.current
        self.sourceButton.setTitle(self.source.isEmpty ? self.presentationData.strings.nagramiXUILocalized("Выбрать язык") : NagramiXTranslationLanguage.title(self.source, interface: self.interface), for: .normal)
        self.targetButton.setTitle(NagramiXTranslationLanguage.title(self.target, interface: self.interface), for: .normal)
        self.result.text = self.presentationData.strings.nagramiXUILocalized("Перевод…"); self.status.text = self.presentationData.strings.nagramiXUILocalized(configuration.provider.title)
        self.copyButton.isHidden = true; self.retryButton.isHidden = true
        guard configuration.enabled else { self.result.text = self.presentationData.strings.nagramiXUILocalized("Перевод отключён в настройках."); return }
        guard !self.source.isEmpty else { self.result.text = self.presentationData.strings.nagramiXUILocalized(NagramiXTranslationFailure.invalidText.text); return }
        self.request.set((nagramiXTranslateText(context: self.context, text: self.text, entities: self.entities, source: self.source, target: self.target, configuration: configuration)
        |> timeout(180, queue: .mainQueue(), alternate: .fail(.network))
        |> deliverOnMainQueue).start(next: { [weak self] text, entities in
            guard let self, self.generation == generation, !self.closing, NagramiXTranslationSettings.current.revision == configuration.revision else { return }
            self.result.attributedText = self.attributed(text, entities: entities)
            self.copyButton.isHidden = !self.canCopy
        }, error: { [weak self] error in
            guard let self, self.generation == generation, !self.closing, NagramiXTranslationSettings.current.revision == configuration.revision else { return }
            self.result.text = self.presentationData.strings.nagramiXUILocalized(error.text); self.retryButton.isHidden = false
        }))
    }
    @objc private func retry() { self.translate() }
    @objc private func panHeader(_ gesture: UIPanGestureRecognizer) {
        guard !self.closing else { return }
        let distance = max(0, gesture.translation(in: self.card).y)
        switch gesture.state {
        case .changed: self.card.transform = CGAffineTransform(translationX: 0, y: distance)
        case .ended:
            if distance > 80 || gesture.velocity(in: self.card).y > 650 { self.close() }
            else { UIView.animate(withDuration: 0.2) { self.card.transform = .identity } }
        case .cancelled, .failed: UIView.animate(withDuration: 0.2) { self.card.transform = .identity }
        default: break
        }
    }
    @objc private func copyResult() { if self.canCopy && !self.copyButton.isHidden { UIPasteboard.general.string = self.result.text } }
    @objc private func chooseSource() { self.chooseLanguage(source: true) }
    @objc private func chooseTarget() { self.chooseLanguage(source: false) }
    private func chooseLanguage(source: Bool) {
        let controller = UIAlertController(title: source ? self.presentationData.strings.nagramiXUILocalized("Исходный язык") : self.presentationData.strings.nagramiXUILocalized("Язык перевода"), message: nil, preferredStyle: .actionSheet)
        for language in supportedTranslationLanguages {
            controller.addAction(UIAlertAction(title: NagramiXTranslationLanguage.title(language, interface: self.interface), style: .default, handler: { [weak self] _ in
                guard let self else { return }
                if source { self.source = language } else { self.target = language }
                self.translate()
            }))
        }
        controller.addAction(UIAlertAction(title: self.presentationData.strings.Common_Cancel, style: .cancel))
        controller.popoverPresentationController?.sourceView = source ? self.sourceButton : self.targetButton
        controller.popoverPresentationController?.sourceRect = (source ? self.sourceButton : self.targetButton).bounds
        self.present(controller, animated: true)
    }
    @objc private func close() {
        guard !self.closing else { return }; self.closing = true
        self.request.set(nil); self.closed?()
        UIView.animate(withDuration: UIAccessibility.isReduceMotionEnabled ? 0 : 0.2, animations: {
            self.card.transform = CGAffineTransform(translationX: 0, y: self.card.bounds.height); self.dim.alpha = 0
        }, completion: { [weak self] _ in self?.dismiss() })
    }
}
