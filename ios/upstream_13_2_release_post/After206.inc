import Foundation
import UIKit
import AsyncDisplayKit
import Display
import TelegramCore
import SwiftSignalKit
import TelegramPresentationData
import NagramiXCore
import AccountContext
import AppBundle
import ChatPresentationInterfaceState
import ChatInputPanelNode
import ReactionSelectionNode
import EntityKeyboard
import TopMessageReactions
import GlassBackgroundComponent
import ComponentFlow
import ComponentDisplayAdapters

private final class ChatMessageSelectionInputPanelNodeViewForOverlayContent: UIView, ChatInputPanelViewForOverlayContent {
    var reactionContextNode: ReactionContextNode?
    var anchorRect: CGRect?
    
    override init(frame: CGRect) {
        super.init(frame: frame)
        
        self.addGestureRecognizer(UITapGestureRecognizer(target: self, action: #selector(self.backgroundTapGesture(_:))))
    }
    
    required init(coder: NSCoder) {
        preconditionFailure()
    }
    
    @objc private func backgroundTapGesture(_ recognizer: UITapGestureRecognizer) {
        if case .ended = recognizer.state {
            self.dismissReactionSelection()
        }
    }
    
    func dismissReactionSelection() {
        if let reactionContextNode = self.reactionContextNode {
            self.reactionContextNode = nil
            reactionContextNode.animateOut(to: self.anchorRect, animatingOutToReaction: false)
            ContainedViewLayoutTransition.animated(duration: 0.25, curve: .easeInOut).updateAlpha(node: reactionContextNode, alpha: 0.0, completion: { [weak reactionContextNode] _ in
                reactionContextNode?.removeFromSupernode()
            })
        }
    }
    
    func maybeDismissContent(point: CGPoint) {
        if self.hitTest(point, with: nil) == self {
            self.dismissReactionSelection()
        }
    }
    
    override func hitTest(_ point: CGPoint, with event: UIEvent?) -> UIView? {
        if let reactionContextNode = self.reactionContextNode {
            if let result = reactionContextNode.view.hitTest(self.convert(point, to: reactionContextNode.view), with: event) {
                return result
            }
            return self
        }
        return nil
    }
}

private final class GlassButtonView: UIView {
    private struct Params: Equatable {
        let theme: PresentationTheme
        let preferClearGlass: Bool
        let size: CGSize
        
        init(theme: PresentationTheme, preferClearGlass: Bool, size: CGSize) {
            self.theme = theme
            self.preferClearGlass = preferClearGlass
            self.size = size
        }
        
        static func ==(lhs: Params, rhs: Params) -> Bool {
            if lhs.theme !== rhs.theme {
                return false
            }
            if lhs.preferClearGlass != rhs.preferClearGlass {
                return false
            }
            if lhs.size != rhs.size {
                return false
            }
            return true
        }
    }
    
    private let backgroundView: GlassBackgroundView
    let button: HighlightTrackingButton
    private let iconView: GlassBackgroundView.ContentImageView
    
    private var params: Params?
    
    var isImplicitlyDisabled: Bool = false {
        didSet {
            self.updateIsEnabled()
        }
    }
    
    var isEnabled: Bool = true {
        didSet {
            self.updateIsEnabled()
        }
    }
    
    var icon: String? {
        didSet {
            if self.icon == oldValue {
                return
            }
            if let icon = self.icon {
                self.iconView.image = UIImage(bundleImageName: icon)?.withRenderingMode(.alwaysTemplate)
            } else {
                self.iconView.image = nil
            }
            if let params = self.params {
                self.updateImpl(params: params, transition: .immediate)
            }
        }
    }
    
    /// The source for a context menu this button opens: its glass, which morphs into the menu.
    var menuSourceView: UIView {
        return self.backgroundView
    }
    
    var systemIcon: String? {
        didSet {
            if self.systemIcon == oldValue { return }
            self.iconView.image = self.systemIcon.flatMap {
                UIImage(systemName: $0, withConfiguration: UIImage.SymbolConfiguration(pointSize: 24.0, weight: .regular))
            }?.withRenderingMode(.alwaysTemplate)
            if let params = self.params {
                self.updateImpl(params: params, transition: .immediate)
            }
        }
    }

    override init(frame: CGRect) {
        self.backgroundView = GlassBackgroundView()
        self.backgroundView.morphsIntoContextMenu = true
        
        self.iconView = GlassBackgroundView.ContentImageView()
        self.backgroundView.contentView.addSubview(self.iconView)
        
        self.button = HighlightTrackingButton()
        self.backgroundView.contentView.addSubview(self.button)
        
        super.init(frame: frame)
        
        self.addSubview(self.backgroundView)
    }
    
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    func update(theme: PresentationTheme, preferClearGlass: Bool, size: CGSize, transition: ComponentTransition) {
        let params = Params(theme: theme, preferClearGlass: preferClearGlass, size: size)
        if self.params != params {
            self.iconView.tintColor = params.theme.chat.inputPanel.panelControlColor
            self.params = params
            self.updateImpl(params: params, transition: transition)
        }
    }
    
    private func updateImpl(params: Params, transition: ComponentTransition) {
        let isEnabled = self.isEnabled && !self.isImplicitlyDisabled
        
        if let image = self.iconView.image {
            let iconFrame = image.size.centered(in: CGRect(origin: CGPoint(), size: params.size))
            transition.setFrame(view: self.iconView, frame: iconFrame)
        }
        
        transition.setFrame(view: self.button, frame: CGRect(origin: CGPoint(), size: params.size))
        
        transition.setFrame(view: self.backgroundView, frame: CGRect(origin: CGPoint(), size: params.size))
        self.backgroundView.update(size: params.size, cornerRadius: min(params.size.width, params.size.height) * 0.5, isDark: params.theme.overallDarkAppearance, tintColor: .init(kind: params.preferClearGlass ? .clear : .panel), isInteractive: true, transition: transition)
        self.backgroundView.isUserInteractionEnabled = isEnabled
        
        self.iconView.alpha = isEnabled ? 1.0 : 0.5
        self.iconView.tintMask.alpha = self.iconView.alpha
        
        self.button.isEnabled = isEnabled
    }
    
    private func updateIsEnabled() {
        if let params = self.params {
            self.updateImpl(params: params, transition: .immediate)
        }
    }
}

public final class ChatMessageSelectionInputPanelNode: ChatInputPanelNode {
    private let deleteButton: GlassButtonView
    private let reportButton: GlassButtonView
    private let forwardButton: GlassButtonView
    private let shareButton: GlassButtonView
    private let forwardWithoutSourceButton: GlassButtonView
    private let broadcastButton: GlassButtonView
    private let buttonScrollView = UIScrollView()
    private let nagramiXTransferDisposable = MetaDisposable()
    private var nagramiXCanCopySelection = false
    private var nagramiXFreeContentEnabled = ContentSettings.default.nagramiXAllowsFreeContent
    private var nagramiXSelectionGeneration: UInt64 = 0
    private let tagButton: GlassButtonView
    private let tagEditButton: GlassButtonView
    
    private let reactionOverlayContainer: ChatMessageSelectionInputPanelNodeViewForOverlayContent
    
    private var validLayout: (width: CGFloat, leftInset: CGFloat, rightInset: CGFloat, bottomInset: CGFloat, additionalSideInsets: UIEdgeInsets, maxHeight: CGFloat, maxOverlayHeight: CGFloat, metrics: LayoutMetrics, isSecondary: Bool, isMediaInputExpanded: Bool, deviceMetrics: DeviceMetrics)?
    private var presentationInterfaceState: ChatPresentationInterfaceState?
    private var actions: ChatAvailableMessageActions?
    // Keep only the resolved visibility, never the previous selection's rights.
    private var nagramiXHasActionLayout = false
    
    private var theme: PresentationTheme
    private let peerMedia: Bool
    
    private let canDeleteMessagesDisposable = MetaDisposable()
    
    public var selectedMessages = Set<EngineMessage.Id>() {
        didSet {
            if oldValue != self.selectedMessages {
                self.updateActions()
            }
        }
    }
    
    public init(theme: PresentationTheme, strings: PresentationStrings, peerMedia: Bool = false) {
        self.theme = theme
        self.peerMedia = peerMedia
        
        self.deleteButton = GlassButtonView()
        self.deleteButton.icon = "Chat/Input/Accessory Panels/MessageSelectionTrash"
        self.deleteButton.isEnabled = false
        self.deleteButton.isAccessibilityElement = true
        self.deleteButton.accessibilityLabel = strings.VoiceOver_MessageContextDelete
        
        self.reportButton = GlassButtonView()
        self.reportButton.icon = "Chat/Input/Accessory Panels/MessageSelectionReport"
        self.reportButton.isEnabled = false
        self.reportButton.isAccessibilityElement = true
        self.reportButton.accessibilityLabel = strings.VoiceOver_MessageContextReport
        
        self.forwardButton = GlassButtonView()
        self.forwardButton.icon = "Chat/Input/Accessory Panels/MessageSelectionForward"
        self.forwardButton.isAccessibilityElement = true
        self.forwardButton.accessibilityLabel = strings.nagramiXForwardWithAuthor

        self.forwardWithoutSourceButton = GlassButtonView()
        self.forwardWithoutSourceButton.icon = "Chat/Context Menu/User"
        self.forwardWithoutSourceButton.isImplicitlyDisabled = true
        self.forwardWithoutSourceButton.isAccessibilityElement = true
        self.forwardWithoutSourceButton.accessibilityLabel = strings.nagramiXForwardWithoutAuthor

        self.broadcastButton = GlassButtonView()
        self.broadcastButton.icon = "Chat/Context Menu/Groups"
        self.broadcastButton.isImplicitlyDisabled = true
        self.broadcastButton.isAccessibilityElement = true
        self.broadcastButton.accessibilityLabel = strings.nagramiXBroadcastMessages
        
        self.shareButton = GlassButtonView()
        self.shareButton.icon = "Chat/Input/Accessory Panels/MessageSelectionAction"
        self.shareButton.isAccessibilityElement = true
        self.shareButton.accessibilityLabel = strings.VoiceOver_MessageContextShare
        
        self.tagButton = GlassButtonView()
        self.tagButton.icon = "Chat/Input/Accessory Panels/TagIcon"
        self.tagButton.isAccessibilityElement = true
        self.tagButton.accessibilityLabel = strings.VoiceOver_MessageSelectionButtonTag
        
        self.tagEditButton = GlassButtonView()
        self.tagEditButton.icon = "Chat/Input/Accessory Panels/TagEditIcon"
        self.tagEditButton.isAccessibilityElement = true
        self.tagEditButton.accessibilityLabel = strings.VoiceOver_MessageSelectionButtonTag
        
        self.reactionOverlayContainer = ChatMessageSelectionInputPanelNodeViewForOverlayContent()
        
        super.init()
        
        self.buttonScrollView.contentInsetAdjustmentBehavior = .never
        self.buttonScrollView.showsHorizontalScrollIndicator = false
        self.buttonScrollView.showsVerticalScrollIndicator = false
        self.buttonScrollView.delaysContentTouches = false
        self.buttonScrollView.bounces = false
        self.view.addSubview(self.buttonScrollView)
        for button in [self.deleteButton, self.reportButton, self.forwardButton, self.shareButton, self.tagButton, self.tagEditButton, self.forwardWithoutSourceButton, self.broadcastButton] {
            self.buttonScrollView.addSubview(button)
        }
        
        self.viewForOverlayContent = self.reactionOverlayContainer
        
        self.forwardButton.isImplicitlyDisabled = true
        self.shareButton.isImplicitlyDisabled = true
        
        self.deleteButton.button.addTarget(self, action: #selector(self.deleteButtonPressed), for: .touchUpInside)
        self.reportButton.button.addTarget(self, action: #selector(self.reportButtonPressed), for: .touchUpInside)
        self.forwardButton.button.addTarget(self, action: #selector(self.forwardButtonPressed), for: .touchUpInside)
        self.shareButton.button.addTarget(self, action: #selector(self.shareButtonPressed), for: .touchUpInside)
        self.forwardWithoutSourceButton.button.addTarget(self, action: #selector(self.forwardWithoutSourceButtonPressed), for: .touchUpInside)
        self.broadcastButton.button.addTarget(self, action: #selector(self.broadcastButtonPressed), for: .touchUpInside)
        self.tagButton.button.addTarget(self, action: #selector(self.tagButtonPressed), for: .touchUpInside)
        self.tagEditButton.button.addTarget(self, action: #selector(self.tagButtonPressed), for: .touchUpInside)
    }
    
    deinit {
        self.canDeleteMessagesDisposable.dispose()
        self.nagramiXTransferDisposable.dispose()
    }
    
    private func updateActions() {
        self.nagramiXSelectionGeneration &+= 1
        let generation = self.nagramiXSelectionGeneration
        self.actions = nil
        if self.selectedMessages.isEmpty {
            self.nagramiXHasActionLayout = false
        }
        self.deleteButton.isEnabled = false
        self.reportButton.isEnabled = false
        self.tagButton.isEnabled = false
        self.tagEditButton.isEnabled = false
        self.forwardButton.isEnabled = !self.selectedMessages.isEmpty
        self.forwardButton.isImplicitlyDisabled = true
        self.shareButton.isImplicitlyDisabled = true
        self.nagramiXCanCopySelection = false
        self.forwardWithoutSourceButton.isImplicitlyDisabled = true
        self.broadcastButton.isImplicitlyDisabled = true
        self.nagramiXTransferDisposable.set(nil)
        self.canDeleteMessagesDisposable.set(nil)
        guard let context = self.context, !self.selectedMessages.isEmpty else {
            if let (width, leftInset, rightInset, bottomInset, additionalSideInsets, maxHeight, maxOverlayHeight, metrics, isSecondary, isMediaInputExpanded, deviceMetrics) = self.validLayout, let interfaceState = self.presentationInterfaceState {
                let _ = self.updateLayout(width: width, leftInset: leftInset, rightInset: rightInset, bottomInset: bottomInset, additionalSideInsets: additionalSideInsets, maxHeight: maxHeight, maxOverlayHeight: maxOverlayHeight, isSecondary: isSecondary, transition: .immediate, interfaceState: interfaceState, metrics: metrics, deviceMetrics: deviceMetrics, isMediaInputExpanded: isMediaInputExpanded)
            }
            return
        }
        let selectedIds = self.selectedMessages
        self.canDeleteMessagesDisposable.set((combineLatest(
            context.sharedContext.chatAvailableMessageActions(engine: context.engine, accountPeerId: context.account.peerId, messageIds: selectedIds, keepUpdated: true),
            self.nagramiXSelectedMessagesSignal(context: context, ids: selectedIds, keepUpdated: true)
        )
        |> deliverOnMainQueue
        |> mapToSignal { [weak self] nativeActions, messages -> Signal<(ChatAvailableMessageActions, Bool), NoError> in
            guard let self, messages.count == selectedIds.count else { return .single((nativeActions, false)) }
            let canCopy = self.interfaceInteraction?.canCopyMessagesWithoutSource?(messages) == true
            var messageMap: [EngineMessage.Id: EngineMessage] = [:]
            var peerMap: [EnginePeer.Id: EnginePeer] = [:]
            for message in messages {
                messageMap[message.id] = EngineMessage(message)
                for (id, peer) in message.peers { peerMap[id] = EnginePeer(peer) }
            }
            return context.sharedContext.chatAvailableMessageActions(engine: context.engine, accountPeerId: context.account.peerId, messageIds: selectedIds, messages: messageMap, peers: peerMap)
            |> map { resolvedActions in
                // Только возможности переноса берём от отображаемых snapshots.
                // Права удаления/жалоб/меток остаются от настоящего Postbox.
                var options = nativeActions.options
                options.subtract([.forward, .externalShare])
                options.formUnion(resolvedActions.options.intersection([.forward, .externalShare]))
                let actions = ChatAvailableMessageActions(options: options, banAuthor: nativeActions.banAuthor, banAuthors: nativeActions.banAuthors, disableDelete: nativeActions.disableDelete, isCopyProtected: nativeActions.isCopyProtected || resolvedActions.isCopyProtected, setTag: nativeActions.setTag, editTags: nativeActions.editTags)
                return (actions, canCopy)
            }
        }
        |> deliverOnMainQueue).startStrict(next: { [weak self] result in
            guard let self, self.nagramiXSelectionGeneration == generation, self.selectedMessages == selectedIds else { return }
            let (actions, canCopy) = result
            self.actions = actions
            self.nagramiXCanCopySelection = canCopy
            if let (width, leftInset, rightInset, bottomInset, additionalSideInsets, maxHeight, maxOverlayHeight, metrics, isSecondary, isMediaInputExpanded, deviceMetrics) = self.validLayout, let interfaceState = self.presentationInterfaceState {
                let _ = self.updateLayout(width: width, leftInset: leftInset, rightInset: rightInset, bottomInset: bottomInset, additionalSideInsets: additionalSideInsets, maxHeight: maxHeight, maxOverlayHeight: maxOverlayHeight, isSecondary: isSecondary, transition: .immediate, interfaceState: interfaceState, metrics: metrics, deviceMetrics: deviceMetrics, isMediaInputExpanded: isMediaInputExpanded)
            }
        }))
    }

    public func updateTheme(theme: PresentationTheme) {
        if self.theme !== theme {
            self.theme = theme
        }
    }
    
    @objc private func deleteButtonPressed() {
        self.interfaceInteraction?.deleteSelectedMessages(self.deleteButton.menuSourceView)
    }
    
    @objc private func reportButtonPressed() {
        self.interfaceInteraction?.reportSelectedMessages()
    }
    
    @objc private func forwardButtonPressed() {
        if let _ = self.presentationInterfaceState?.renderedPeer?.peer as? TelegramSecretChat {
            return
        }
        if let actions = self.actions, actions.isCopyProtected {
            self.interfaceInteraction?.displayCopyProtectionTip(self.forwardButton, false)
        } else if !self.forwardButton.isImplicitlyDisabled {
            self.interfaceInteraction?.forwardSelectedMessages()
        }
    }
    
    @objc private func shareButtonPressed() {
        if let _ = self.presentationInterfaceState?.renderedPeer?.peer as? TelegramSecretChat {
            return
        }
        if let actions = self.actions, actions.isCopyProtected {
            self.interfaceInteraction?.displayCopyProtectionTip(self.shareButton, true)
        } else if !self.shareButton.isImplicitlyDisabled {
            self.interfaceInteraction?.shareSelectedMessages()
        }
    }
    
    @objc private func tagButtonPressed() {
        guard let context = self.context else {
            return
        }
        
        if self.reactionOverlayContainer.reactionContextNode != nil {
            return
        }
        
        let reactionItems: Signal<[ReactionItem], NoError> = tagMessageReactions(context: context, subPeerId: self.presentationInterfaceState?.chatLocation.threadId.flatMap(EnginePeer.Id.init))
        
        let _ = (reactionItems
        |> take(1)
        |> deliverOnMainQueue).start(next: { [weak self] reactionItems in
            guard let self, let actions = self.actions, let context = self.context else {
                return
            }
            
            let presentationData = context.sharedContext.currentPresentationData.with { $0 }
            
            let reactionContextNode = ReactionContextNode(
                context: context,
                animationCache: context.animationCache,
                presentationData: presentationData,
                items: reactionItems.map { ReactionContextItem.reaction(item: $0, icon: .none) },
                selectedItems: actions.editTags,
                title: actions.editTags.isEmpty ? presentationData.strings.Chat_ReactionSelectionTitleAddTag : presentationData.strings.Chat_ReactionSelectionTitleEditTag,
                reactionsLocked: false,
                alwaysAllowPremiumReactions: false,
                allPresetReactionsAreAvailable: true,
                getEmojiContent: { animationCache, animationRenderer in
                    let mappedReactionItems: [EmojiComponentReactionItem] = reactionItems.map { reaction -> EmojiComponentReactionItem in
                        return EmojiComponentReactionItem(reaction: reaction.reaction.rawValue, file: reaction.stillAnimation)
                    }
                    
                    return EmojiPagerContentComponent.emojiInputData(
                        context: context,
                        animationCache: animationCache,
                        animationRenderer: animationRenderer,
                        isStandalone: false,
                        subject: .messageTag,
                        hasTrending: false,
                        topReactionItems: mappedReactionItems,
                        areUnicodeEmojiEnabled: false,
                        areCustomEmojiEnabled: true,
                        chatPeerId: context.account.peerId,
                        selectedItems: Set(),
                        premiumIfSavedMessages: false
                    )
                },
                isExpandedUpdated: { [weak self] transition in
                    guard let self else {
                        return
                    }
                    self.update(transition: transition)
                },
                requestLayout: { [weak self] transition in
                    guard let self else {
                        return
                    }
                    self.update(transition: transition)
                },
                requestUpdateOverlayWantsToBeBelowKeyboard: { [weak self] transition in
                    guard let self else {
                        return
                    }
                    self.update(transition: transition)
                }
            )
            reactionContextNode.reactionSelected = { [weak self] updateReaction, _ in
                guard let self, let context = self.context, let presentationInterfaceState = self.presentationInterfaceState, let actions = self.actions else {
                    return
                }
                
                self.interfaceInteraction?.cancelMessageSelection(.animated(duration: 0.4, curve: .spring))
                
                if actions.editTags.contains(updateReaction.reaction) {
                    var reactions = actions.editTags
                    reactions.remove(updateReaction.reaction)
                    let mappedUpdatedReactions = reactions.map { reaction -> UpdateMessageReaction in
                        switch reaction {
                        case let .builtin(value):
                            return .builtin(value)
                        case let .custom(fileId):
                            return .custom(fileId: fileId, file: nil)
                        case .stars:
                            return .stars
                        }
                    }
                    if let selectionState = presentationInterfaceState.interfaceState.selectionState {
                        context.engine.messages.setMessageReactions(ids: Array(selectionState.selectedIds), reactions: mappedUpdatedReactions)
                    } else {
                        context.engine.messages.setMessageReactions(ids: Array(self.selectedMessages), reactions: mappedUpdatedReactions)
                    }
                } else {
                    if let selectionState = presentationInterfaceState.interfaceState.selectionState {
                        context.engine.messages.addMessageReactions(ids: Array(selectionState.selectedIds), reactions: [updateReaction])
                    } else {
                        context.engine.messages.addMessageReactions(ids: Array(self.selectedMessages), reactions: [updateReaction])
                    }
                }
                
                self.reactionOverlayContainer.dismissReactionSelection()
            }
            reactionContextNode.displayTail = true
            reactionContextNode.forceTailToRight = true
            reactionContextNode.forceDark = false
            self.reactionOverlayContainer.reactionContextNode = reactionContextNode
            self.reactionOverlayContainer.addSubnode(reactionContextNode)
            
            self.update(transition: .immediate)
        })
    }
    
    private func nagramiXSelectedMessagesSignal(context: AccountContext, ids: Set<EngineMessage.Id>, keepUpdated: Bool = false) -> Signal<[EngineRawMessage], NoError> {
        let messageIds = ids.sorted()
        return combineLatest(
            context.engine.data.subscribe(EngineDataMap(messageIds.map(TelegramEngine.EngineData.Item.Messages.Message.init))),
            context.account.nagramiXMessageArchive.updates
        )
        |> take(keepUpdated ? Int.max : 1)
        |> deliverOnMainQueue
        |> map { messages, _ in
            return messageIds.compactMap { id -> EngineRawMessage? in
                return context.account.nagramiXMessageArchive.interactionMessage(id: id, liveMessage: (messages[id] ?? nil)?._asMessage())
            }
        }
    }

    @objc private func forwardWithoutSourceButtonPressed() {
        guard NagramiXTabSettings.current.showForwardWithoutAuthor else {
            return
        }
        self.nagramiXPerformSelectionTransfer(button: self.forwardWithoutSourceButton, action: self.interfaceInteraction?.forwardMessagesWithoutSource)
    }

    @objc private func broadcastButtonPressed() {
        guard NagramiXTabSettings.current.showBroadcastMessages else {
            return
        }
        self.nagramiXPerformSelectionTransfer(button: self.broadcastButton, action: self.interfaceInteraction?.copyMessagesWithoutSource)
    }

    private func nagramiXPerformSelectionTransfer(button: GlassButtonView, action: (([EngineRawMessage]) -> Void)?) {
        guard let context = self.context, let action, !self.selectedMessages.isEmpty else {
            return
        }
        // Custom copy actions use their payload eligibility, independently
        // of the native Repost/external-share protection flag.
        guard !button.isImplicitlyDisabled else {
            return
        }

        // Resolve fresh messages at the tap; never send a cached/deleted subset.
        let selectedIds = self.selectedMessages
        let generation = self.nagramiXSelectionGeneration
        self.nagramiXTransferDisposable.set((self.nagramiXSelectedMessagesSignal(context: context, ids: selectedIds)
        |> deliverOnMainQueue).startStrict(next: { [weak self, weak button] messages in
            guard let self, let button, self.nagramiXSelectionGeneration == generation, self.selectedMessages == selectedIds,
                messages.count == selectedIds.count,
                self.interfaceInteraction?.canCopyMessagesWithoutSource?(messages) == true else {
                return
            }
            if button === self.forwardWithoutSourceButton {
                guard NagramiXTabSettings.current.showForwardWithoutAuthor else { return }
            } else {
                guard NagramiXTabSettings.current.showBroadcastMessages else { return }
            }
            action(messages)
        }))
    }

    private func update(transition: ContainedViewLayoutTransition) {
        if let (width, leftInset, rightInset, bottomInset, additionalSideInsets, maxHeight, maxOverlayHeight, metrics, isSecondary, isMediaInputExpanded, deviceMetrics) = self.validLayout, let interfaceState = self.presentationInterfaceState {
            let _ = self.updateLayout(width: width, leftInset: leftInset, rightInset: rightInset, bottomInset: bottomInset, additionalSideInsets: additionalSideInsets, maxHeight: maxHeight, maxOverlayHeight: maxOverlayHeight, isSecondary: isSecondary, transition: transition, interfaceState: interfaceState, metrics: metrics, deviceMetrics: deviceMetrics, isMediaInputExpanded: isMediaInputExpanded)
        }
    }
    
    override public func updateLayout(width: CGFloat, leftInset: CGFloat, rightInset: CGFloat, bottomInset: CGFloat, additionalSideInsets: UIEdgeInsets, maxHeight: CGFloat, maxOverlayHeight: CGFloat, isSecondary: Bool, transition: ContainedViewLayoutTransition, interfaceState: ChatPresentationInterfaceState, metrics: LayoutMetrics, deviceMetrics: DeviceMetrics, isMediaInputExpanded: Bool) -> CGFloat {
        self.validLayout = (width, leftInset, rightInset, bottomInset, additionalSideInsets, maxHeight, maxOverlayHeight, metrics, isSecondary, isMediaInputExpanded, deviceMetrics)
        
        var leftInset = leftInset + 8.0
        var rightInset = rightInset + 8.0
        
        let compactBottomSideInset = self.compactBottomSideInset(bottomInset: bottomInset, deviceMetrics: deviceMetrics)
        leftInset += compactBottomSideInset
        rightInset += compactBottomSideInset
        
        let panelHeight = defaultHeight(metrics: metrics)
        
        if self.presentationInterfaceState != interfaceState {
            self.presentationInterfaceState = interfaceState
        }
        let freeContentEnabled = ContentSettings.default.nagramiXAllowsFreeContent
        if self.nagramiXFreeContentEnabled != freeContentEnabled {
            self.nagramiXFreeContentEnabled = freeContentEnabled
            self.updateActions()
        }
        let archiveOnlySelection = !self.selectedMessages.isEmpty && self.context.map { context in
            self.selectedMessages.allSatisfy { context.account.nagramiXMessageArchive.deletedMessage(id: $0) != nil }
        } == true
        if let actions = self.actions {
            self.nagramiXHasActionLayout = true
            self.tagButton.isEnabled = actions.setTag
            self.tagEditButton.isEnabled = actions.setTag
            self.deleteButton.isEnabled = false
            self.reportButton.isEnabled = false
            self.forwardButton.isImplicitlyDisabled = !archiveOnlySelection && !actions.options.contains(.forward)
            
            if self.peerMedia {
                self.deleteButton.isEnabled = !actions.options.intersection([.deleteLocally, .deleteGlobally]).isEmpty
            } else {
                self.deleteButton.isEnabled = !actions.disableDelete
            }
            if archiveOnlySelection {
                self.deleteButton.isEnabled = true
            }
            self.shareButton.isImplicitlyDisabled = actions.options.intersection(.forward).isEmpty || actions.options.intersection(.externalShare).isEmpty
            self.reportButton.isEnabled = !actions.options.intersection([.report]).isEmpty
            
            if self.peerMedia {
                self.deleteButton.isHidden = !self.deleteButton.isEnabled
            } else {
                self.deleteButton.isHidden = false
            }
            self.reportButton.isHidden = !self.reportButton.isEnabled
            
            if actions.setTag {
                if !actions.editTags.isEmpty {
                    self.tagButton.isHidden = true
                    self.tagEditButton.isHidden = false
                } else {
                    self.tagButton.isHidden = false
                    self.tagEditButton.isHidden = true
                }   
            } else {
                self.tagButton.isHidden = true
                self.tagEditButton.isHidden = true
            }
        } else {
            self.deleteButton.isEnabled = false
            self.reportButton.isEnabled = false
            self.forwardButton.isImplicitlyDisabled = true
            self.shareButton.isImplicitlyDisabled = true
            self.tagButton.isEnabled = false
            self.tagEditButton.isEnabled = false
            // A new selection temporarily has no actions while its current
            // permissions load. Do not remove/reinsert the visible slots.
            if !self.nagramiXHasActionLayout || self.selectedMessages.isEmpty {
                self.deleteButton.isHidden = self.peerMedia
                self.reportButton.isHidden = true
                self.tagButton.isHidden = true
                self.tagEditButton.isHidden = true
            }
        }
        
        let transferSettings = NagramiXTabSettings.current
        let copyBlocked = !self.nagramiXCanCopySelection
        self.forwardWithoutSourceButton.isHidden = !transferSettings.showForwardWithoutAuthor || self.interfaceInteraction?.forwardMessagesWithoutSource == nil || copyBlocked
        self.broadcastButton.isHidden = !transferSettings.showBroadcastMessages || self.interfaceInteraction?.copyMessagesWithoutSource == nil || copyBlocked
        let canCopySelection = self.nagramiXCanCopySelection
        self.forwardWithoutSourceButton.isEnabled = !self.selectedMessages.isEmpty
        self.broadcastButton.isEnabled = !self.selectedMessages.isEmpty
        self.forwardWithoutSourceButton.isImplicitlyDisabled = !canCopySelection
        self.broadcastButton.isImplicitlyDisabled = !canCopySelection

        if self.reportButton.isHidden || (self.peerMedia && self.deleteButton.isHidden && self.reportButton.isHidden) {
            if let peer = interfaceState.renderedPeer?.peer as? TelegramChannel, case .broadcast = peer.info {
                self.reportButton.isHidden = false
            } else if self.peerMedia {
                self.deleteButton.isHidden = false
            }
        }
        
        var width = width
        if additionalSideInsets.right > 0.0 {
            width -= additionalSideInsets.right
        }
        
        var tagButton: GlassButtonView?
        if !self.tagButton.isHidden {
            tagButton = self.tagButton
        } else if !self.tagEditButton.isHidden {
            tagButton = self.tagEditButton
        }
        
        var buttons: [GlassButtonView]
        if self.reportButton.isHidden {
            if let tagButton {
                buttons = [
                    self.deleteButton,
                    tagButton,
                    self.shareButton,
                    self.forwardButton
                ]
            } else {
                buttons = [
                    self.deleteButton,
                    self.shareButton,
                    self.forwardButton
                ]
            }
        } else if !self.deleteButton.isHidden {
            if let tagButton {
                buttons = [
                    self.deleteButton,
                    self.reportButton,
                    tagButton,
                    self.shareButton,
                    self.forwardButton
                ]
            } else {
                buttons = [
                    self.deleteButton,
                    self.reportButton,
                    self.shareButton,
                    self.forwardButton
                ]
            }
        } else {
            if let tagButton {
                buttons = [
                    self.deleteButton,
                    self.reportButton,
                    tagButton,
                    self.shareButton,
                    self.forwardButton
                ]
            } else {
                buttons = [
                    self.deleteButton,
                    self.reportButton,
                    self.shareButton,
                    self.forwardButton
                ]
            }
        }
        
        if !self.forwardWithoutSourceButton.isHidden {
            buttons.append(self.forwardWithoutSourceButton)
        }
        if !self.broadcastButton.isHidden {
            buttons.append(self.broadcastButton)
        }

        let buttonSize = CGSize(width: 40.0, height: 40.0)
        
        let availableWidth = max(0.0, width - leftInset - rightInset)
        let minimumContentWidth = buttonSize.width * CGFloat(buttons.count) + 8.0 * CGFloat(buttons.count - 1)
        let contentWidth = max(availableWidth, minimumContentWidth)
        let viewportFrame = CGRect(x: leftInset, y: 0.0, width: availableWidth, height: panelHeight)
        if self.buttonScrollView.frame != viewportFrame {
            self.buttonScrollView.layer.removeAnimation(forKey: "position")
            self.buttonScrollView.layer.removeAnimation(forKey: "bounds")
        }
        ContainedViewLayoutTransition.immediate.updateFrame(view: self.buttonScrollView, frame: viewportFrame)
        self.buttonScrollView.contentSize = CGSize(width: contentWidth, height: panelHeight)
        self.buttonScrollView.isScrollEnabled = contentWidth > availableWidth
        let maximumOffset = max(0.0, contentWidth - availableWidth)
        if self.buttonScrollView.contentOffset.x > maximumOffset {
            self.buttonScrollView.setContentOffset(CGPoint(x: maximumOffset, y: 0.0), animated: false)
        }
        let spacing: CGFloat = max(8.0, floor((contentWidth - buttonSize.width * CGFloat(buttons.count)) / CGFloat(buttons.count - 1)))
        var offset: CGFloat = 0.0
        for i in 0 ..< buttons.count {
            let button = buttons[i]
            let buttonFrame: CGRect
            if i == buttons.count - 1 {
                buttonFrame = CGRect(origin: CGPoint(x: contentWidth - buttonSize.width, y: 0.0), size: buttonSize)
            } else {
                buttonFrame = CGRect(origin: CGPoint(x: offset, y: 0.0), size: buttonSize)
            }
            // The panel itself keeps its native entrance/exit transition.
            // Its icons must not travel through neighbouring action slots.
            button.layer.removeAnimation(forKey: "position")
            button.layer.removeAnimation(forKey: "bounds")
            ContainedViewLayoutTransition.immediate.updateFrame(view: button, frame: buttonFrame)
            button.update(theme: interfaceState.theme, preferClearGlass: interfaceState.preferredGlassType == .clear, size: buttonFrame.size, transition: .immediate)
            
            offset += buttonSize.width + spacing
        }
        
        if let reactionContextNode = self.reactionOverlayContainer.reactionContextNode, let tagButton {
            let isFirstTime = reactionContextNode.bounds.isEmpty
            
            let size = CGSize(width: width, height: maxHeight)
            let reactionsAnchorRect = self.buttonScrollView.convert(tagButton.frame, to: self.view).offsetBy(dx: -54.0, dy: -(panelHeight - size.height) + 14.0)
            transition.updateFrame(node: reactionContextNode, frame: CGRect(origin: CGPoint(x: 0.0, y: panelHeight - size.height), size: size))
            reactionContextNode.updateLayout(size: size, insets: UIEdgeInsets(), anchorRect: reactionsAnchorRect, centerAligned: true, isCoveredByInput: false, isAnimatingOut: false, transition: transition)
            reactionContextNode.updateIsIntersectingContent(isIntersectingContent: true, transition: .immediate)
            if isFirstTime {
                reactionContextNode.animateIn(from: reactionsAnchorRect)
            }
        }
        
        return panelHeight
    }
    
    override public func minimalHeight(interfaceState: ChatPresentationInterfaceState, metrics: LayoutMetrics) -> CGFloat {
        return defaultHeight(metrics: metrics)
    }
}
