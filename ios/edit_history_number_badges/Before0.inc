import Foundation
import UIKit
import AsyncDisplayKit
import Display
import TelegramCore
import AccountContext
import TelegramPresentationData
import PresentationDataUtils
import TextFormat
import Pasteboard
import UndoUI
import SwiftSignalKit
import NagramiXCore

/// A local text/caption snapshot, never a server-side forward of the live ID.
/// Выбранный текст передаётся отдельному действию истории без повторного
/// получения сегодняшней версии сообщения из Postbox.
func nagramiXEditHistorySnapshot(message: EngineRawMessage, revision: NagramiXMessageRevision) -> EngineRawMessage {
    return message.withUpdatedText(revision.text).withUpdatedMedia([]).withUpdatedAttributes([
        TextEntitiesMessageAttribute(entities: revision.entities),
        NagramiXArchivedMessageAttribute(deletedAt: 0, revisions: [])
    ])
}

private final class NagramiXEditHistoryCell: UITableViewCell {
    private let card = UIView()
    private let heading = UILabel()
    private let counter = UILabel()
    private let counterBadge = UIView()
    private let headerStack = UIStackView()
    private let date = UILabel()
    private let textView = UITextView()
    private let divider = UIView()
    private let actions = UIStackView()
    private let copyButton = UIButton(type: .system)
    private let forwardButton = UIButton(type: .system)
    private var copyAction: (() -> Void)?
    private var forwardAction: (() -> Void)?

