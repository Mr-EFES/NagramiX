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

private enum NagramiXRevisionComparison {
    // Preserve whole graphemes and keep punctuation independent from words.
    // UTF-16 offsets address the original entity-formatted NSAttributedString.
    private struct Tokens {
        var words: [Substring] = []
        var offsets: [Int] = [0]

        init(_ text: String) {
            var start = text.startIndex
            var offset = 0
            var inWord = false
            for index in text.indices {
                let character = text[index]
                let word = (character.isLetter || character.isNumber)
                    && !character.unicodeScalars.contains(where: { $0.properties.isIdeographic })
                if index != start && !(word && inWord) {
                    self.words.append(text[start..<index])
                    self.offsets.append(offset)
                    start = index
                }
                offset += character.utf16.count
                inWord = word
            }
            if start != text.endIndex {
                self.words.append(text[start...])
                self.offsets.append(offset)
            }
        }
    }

    static func changedRanges(older: String, newer: String, showingNewer: Bool) -> [NSRange] {
        guard older != newer else { return [] }
        let before = Tokens(older)
        let after = Tokens(newer)
        // Tokens present on only one side are always changes. Exclude them
        // before alignment so rewriting a long message does not stall scrolling.
        let shared = Set(before.words).intersection(after.words)
        let ids = Dictionary(uniqueKeysWithValues: shared.enumerated().map { ($0.element, $0.offset) })
        let oldIDs = before.words.map { ids[$0] }
        let newIDs = after.words.map { ids[$0] }
        let difference = newIDs.compactMap { $0 }.difference(from: oldIDs.compactMap { $0 })
        let offsets = showingNewer ? after.offsets : before.offsets
        var sharedPositions: [Int] = []
        var changed = IndexSet()
        for (position, id) in (showingNewer ? newIDs : oldIDs).enumerated() {
            if id == nil {
                changed.insert(position)
            } else {
                sharedPositions.append(position)
            }
        }
        for change in showingNewer ? difference.insertions : difference.removals {
            switch change {
            case let .insert(position, _, _), let .remove(position, _, _):
                changed.insert(sharedPositions[position])
            }
        }
        return changed.rangeView.map { range in
            NSRange(location: offsets[range.lowerBound], length: offsets[range.upperBound] - offsets[range.lowerBound])
        }
    }
}

/// Размер зависит от шрифта и всех цифр номера, а не от свободной ширины заголовка.
private final class NagramiXEditHistoryCounterBadge: UIView {
    let label = UILabel()