    override init(style: UITableViewCell.CellStyle, reuseIdentifier: String?) {
        super.init(style: style, reuseIdentifier: reuseIdentifier)
        self.selectionStyle = .none
        self.backgroundColor = .clear
        self.card.layer.cornerRadius = 20.0
        self.card.layer.cornerCurve = .continuous
        self.heading.numberOfLines = 0
        self.heading.accessibilityTraits = .header
        self.counter.isAccessibilityElement = false
        self.counter.setContentCompressionResistancePriority(.required, for: .horizontal)
        self.counterBadge.layer.cornerRadius = 10.0
        self.counterBadge.layer.cornerCurve = .continuous
        self.counterBadge.setContentHuggingPriority(.required, for: .horizontal)
        self.counterBadge.setContentCompressionResistancePriority(.required, for: .horizontal)
        self.counterBadge.addSubview(self.counter)
        self.counter.translatesAutoresizingMaskIntoConstraints = false
        self.headerStack.addArrangedSubview(self.heading)
        self.headerStack.addArrangedSubview(self.counterBadge)
        self.headerStack.spacing = 8.0
        self.headerStack.alignment = .top
        self.date.numberOfLines = 0
        self.textView.isEditable = false
        self.textView.isScrollEnabled = false
        self.textView.backgroundColor = .clear
        self.textView.textContainerInset = .zero
        self.textView.textContainer.lineFragmentPadding = 0.0
        self.textView.setContentCompressionResistancePriority(.required, for: .vertical)
        self.copyButton.titleLabel?.numberOfLines = 0
        self.forwardButton.titleLabel?.numberOfLines = 0
        self.copyButton.contentHorizontalAlignment = .leading
        self.forwardButton.contentHorizontalAlignment = .leading
        self.copyButton.addTarget(self, action: #selector(self.copyPressed), for: .touchUpInside)
        self.forwardButton.addTarget(self, action: #selector(self.forwardPressed), for: .touchUpInside)
        self.actions.addArrangedSubview(self.copyButton)
        self.actions.addArrangedSubview(self.forwardButton)
        self.actions.spacing = 12.0
        self.actions.distribution = .fillEqually
        let stack = UIStackView(arrangedSubviews: [self.headerStack, self.date, self.textView, self.divider, self.actions])
        stack.axis = .vertical
        stack.spacing = 8.0
        stack.setCustomSpacing(14.0, after: self.date)
        stack.setCustomSpacing(14.0, after: self.textView)
        stack.setCustomSpacing(0.0, after: self.divider)
        self.card.translatesAutoresizingMaskIntoConstraints = false
        stack.translatesAutoresizingMaskIntoConstraints = false
        self.contentView.addSubview(self.card)
        self.card.addSubview(stack)
        // UIStackView collapses hidden export buttons to zero height. Let that
        // required constraint win while keeping a 44pt target for visible ones.
        let copyHeight = self.copyButton.heightAnchor.constraint(greaterThanOrEqualToConstant: 44.0)
        let forwardHeight = self.forwardButton.heightAnchor.constraint(greaterThanOrEqualToConstant: 44.0)
        copyHeight.priority = UILayoutPriority(999.0)
        forwardHeight.priority = UILayoutPriority(999.0)
        NSLayoutConstraint.activate([
            self.card.leadingAnchor.constraint(equalTo: self.contentView.leadingAnchor, constant: 16.0),
            self.card.trailingAnchor.constraint(equalTo: self.contentView.trailingAnchor, constant: -16.0),
            self.card.topAnchor.constraint(equalTo: self.contentView.topAnchor, constant: 6.0),
            self.card.bottomAnchor.constraint(equalTo: self.contentView.bottomAnchor, constant: -6.0),
            stack.leadingAnchor.constraint(equalTo: self.card.leadingAnchor, constant: 16.0),
            stack.trailingAnchor.constraint(equalTo: self.card.trailingAnchor, constant: -16.0),
            stack.topAnchor.constraint(equalTo: self.card.topAnchor, constant: 16.0),
            stack.bottomAnchor.constraint(equalTo: self.card.bottomAnchor, constant: -12.0),
            self.counter.leadingAnchor.constraint(equalTo: self.counterBadge.leadingAnchor, constant: 8.0),
            self.counter.trailingAnchor.constraint(equalTo: self.counterBadge.trailingAnchor, constant: -8.0),
            self.counter.topAnchor.constraint(equalTo: self.counterBadge.topAnchor, constant: 3.0),
            self.counter.bottomAnchor.constraint(equalTo: self.counterBadge.bottomAnchor, constant: -3.0),
            copyHeight,
            forwardHeight
        ])
        let dividerHeight = self.divider.heightAnchor.constraint(equalToConstant: 1.0 / UIScreen.main.scale)
        dividerHeight.priority = UILayoutPriority(999.0)
        dividerHeight.isActive = true
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    func configure(revision: NagramiXMessageRevision, index: Int, count: Int, presentationData: PresentationData, canExport: Bool, canForward: Bool, copy: @escaping () -> Void, forward: @escaping () -> Void) {
        let theme = presentationData.theme
        let strings = presentationData.strings
        let size = presentationData.listsFontSize.baseDisplaySize
        let font = UIFontMetrics(forTextStyle: .body).scaledFont(for: Font.regular(size))
        let bold = UIFontMetrics(forTextStyle: .body).scaledFont(for: Font.semibold(size))
        self.heading.font = bold
        self.counter.font = UIFontMetrics(forTextStyle: .caption1).scaledFont(for: Font.semibold(13.0))
        self.date.font = UIFontMetrics(forTextStyle: .caption1).scaledFont(for: Font.regular(13.0))
        self.card.backgroundColor = theme.list.itemBlocksBackgroundColor
        self.heading.textColor = theme.list.itemPrimaryTextColor
        self.date.textColor = theme.list.itemSecondaryTextColor
        self.divider.backgroundColor = theme.list.itemBlocksSeparatorColor
        let isCurrent = index == count - 1
        let label = isCurrent ? strings.nagramiXCurrentVersion : strings.nagramiXSavedVersion
        self.heading.text = label
        self.counter.text = "\(index + 1) / \(count)"
        self.heading.accessibilityLabel = label + ", " + (self.counter.text ?? "")
        self.counter.textColor = isCurrent ? theme.list.itemAccentColor : theme.list.itemSecondaryTextColor
        self.counterBadge.backgroundColor = isCurrent ? theme.list.itemAccentColor.withAlphaComponent(0.16) : .clear
        // Keep ordinary actions side by side; large accessibility sizes receive
        // the full card width instead of shrinking or truncating their titles.
        let accessibleSize = self.traitCollection.preferredContentSizeCategory.isAccessibilityCategory
        self.headerStack.axis = accessibleSize ? .vertical : .horizontal
        self.headerStack.alignment = accessibleSize ? .leading : .top
        self.actions.axis = accessibleSize ? .vertical : .horizontal
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: strings.baseLanguageCode)
        formatter.dateStyle = .medium
        formatter.timeStyle = .medium
        self.date.text = formatter.string(from: Date(timeIntervalSince1970: TimeInterval(revision.timestamp)))
        self.textView.isSelectable = canExport && !revision.text.isEmpty
        self.textView.attributedText = stringWithAppliedEntities(
            revision.text.isEmpty ? strings.nagramiXRevisionWithoutText : revision.text,
            entities: revision.text.isEmpty ? [] : revision.entities, baseColor: theme.list.itemPrimaryTextColor,
            linkColor: theme.list.itemAccentColor, baseFont: font, linkFont: font,
            boldFont: bold, italicFont: Font.italic(font.pointSize),
            boldItalicFont: Font.semiboldItalic(font.pointSize), fixedFont: Font.monospace(font.pointSize),
            blockQuoteFont: font, message: nil
        )
        self.copyAction = copy
        self.forwardAction = forward
        self.copyButton.accessibilityLabel = strings.Conversation_ContextMenuCopy + ", " + (self.heading.accessibilityLabel ?? label)
        self.forwardButton.accessibilityLabel = strings.Conversation_ContextMenuForward + ", " + (self.heading.accessibilityLabel ?? label)
        for (button, title, symbol) in [
            (self.copyButton, strings.Conversation_ContextMenuCopy, "doc.on.doc"),
            (self.forwardButton, strings.Conversation_ContextMenuForward, "arrowshape.turn.up.right")
        ] {
            var configuration = UIButton.Configuration.plain()
            configuration.title = title
            configuration.image = UIImage(systemName: symbol, withConfiguration: UIImage.SymbolConfiguration(pointSize: font.pointSize, weight: .regular))?.imageFlippedForRightToLeftLayoutDirection()
            configuration.imagePlacement = .leading
            configuration.imagePadding = 6.0
            configuration.titleAlignment = .leading
            configuration.titleLineBreakMode = .byWordWrapping
            configuration.contentInsets = NSDirectionalEdgeInsets(top: 10.0, leading: 0.0, bottom: 10.0, trailing: 0.0)
            configuration.baseForegroundColor = theme.list.itemAccentColor
            configuration.titleTextAttributesTransformer = UIConfigurationTextAttributesTransformer { attributes in
                var attributes = attributes
                attributes.font = font
                return attributes
            }
            button.configuration = configuration
        }
        self.copyButton.isHidden = !canExport || revision.text.isEmpty
        self.forwardButton.isHidden = !canExport || !canForward || revision.text.isEmpty
        self.actions.isHidden = self.copyButton.isHidden && self.forwardButton.isHidden
        self.divider.isHidden = self.actions.isHidden
    }

    @objc private func copyPressed() { self.copyAction?() }
    @objc private func forwardPressed() { self.forwardAction?() }
}

final class NagramiXEditHistoryController: ViewController, UITableViewDataSource {
    private let context: AccountContext
    private let message: EngineRawMessage
    private let canExport: Bool
    private let forwardRevision: ((EngineRawMessage) -> Void)?
    private let tableView = UITableView(frame: .zero, style: .plain)
    private let emptyStateLabel = UILabel()
    private let emptyStateContainer = UIView()
    private var didApplyInitialLayout = false
    private var presentationData: PresentationData
    private var revisions: [NagramiXMessageRevision]
    private var updatesDisposable: Disposable?
    private var presentationDisposable: Disposable?
    private var contentSizeObserver: NSObjectProtocol?
    private var validLayout: ContainerViewLayout?
    private weak var copyOverlay: UndoOverlayController?

    init(context: AccountContext, message: EngineRawMessage, revisions: [NagramiXMessageRevision], canExport: Bool, forward: ((EngineRawMessage) -> Void)?) {
        self.context = context
        self.message = message
        self.revisions = revisions
        self.canExport = canExport
        self.forwardRevision = forward
        self.presentationData = context.sharedContext.currentPresentationData.with { $0 }
        super.init(navigationBarPresentationData: NavigationBarPresentationData(presentationData: self.presentationData))
        self.updatePresentation()
    }

    required init(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    deinit {
        self.updatesDisposable?.dispose()
        self.presentationDisposable?.dispose()
        if let observer = self.contentSizeObserver {
            NotificationCenter.default.removeObserver(observer)
        }
    }

    override func loadDisplayNode() {
        self.displayNode = ASDisplayNode()
        self.tableView.dataSource = self
        self.tableView.register(NagramiXEditHistoryCell.self, forCellReuseIdentifier: "revision")
        self.tableView.rowHeight = UITableView.automaticDimension
        self.tableView.estimatedRowHeight = 204.0
        self.tableView.separatorStyle = .none
        self.tableView.contentInsetAdjustmentBehavior = .never
        self.tableView.alwaysBounceVertical = true
        if #available(iOS 15.0, *) {
            self.tableView.sectionHeaderTopPadding = 0.0
        }
        self.emptyStateLabel.numberOfLines = 0
        self.emptyStateContainer.addSubview(self.emptyStateLabel)
        self.displayNode.view.addSubview(self.tableView)
        self.displayNodeDidLoad()
        self.updatePresentation()
        self.updatesDisposable = (self.context.account.nagramiXMessageArchive.updates |> deliverOnMainQueue).start(next: { [weak self] _ in
            guard let self else { return }
            // The stored current revision can be newer than the source EngineRawMessage
            // captured when the context menu was opened. Never replace it with
            // that stale source text on refresh.
            let revisions = self.context.account.nagramiXMessageArchive.revisions(messageId: self.message.id)
            if self.revisions != revisions {
                self.revisions = revisions
                self.refreshPresentationAndLayout()
            }
        })
        self.presentationDisposable = (self.context.sharedContext.presentationData |> deliverOnMainQueue).start(next: { [weak self] data in
            guard let self else { return }
            self.presentationData = data
            self.refreshPresentationAndLayout()
        })
        self.contentSizeObserver = NotificationCenter.default.addObserver(forName: UIContentSizeCategory.didChangeNotification, object: nil, queue: .main, using: { [weak self] _ in
            self?.refreshPresentationAndLayout()
        })
    }

    private func refreshPresentationAndLayout() {
        // Keep the same reading position when a newer edit or theme arrives.
        let offset = self.tableView.contentOffset
        self.updatePresentation()
        if let layout = self.validLayout {
            self.containerLayoutUpdated(layout, transition: .immediate)
        }
        self.tableView.layoutIfNeeded()
        let maxOffset = max(0.0, self.tableView.contentSize.height - self.tableView.bounds.height)
        self.tableView.setContentOffset(CGPoint(x: 0.0, y: min(maxOffset, max(0.0, offset.y))), animated: false)
    }

    private func updatePresentation() {
        self.title = self.presentationData.strings.nagramiXEditHistory
        self.statusBar.statusBarStyle = self.presentationData.theme.rootController.statusBarStyle.style
        self.navigationItem.leftBarButtonItem = UIBarButtonItem(title: self.presentationData.strings.Common_Close, style: .plain, target: self, action: #selector(self.closePressed))
        self.navigationBar?.updatePresentationData(NavigationBarPresentationData(presentationData: self.presentationData), transition: .immediate)
        guard self.isNodeLoaded else { return }
        self.displayNode.backgroundColor = self.presentationData.theme.list.blocksBackgroundColor
        self.tableView.backgroundColor = self.presentationData.theme.list.blocksBackgroundColor
        self.emptyStateLabel.text = self.presentationData.strings.nagramiXNoPreviousVersions
        self.emptyStateLabel.textColor = self.presentationData.theme.list.itemSecondaryTextColor
        self.emptyStateLabel.font = UIFontMetrics(forTextStyle: .footnote).scaledFont(for: Font.regular(14.0))
        self.tableView.backgroundView = self.revisions.isEmpty ? self.emptyStateContainer : nil
        self.tableView.reloadData()
    }

    @objc private func closePressed() { self.dismiss() }

    override func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        self.validLayout = layout
        super.containerLayoutUpdated(layout, transition: transition)
        let top = self.navigationLayout(layout: layout).navigationFrame.maxY
        let bottom = layout.insets(options: [.input]).bottom
        let width = max(0.0, layout.size.width - layout.safeInsets.left - layout.safeInsets.right)
        transition.updateFrame(view: self.tableView, frame: CGRect(x: layout.safeInsets.left, y: top, width: width, height: max(0.0, layout.size.height - top - bottom)))
        let textWidth = max(1.0, width - 40.0)
        let height = self.emptyStateLabel.sizeThatFits(CGSize(width: textWidth, height: .greatestFiniteMagnitude)).height
        self.emptyStateLabel.frame = CGRect(x: 20.0, y: 16.0, width: textWidth, height: height)
        if !self.didApplyInitialLayout, width > 0.0, self.tableView.bounds.height > 0.0 {
            self.tableView.layoutIfNeeded()
            self.tableView.setContentOffset(.zero, animated: false)
            self.didApplyInitialLayout = true
        }
    }

    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        return self.revisions.count
    }

    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "revision", for: indexPath) as! NagramiXEditHistoryCell
        let revision = self.revisions[indexPath.row]
        cell.configure(revision: revision, index: indexPath.row, count: self.revisions.count, presentationData: self.presentationData, canExport: self.canExport, canForward: self.forwardRevision != nil, copy: { [weak self] in
            guard let self, self.canExport else { return }
            storeMessageTextInPasteboard(revision.text, entities: revision.entities)
            let replacing = self.copyOverlay != nil
            self.copyOverlay?.dismissWithCommitActionAndReplacementAnimation()
            let overlay = UndoOverlayController(presentationData: self.presentationData, content: .copy(text: self.presentationData.strings.Conversation_MessageCopied), elevatedLayout: false, animateInAsReplacement: replacing, action: { _ in false })
            self.copyOverlay = overlay
            self.present(overlay, in: .current)
        }, forward: { [weak self] in
            guard let self, self.canExport else { return }
            self.forwardRevision?(nagramiXEditHistorySnapshot(message: self.message, revision: revision))
        })
        return cell
    }
}