    override init(frame: CGRect) {
        super.init(frame: frame)
        self.isAccessibilityElement = false
        self.isUserInteractionEnabled = false
        self.layer.cornerCurve = .circular
        self.setContentHuggingPriority(.required, for: .horizontal)
        self.setContentHuggingPriority(.required, for: .vertical)
        self.setContentCompressionResistancePriority(.required, for: .horizontal)
        self.setContentCompressionResistancePriority(.required, for: .vertical)
        self.label.isAccessibilityElement = false
        self.label.numberOfLines = 1
        self.label.textAlignment = .center
        self.label.translatesAutoresizingMaskIntoConstraints = false
        self.addSubview(self.label)
        NSLayoutConstraint.activate([
            self.widthAnchor.constraint(equalTo: self.heightAnchor),
            self.label.centerXAnchor.constraint(equalTo: self.centerXAnchor),
            self.label.centerYAnchor.constraint(equalTo: self.centerYAnchor),
            self.label.leadingAnchor.constraint(greaterThanOrEqualTo: self.leadingAnchor, constant: 5.0),
            self.label.trailingAnchor.constraint(lessThanOrEqualTo: self.trailingAnchor, constant: -5.0),
            self.label.topAnchor.constraint(greaterThanOrEqualTo: self.topAnchor, constant: 2.0),
            self.label.bottomAnchor.constraint(lessThanOrEqualTo: self.bottomAnchor, constant: -2.0)
        ])
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    override var intrinsicContentSize: CGSize {
        let labelSize = self.label.intrinsicContentSize
        let paddedDiameter = max(labelSize.width + 10.0, labelSize.height + 4.0)
        let glyphDiameter = (labelSize.width * labelSize.width + labelSize.height * labelSize.height).squareRoot() + 4.0
        let diameter = ceil(max(22.0, max(paddedDiameter, glyphDiameter)))
        return CGSize(width: diameter, height: diameter)
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        self.layer.cornerRadius = min(self.bounds.width, self.bounds.height) * 0.5
    }
}

private final class NagramiXEditHistoryCell: UITableViewCell {
    private let card = UIView()
    private let heading = UILabel()
    private let counterBadge = NagramiXEditHistoryCounterBadge(frame: .zero)
    private var counter: UILabel { self.counterBadge.label }
    private let headerStack = UIStackView()
    private let date = UILabel()
    private let changeLabel = UILabel()
    private let messageLine = UIStackView()
    private let textView = UITextView()
    private let divider = UIView()
    private let actions = UIStackView()
    private let copyButton = UIButton(type: .system)
    private let forwardButton = UIButton(type: .system)
    private let broadcastButton = UIButton(type: .system)
    private let shareButton = UIButton(type: .system)
    private var broadcastAction: (() -> Void)?
    private var shareAction: (() -> Void)?
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
        self.counter.setContentCompressionResistancePriority(.required, for: .horizontal)
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
        self.changeLabel.numberOfLines = 0
        self.changeLabel.setContentHuggingPriority(.required, for: .horizontal)
        self.messageLine.addArrangedSubview(self.changeLabel)
        self.messageLine.addArrangedSubview(self.textView)
        self.messageLine.spacing = 6.0
        for (button, selector) in [
            (self.copyButton, #selector(self.copyPressed)), (self.forwardButton, #selector(self.forwardPressed)),
            (self.broadcastButton, #selector(self.broadcastPressed)), (self.shareButton, #selector(self.sharePressed))
        ] {
            button.addTarget(self, action: selector, for: .touchUpInside)
            button.titleLabel?.numberOfLines = 0
            self.actions.addArrangedSubview(button)
            let height = button.heightAnchor.constraint(greaterThanOrEqualToConstant: 44.0)
            height.priority = UILayoutPriority(999)
            height.isActive = true
        }
        self.actions.spacing = 2.0
        self.actions.distribution = .fillEqually
        let stack = UIStackView(arrangedSubviews: [self.headerStack, self.date, self.messageLine, self.divider, self.actions])
        stack.axis = .vertical
        stack.spacing = 4.0
        stack.setCustomSpacing(6.0, after: self.date)
        stack.setCustomSpacing(7.0, after: self.messageLine)
        stack.setCustomSpacing(0.0, after: self.divider)
        self.card.translatesAutoresizingMaskIntoConstraints = false
        stack.translatesAutoresizingMaskIntoConstraints = false
        self.contentView.addSubview(self.card)
        self.card.addSubview(stack)
        NSLayoutConstraint.activate([
            self.card.leadingAnchor.constraint(equalTo: self.contentView.leadingAnchor, constant: 16.0),
            self.card.trailingAnchor.constraint(equalTo: self.contentView.trailingAnchor, constant: -16.0),
            self.card.topAnchor.constraint(equalTo: self.contentView.topAnchor, constant: 4.0),
            self.card.bottomAnchor.constraint(equalTo: self.contentView.bottomAnchor, constant: -4.0),
            stack.leadingAnchor.constraint(equalTo: self.card.leadingAnchor, constant: 16.0),
            stack.trailingAnchor.constraint(equalTo: self.card.trailingAnchor, constant: -16.0),
            stack.topAnchor.constraint(equalTo: self.card.topAnchor, constant: 10.0),
            stack.bottomAnchor.constraint(equalTo: self.card.bottomAnchor, constant: -4.0)
        ])
        let dividerHeight = self.divider.heightAnchor.constraint(equalToConstant: 1.0 / UIScreen.main.scale)
        dividerHeight.priority = UILayoutPriority(999.0)
        dividerHeight.isActive = true
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    func configure(revision: NagramiXMessageRevision, index: Int, count: Int, neighbor: NagramiXMessageRevision?, presentationData: PresentationData, canExport: Bool, canForward: Bool, canBroadcast: Bool, copy: @escaping () -> Void, forward: @escaping () -> Void, broadcast: @escaping () -> Void, share: @escaping () -> Void) {
        let theme = presentationData.theme
        let strings = presentationData.strings
        let size = presentationData.listsFontSize.baseDisplaySize * (15.0 / 17.0)
        let font = UIFontMetrics(forTextStyle: .body).scaledFont(for: Font.regular(size))
        let bold = UIFontMetrics(forTextStyle: .body).scaledFont(for: Font.semibold(size))
        let caption = UIFontMetrics(forTextStyle: .caption1).scaledFont(for: Font.regular(12.0))
        self.heading.font = bold
        self.counter.font = UIFontMetrics(forTextStyle: .caption1).scaledFont(for: Font.semibold(12.0))
        self.date.font = caption
        self.card.backgroundColor = theme.list.itemBlocksBackgroundColor
        self.heading.textColor = theme.list.itemPrimaryTextColor
        self.date.textColor = theme.list.itemSecondaryTextColor
        self.divider.backgroundColor = theme.list.itemBlocksSeparatorColor
        let isCurrent = index == count - 1
        let label = isCurrent ? strings.nagramiXCurrentVersion : strings.nagramiXSavedVersion
        self.heading.text = label
        let numberFormatter = NumberFormatter()
        numberFormatter.locale = Locale(identifier: strings.baseLanguageCode)
        numberFormatter.numberStyle = .decimal
        numberFormatter.usesGroupingSeparator = false
        let ordinal = numberFormatter.string(from: NSNumber(value: index + 1)) ?? String(index + 1)
        let total = numberFormatter.string(from: NSNumber(value: count)) ?? String(count)
        self.counter.text = ordinal
        self.heading.accessibilityLabel = label + ", " + ordinal + " / " + total
        self.counter.textColor = isCurrent ? .white : theme.list.itemPrimaryTextColor
        self.counterBadge.backgroundColor = isCurrent ? theme.list.itemAccentColor : theme.list.itemSecondaryTextColor.withAlphaComponent(0.18)
        self.counterBadge.invalidateIntrinsicContentSize()
        self.counterBadge.setNeedsLayout()
        // Keep ordinary actions side by side; large accessibility sizes receive
        // the full card width instead of shrinking or truncating their titles.
        let accessibleSize = self.traitCollection.preferredContentSizeCategory.isAccessibilityCategory
        // Номер остаётся в верхнем trailing-углу и при Accessibility/RTL;
        // длинный заголовок занимает оставшуюся ширину и переносится целиком.
        self.headerStack.axis = .horizontal
        self.headerStack.alignment = .top
        self.messageLine.axis = accessibleSize ? .vertical : .horizontal
        self.messageLine.alignment = accessibleSize ? .fill : .firstBaseline
        self.actions.axis = accessibleSize ? .vertical : .horizontal
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: strings.baseLanguageCode)
        formatter.dateStyle = .medium
        formatter.timeStyle = .medium
        self.date.text = formatter.string(from: Date(timeIntervalSince1970: TimeInterval(revision.timestamp)))
        self.textView.isSelectable = canExport && !revision.text.isEmpty
        func rendered(_ version: NagramiXMessageRevision) -> NSAttributedString {
            return stringWithAppliedEntities(
                version.text.isEmpty ? strings.nagramiXRevisionWithoutText : version.text,
                entities: version.text.isEmpty ? [] : version.entities, baseColor: theme.list.itemPrimaryTextColor,
                linkColor: theme.list.itemAccentColor, baseFont: font, linkFont: font,
                boldFont: bold, italicFont: Font.italic(font.pointSize),
                boldItalicFont: Font.semiboldItalic(font.pointSize), fixedFont: Font.monospace(font.pointSize),
                blockQuoteFont: font, message: nil
            )
        }
        let text = NSMutableAttributedString(attributedString: rendered(revision))
        let color = isCurrent ? theme.list.freeTextSuccessColor : theme.list.itemDestructiveColor
        self.changeLabel.text = isCurrent ? strings.nagramiXLocalized("NagramiX.EditHistory.After") : strings.nagramiXLocalized("NagramiX.EditHistory.Before")
        self.changeLabel.textColor = color
        self.changeLabel.font = UIFontMetrics(forTextStyle: .caption1).scaledFont(for: Font.semibold(12.0))
        let decoration: NSAttributedString.Key = isCurrent ? .underlineStyle : .strikethroughStyle
        if let neighbor, !revision.text.isEmpty {
            // Entity rendering can substitute a formatted date and change UTF-16 offsets.
            let other = neighbor.text.isEmpty ? "" : rendered(neighbor).string
            let ranges = NagramiXRevisionComparison.changedRanges(
                older: isCurrent ? other : text.string,
                newer: isCurrent ? text.string : other, showingNewer: isCurrent
            )
            for range in ranges {
                text.addAttributes([.foregroundColor: color, decoration: NSUnderlineStyle.single.rawValue], range: range)
            }
        }
        self.textView.attributedText = text
        self.copyAction = copy
        self.forwardAction = forward
        self.broadcastAction = broadcast
        self.shareAction = share
        for (button, title, symbol) in [
            (self.copyButton, strings.Conversation_ContextMenuCopy, "doc.on.doc"),
            (self.forwardButton, strings.Conversation_ContextMenuForward, "person"),
            (self.broadcastButton, strings.nagramiXLocalized("NagramiX.EditHistory.Broadcast"), "person.2"),
            (self.shareButton, strings.Conversation_ContextMenuShare, "square.and.arrow.up")
        ] {
            var configuration = UIButton.Configuration.plain()
            configuration.title = title
            configuration.image = UIImage(systemName: symbol, withConfiguration: UIImage.SymbolConfiguration(pointSize: 18.0, weight: .regular))
            configuration.imagePlacement = accessibleSize ? .leading : .top
            configuration.imagePadding = 3.0
            configuration.titleAlignment = .center
            configuration.titleLineBreakMode = .byWordWrapping
            configuration.contentInsets = NSDirectionalEdgeInsets(top: 3, leading: 1, bottom: 3, trailing: 1)
            configuration.baseForegroundColor = theme.list.itemAccentColor
            configuration.titleTextAttributesTransformer = UIConfigurationTextAttributesTransformer { attributes in
                var attributes = attributes
                attributes.font = caption
                return attributes
            }
            button.configuration = configuration
            button.accessibilityLabel = title + ", " + (self.heading.accessibilityLabel ?? label)
        }
        self.actions.isHidden = !canExport || revision.text.isEmpty
        self.forwardButton.isHidden = !canForward
        self.broadcastButton.isHidden = !canBroadcast
        self.divider.isHidden = self.actions.isHidden
    }

    @objc private func broadcastPressed() { self.broadcastAction?() }
    @objc private func sharePressed() { self.shareAction?() }
    @objc private func copyPressed() { self.copyAction?() }
    @objc private func forwardPressed() { self.forwardAction?() }
}

final class NagramiXEditHistoryController: ViewController, UITableViewDataSource {
    private let context: AccountContext
    private let message: EngineRawMessage
    private let canExport: Bool
    private let forwardRevision: ((EngineRawMessage) -> Void)?
    private let broadcastRevision: (([EngineRawMessage]) -> Void)?
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

    init(context: AccountContext, message: EngineRawMessage, revisions: [NagramiXMessageRevision], canExport: Bool, forward: ((EngineRawMessage) -> Void)?, broadcast: (([EngineRawMessage]) -> Void)? = nil) {
        self.context = context
        self.message = message
        self.revisions = revisions
        self.canExport = canExport
        self.forwardRevision = forward
        self.broadcastRevision = broadcast
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
        self.tableView.estimatedRowHeight = 134.0
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
                let top = self.tableView.indexPathsForVisibleRows?.min()
                var anchor: (index: Int, inset: CGFloat)?
                if self.tableView.contentOffset.y > 0, let top {
                    let index = self.revisions.count - 1 - top.row
                    if revisions.indices.contains(index), self.revisions[index] == revisions[index] {
                        anchor = (index, self.tableView.contentOffset.y - self.tableView.rectForRow(at: top).minY)
                    }
                }
                self.revisions = revisions
                self.refreshPresentationAndLayout(anchor: anchor)
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

    private func refreshPresentationAndLayout(anchor: (index: Int, inset: CGFloat)? = nil) {
        // Keep the same reading position when a newer edit or theme arrives.
        let offset = self.tableView.contentOffset
        self.updatePresentation()
        if let layout = self.validLayout {
            self.containerLayoutUpdated(layout, transition: .immediate)
        }
        self.tableView.layoutIfNeeded()
        var y = offset.y
        if let anchor {
            let path = IndexPath(row: self.revisions.count - 1 - anchor.index, section: 0)
            self.tableView.scrollToRow(at: path, at: .top, animated: false)
            self.tableView.layoutIfNeeded()
            y = self.tableView.rectForRow(at: path).minY + anchor.inset
        }
        let maxOffset = max(0.0, self.tableView.contentSize.height - self.tableView.bounds.height)
        self.tableView.setContentOffset(CGPoint(x: 0.0, y: min(maxOffset, max(0.0, y))), animated: false)
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
        let index = self.revisions.count - 1 - indexPath.row
        let revision = self.revisions[index]
        let isCurrent = index == self.revisions.count - 1
        let adjacentIndex = isCurrent ? index - 1 : index + 1
        let neighbor = self.revisions.indices.contains(adjacentIndex) ? self.revisions[adjacentIndex] : nil
        cell.configure(revision: revision, index: index, count: self.revisions.count, neighbor: neighbor, presentationData: self.presentationData, canExport: self.canExport, canForward: self.forwardRevision != nil, canBroadcast: self.broadcastRevision != nil, copy: { [weak self] in
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
        }, broadcast: { [weak self] in
            guard let self, self.canExport else { return }
            self.broadcastRevision?([nagramiXEditHistorySnapshot(message: self.message, revision: revision)])
        }, share: { [weak self] in
            guard let self, self.canExport else { return }
            let controller = self.context.sharedContext.makeShareScreen(context: self.context, params: ShareControllerParams(
                subject: .text(revision.text), externalShare: true, immediateExternalShare: true
            ))
            self.present(controller, in: .window(.root))
        })
        return cell
    }
}
