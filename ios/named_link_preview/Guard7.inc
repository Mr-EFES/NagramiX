import Foundation
import NagramiXCore
import NagramiXMediaSettings
import TelegramPresentationData
import AccountContext
import TelegramCore
import SwiftSignalKit
import Display
import TelegramPresentationData
import PresentationDataUtils
import TextFormat
import UndoUI
import ChatInterfaceState
import PremiumUI
import ReactionSelectionNode
import TopMessageReactions
import ChatMessagePaymentAlertController

enum NagramiXMessageTransferMode: Equatable {
    case forwardWithSource
    case copyAsNew
    case forwardWithoutSource
    case copyToSingleRecipient

    var copiesAsNew: Bool {
        return self == .copyAsNew || self == .copyToSingleRecipient
    }

    func selectionTitle(strings: PresentationStrings) -> String {
        switch self {
        case .forwardWithSource: return strings.nagramiXForwardWithAuthor
        case .forwardWithoutSource, .copyToSingleRecipient: return strings.nagramiXForwardWithoutAuthor
        case .copyAsNew: return strings.nagramiXBroadcastMessages
        }
    }

    var singleRecipient: Bool {
        return self == .forwardWithoutSource || self == .copyToSingleRecipient
    }
}

/// Native forwarding must keep a live server identity. Copy preparation can
/// still prefer its retained resource; the two choices are separate intents.
func nagramiXNativeForwardSource(_ live: EngineRawMessage?) -> EngineRawMessage? {
    guard let live, live.id.namespace == Namespaces.Message.Cloud,
          !live.flags.isSending, !live.flags.contains(.Failed),
          !live.containsSecretMedia, !live.nagramiXRequiresFreeContentCopy,
          !live.media.contains(where: { $0 is TelegramMediaExpiredContent }),
          !live.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) else { return nil }
    return live
}

func nagramiXArchivedCopyAlert(context: AccountContext) -> ViewController {
    let strings = context.sharedContext.currentPresentationData.with { $0 }.strings
    return textAlertController(context: context, title: nil, text: strings.nagramiXArchivedCopyUnavailable, actions: [TextAlertAction(type: .defaultAction, title: strings.Common_OK, action: {})])
}

extension ChatControllerImpl {
    func forwardMessages(messageIds: [EngineMessage.Id], options: ChatInterfaceForwardOptionsState? = nil, resetCurrent: Bool = false, transferMode: NagramiXMessageTransferMode = .forwardWithSource, nagramiXTransferTitle: String? = nil) {
        let selectionTitle = nagramiXTransferTitle ?? transferMode.selectionTitle(strings: self.presentationData.strings)
        let _ = (self.context.engine.data.get(EngineDataMap(
            messageIds.map(TelegramEngine.EngineData.Item.Messages.Message.init)
        ))
        |> deliverOnMainQueue).startStandalone(next: { [weak self] messages in
            guard let self else { return }
            let sortedMessages = messageIds.compactMap { id -> EngineRawMessage? in
                let live = (messages[id] ?? nil)?._asMessage()
                if transferMode == .forwardWithSource, let native = nagramiXNativeForwardSource(live) {
                    return native
                }
                return self.context.account.nagramiXMessageArchive.interactionMessage(id: id, liveMessage: live)
            }.sorted { $0.id < $1.id }
            guard sortedMessages.count == Set(messageIds).count, !sortedMessages.isEmpty else {
                self.present(nagramiXArchivedCopyAlert(context: self.context), in: .window(.root))
                return
            }
            let hasArchivedMessages = sortedMessages.contains(where: { $0.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) })
            let ownRecordingDraft = resetCurrent && sortedMessages.contains(where: { $0.nagramiXAllowsOwnViewOnceCopy(accountPeerId: self.context.account.peerId) })
            let transferMode = ownRecordingDraft && transferMode == .forwardWithSource ? NagramiXMessageTransferMode.forwardWithoutSource : transferMode
            // Telegram cannot forward IDs that were already deleted remotely.
            self.forwardMessages(messages: sortedMessages, options: options, resetCurrent: resetCurrent, transferMode: hasArchivedMessages ? (transferMode == .copyAsNew ? .copyAsNew : .copyToSingleRecipient) : transferMode, nagramiXTransferTitle: selectionTitle)
        })
    }

    func forwardMessages(messages: [EngineRawMessage], options: ChatInterfaceForwardOptionsState? = nil, resetCurrent: Bool, transferMode: NagramiXMessageTransferMode = .forwardWithSource, nagramiXProtectedMediaPrepared: Bool = false, nagramiXCopyObjectsPrepared: Bool = false, nagramiXTransferTitle: String? = nil) {
        let selectionTitle = nagramiXTransferTitle ?? transferMode.selectionTitle(strings: self.presentationData.strings)
        // Both custom actions share the no-author forward/copy transport plan.
        let transferMode: NagramiXMessageTransferMode = transferMode == .forwardWithoutSource ? .copyToSingleRecipient : transferMode
        if transferMode.copiesAsNew && !nagramiXCopyObjectsPrepared {
            let hasSpecialObjects = nagramiXMessagesRequiringCopy(messages).contains { message in
                message.media.contains { media in
                    if media is TelegramMediaImage || media is TelegramMediaFile || media is TelegramMediaContact || media is TelegramMediaMap || media is TelegramMediaWebpage { return false }
                    if let poll = media as? TelegramMediaPoll {
                        if case .quiz = poll.kind { return poll.correctAnswers?.isEmpty != false && poll.results.voters?.contains(where: { $0.isCorrect }) != true }
                        return false
                    }
                    return true
                }
            }
            if hasSpecialObjects {
                self.nagramiXResolveCopyObjects(messages: messages) { [weak self] resolved in
                    guard let self else { return }
                    guard let resolved else { self.present(nagramiXArchivedCopyAlert(context: self.context), in: .window(.root)); return }
                    self.forwardMessages(messages: resolved, options: options, resetCurrent: resetCurrent, transferMode: transferMode, nagramiXProtectedMediaPrepared: nagramiXProtectedMediaPrepared, nagramiXCopyObjectsPrepared: true, nagramiXTransferTitle: selectionTitle)
                }
                return
            }
        }
        let richCopySources = transferMode.copiesAsNew ? nagramiXMessagesRequiringCopy(messages) : messages
        if transferMode != .forwardWithSource && richCopySources.contains(where: { message in
            guard let richText = message.attributes.first(where: { $0 is RichTextMessageAttribute }) as? RichTextMessageAttribute else { return false }
            return !(richText.fullInstantPage ?? richText.instantPage).isComplete
        }) {
            self.nagramiXPrepareRichTextCopy(messages: richCopySources) { [weak self] resolvedCopies in
                var resolvedById: [EngineMessage.Id: EngineRawMessage] = [:]
                for message in resolvedCopies { resolvedById[message.id] = message }
                let resolvedMessages = messages.map { resolvedById[$0.id] ?? $0 }
                self?.forwardMessages(messages: resolvedMessages, options: options, resetCurrent: resetCurrent, transferMode: transferMode, nagramiXProtectedMediaPrepared: nagramiXProtectedMediaPrepared, nagramiXCopyObjectsPrepared: true, nagramiXTransferTitle: selectionTitle)
            }
            return
        }
        let nagramiXOwnViewOnceCopy = messages.contains(where: { $0.nagramiXAllowsOwnViewOnceCopy(accountPeerId: self.context.account.peerId) })
        // Repost remains a native forward; only the two copy actions gain this path.
        if nagramiXOwnViewOnceCopy && transferMode == .forwardWithSource {
            self.present(nagramiXArchivedCopyAlert(context: self.context), in: .window(.root))
            return
        }
        let nagramiXProtectedCopy = transferMode.copiesAsNew
        if nagramiXProtectedCopy {
            guard nagramiXCanCopyMessagesAsNew(messages, accountPeerId: self.context.account.peerId) else {
                self.present(nagramiXArchivedCopyAlert(context: self.context), in: .window(.root))
                return
            }
            guard nagramiXCanCopyMessagesAsNew(messages, accountPeerId: self.context.account.peerId) else {
                self.present(nagramiXArchivedCopyAlert(context: self.context), in: .window(.root))
                return
            }

        }
        // Both copy actions select recipients and send through the same prepared batch.
        // Only native reposts hand source IDs to a destination draft.
        let _ = self.presentVoiceMessageDiscardAlert(action: { [weak self] in
            guard let self else {
                return
            }

            var filter: ChatListNodePeersFilter = [.onlyWriteable, .excludeDisabled, .doNotSearchMessages]
            if transferMode.copiesAsNew && !nagramiXOwnViewOnceCopy {
                filter.insert(.nagramiXCopyDestinations)
            }
            if nagramiXOwnViewOnceCopy {
                filter.formUnion([.onlyPrivateChats, .excludeSavedMessages, .excludeSecretChats, .excludeBots])
            }
            var hasPublicPolls = false
            var hasPublicQuiz = false
            var hasTodo = false
            for message in messages {
                for media in message.media {
                    if media is TelegramMediaPoll {
                        filter.insert(.excludeSecretChats)
                    }
                    if let poll = media as? TelegramMediaPoll, case .public = poll.publicity {
                        hasPublicPolls = true
                        if case .quiz = poll.kind {
                            hasPublicQuiz = true
                        }
                        filter.insert(.excludeChannels)
                    } else if let _ = media as? TelegramMediaTodo {
                        hasTodo = true
                        filter.insert(.excludeChannels)
                    } else if let _ = media as? TelegramMediaPaidContent {
                        filter.insert(.excludeSecretChats)
                    }
                }
            }
            var attemptSelectionImpl: ((EnginePeer, ChatListDisabledPeerReason) -> Void)?
            var nagramiXCopyThreadIds: [EnginePeer.Id: Int64] = [:]
            let controller = self.context.sharedContext.makePeerSelectionController(PeerSelectionControllerParams(context: self.context, updatedPresentationData: self.updatedPresentationData, filter: filter, hasFilters: true, title: selectionTitle, attemptSelection: { peer, _, reason in
                attemptSelectionImpl?(peer, reason)
            }, multipleSelection: !transferMode.singleRecipient, multipleSelectionLimit: transferMode.singleRecipient ? 1 : nil, forwardedMessageIds: transferMode == .copyAsNew || nagramiXProtectedCopy ? [] : messages.map { $0.id }, selectForumThreads: true))
            if transferMode.copiesAsNew {
                controller.nagramiXConfigureCopySelection()
            }
            let context = self.context
            attemptSelectionImpl = { [weak self, weak controller] peer, reason in
                guard let strongSelf = self, let controller = controller else {
                    return
                }
                let presentationData = context.sharedContext.currentPresentationData.with { $0 }
                if hasPublicPolls {
                    if case let .channel(channel) = peer, case .broadcast = channel.info {
                        controller.present(textAlertController(context: context, title: nil, text: hasPublicQuiz ? presentationData.strings.Forward_ErrorPublicQuizDisabledInChannels : presentationData.strings.Forward_ErrorPublicPollDisabledInChannels, actions: [TextAlertAction(type: .defaultAction, title: presentationData.strings.Common_OK, action: {})]), in: .window(.root))
                        return
                    }
                } else if hasTodo {
                    if case let .channel(channel) = peer, case .broadcast = channel.info {
                        controller.present(textAlertController(context: context, title: nil, text: presentationData.strings.Forward_ErrorTodoDisabledInChannels, actions: [TextAlertAction(type: .defaultAction, title: presentationData.strings.Common_OK, action: {})]), in: .window(.root))
                        return
                    }
                }
                switch reason {
                case .generic:
                    controller.present(textAlertController(context: context, updatedPresentationData: strongSelf.updatedPresentationData, title: nil, text: presentationData.strings.Forward_ErrorDisabledForChat, actions: [TextAlertAction(type: .defaultAction, title: presentationData.strings.Common_OK, action: {})]), in: .window(.root))
                case .premiumRequired:
                    controller.forEachController { c in
                        if let c = c as? UndoOverlayController {
                            c.dismiss()
                        }
                        return true
                    }
                    
                    var hasAction = false
                    let premiumConfiguration = PremiumConfiguration.with(appConfiguration: strongSelf.context.currentAppConfiguration.with { $0 })
                    if !premiumConfiguration.isPremiumDisabled {
                        hasAction = true
                    }
                    
                    controller.present(UndoOverlayController(presentationData: presentationData, content: .premiumPaywall(title: nil, text: presentationData.strings.Chat_ToastMessagingRestrictedToPremium_Text(peer.compactDisplayTitle).string, customUndoText: hasAction ? presentationData.strings.Chat_ToastMessagingRestrictedToPremium_Action : nil, timeout: nil, linkAction: { _ in
                    }), elevatedLayout: false, animateInAsReplacement: true, action: { [weak controller] action in
                        guard let self, let controller else {
                            return false
                        }
                        if case .undo = action {
                            let premiumController = PremiumIntroScreen(context: self.context, source: .settings)
                            controller.push(premiumController)
                        }
                        return false
                    }), in: .current)
                }
            }
            var nagramiXCopyPreparationGeneration = 0
            var nagramiXCopyPreparing = false
            var nagramiXCopyLookingUp = false
            var nagramiXCopyDidCommit = false
            var nagramiXCopyLease: NagramiXCopyMediaLease?
            controller.multiplePeersSelected = { [weak self, weak controller] peers, peerMap, messageText, mode, forwardOptions, _ in
                guard !transferMode.copiesAsNew || (!nagramiXCopyPreparing && !nagramiXCopyLookingUp && !nagramiXCopyDidCommit) else { return }
                var recipientIds = Set<EnginePeer.Id>()
                let peers = peers.filter { recipientIds.insert($0.id).inserted }
                // Enforce the recipient contract before payments, scheduling or enqueue.
                guard !transferMode.singleRecipient || peers.count == 1 else {
                    return
                }
                guard !peers.isEmpty else { return }
                let destinationThreadIds = nagramiXCopyThreadIds.filter { recipientIds.contains($0.key) }
                if transferMode.copiesAsNew && peers.contains(where: { peer in
                    if case .community = peer { return true }
                    if case let .channel(channel) = peer, channel.isForumOrMonoForum {
                        return destinationThreadIds[peer.id] == nil
                    }
                    return false
                }) {
                    controller?.present(textAlertController(context: context, title: nil, text: context.sharedContext.currentPresentationData.with { $0 }.strings.Forward_ErrorDisabledForChat, actions: [TextAlertAction(type: .defaultAction, title: context.sharedContext.currentPresentationData.with { $0 }.strings.Common_OK, action: {})]), in: .window(.root))
                    return
                }
                let peerIds = peers.map { $0.id }
                var recipientsToStore = peerMap
                for peer in peers { recipientsToStore[peer.id] = peer }
                let beginSend: () -> Void = { [weak self, weak controller] in
                guard !transferMode.copiesAsNew || !nagramiXCopyDidCommit else { return }
                nagramiXCopyLookingUp = true
                let lookupReceived = Atomic<Bool>(value: false)
                // Search selections may exist only in the picker. Commit their peer data
                // before fees, input-peer resolution or enqueue can observe the destination.
                let _ = (combineLatest(recipientsToStore.values.map { peer in
                    context.engine.peers.ensurePeerIsLocallyAvailable(peer: peer)
                })
                |> take(1)
                |> mapToSignal { _ in context.engine.data.get(
                    EngineDataMap(
                        peerIds.map(TelegramEngine.EngineData.Item.Peer.SendPaidMessageStars.init(id:))
                    ),
                    EngineDataList(
                        peerIds.map(TelegramEngine.EngineData.Item.Peer.RenderedPeer.init(id:))
                    )
                ) }
                |> timeout(20.0, queue: Queue.mainQueue(), alternate: .complete())
                |> deliverOnMainQueue).start(next: { [weak self, weak controller] sendPaidMessageStars, renderedPeers in
                    _ = lookupReceived.swap(true)
                    nagramiXCopyLookingUp = false
                    guard let strongSelf = self else {
                        return
                    }
                    if nagramiXOwnViewOnceCopy {
                        let allowsMode: Bool
                        switch mode {
                        case .generic, .silent: allowsMode = true
                        case .schedule, .whenOnline: allowsMode = false
                        }
                        // Revalidate contacts/search selections and current fees as
                        // well as the list filter before staging, payment or enqueue.
                        let allowsPeers = peers.allSatisfy { peer in
                            nagramiXAllowsOwnViewOnceDestination(peer, accountPeerId: context.account.peerId, requiresPayment: (sendPaidMessageStars[peer.id] ?? nil) != nil)
                        }
                        guard allowsMode && allowsPeers else {
                            controller?.present(textAlertController(context: context, title: nil, text: strongSelf.presentationData.strings.Forward_ErrorDisabledForChat, actions: [TextAlertAction(type: .defaultAction, title: strongSelf.presentationData.strings.Common_OK, action: {})]), in: .window(.root))
                            return
                        }
                    }
                    let renderedPeers = renderedPeers.compactMap({ $0 })
                    
                    // Expanding a paid bundle or a round-video caption can
                    // create more than one new message. Confirm the real cost.
                    let copyCount = transferMode.copiesAsNew ? nagramiXMessagesWithoutAuthor(messages, hideCaptions: forwardOptions?.hideCaptions == true, accountPeerId: context.account.peerId)?.count : nil
                    var count = Int32(clamping: copyCount ?? messages.count)
                    if messageText.string.count > 0 {
                        count += Int32(clamping: breakChatInputText(trimChatInputText(convertMarkdownToAttributes(messageText))).filter { $0.length != 0 }.count)
                    }
                    var totalAmount: StarsAmount = .zero
                    var chargingPeers: [EngineRenderedPeer] = []
                    for peer in renderedPeers {
                        if let maybeAmount = sendPaidMessageStars[peer.peerId], let amount = maybeAmount {
                            totalAmount = totalAmount + amount
                            chargingPeers.append(peer)
                        }
                    }
                                        
                    let proceed = { [weak self, weak controller] in
                        guard let strongSelf = self, let strongController = controller,
                              strongController.navigationController != nil else {
                            return
                        }

                        // A settings change while choosing recipients/payment/date
                        // must not silently switch the recording's lifetime policy.
                        guard !transferMode.copiesAsNew || (nagramiXCanCopyMessagesAsNew(messages, accountPeerId: strongSelf.context.account.peerId) && messages.contains(where: { $0.nagramiXAllowsOwnViewOnceCopy(accountPeerId: strongSelf.context.account.peerId) }) == nagramiXOwnViewOnceCopy) else {
                            strongSelf.present(nagramiXArchivedCopyAlert(context: strongSelf.context), in: .window(.root))
                            return
                        }
                        var nagramiXRecipientCopies: NagramiXRecipientCopyBatch?
                        var result: [EnqueueMessage] = []
                        if messageText.string.count > 0 {
                            let inputText = convertMarkdownToAttributes(messageText)
                            for text in breakChatInputText(trimChatInputText(inputText)) {
                                if text.length != 0 {
                                    var attributes: [EngineMessage.Attribute] = []
                                    let entities = generateTextEntities(text.string, enabledTypes: .all, currentEntities: generateChatInputTextEntities(text))
                                    if !entities.isEmpty {
                                        attributes.append(TextEntitiesMessageAttribute(entities: entities))
                                    }
                                    result.append(.message(text: text.string, attributes: attributes, inlineStickers: [:], mediaReference: nil, threadId: transferMode.copiesAsNew ? nil : strongSelf.chatLocation.threadId, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: nil, correlationId: nil, bubbleUpEmojiOrStickersets: []))
                                }
                            }
                        }
                        
                        switch transferMode {
                        case .forwardWithSource, .forwardWithoutSource:
                            var attributes: [EngineMessage.Attribute] = []
                            attributes.append(ForwardOptionsMessageAttribute(hideNames: transferMode.singleRecipient || forwardOptions?.hideNames == true, hideCaptions: forwardOptions?.hideCaptions == true))
                            result.append(contentsOf: messages.map { message -> EnqueueMessage in
                                return .forward(source: message.id, threadId: nil, grouping: .auto, attributes: attributes, correlationId: nil)
                            })
                        case .copyAsNew, .copyToSingleRecipient:
                            guard let batch = nagramiXPrepareRecipientCopies(messages, account: strongSelf.context.account, recipientCount: peers.count, hideCaptions: forwardOptions?.hideCaptions == true, forceLocalMedia: false, accountPeerId: strongSelf.context.account.peerId) else {
                                nagramiXCopyLease?.dispose(); nagramiXCopyLease = nil
                                strongSelf.present(nagramiXArchivedCopyAlert(context: strongSelf.context), in: .window(.root))
                                return
                            }
                            nagramiXRecipientCopies = batch
                            result.append(contentsOf: batch.recipientMessages[0])
                        }
                        
                        // Selecting a date can still be cancelled. Keep the picker
                        // and its stable selection until commit actually begins.
                        if !transferMode.copiesAsNew { strongController.dismiss() }
                        var nagramiXCopyCommitted = false
                        let commit: ([EnqueueMessage]) -> Void = { result in
                            guard let strongSelf = self else {
                                return
                            }
                            if transferMode.copiesAsNew {
                                guard !nagramiXCopyCommitted && !nagramiXCopyDidCommit else { return }
                                guard !transferMode.copiesAsNew || (nagramiXCanCopyMessagesAsNew(messages, accountPeerId: strongSelf.context.account.peerId) && messages.contains(where: { $0.nagramiXAllowsOwnViewOnceCopy(accountPeerId: strongSelf.context.account.peerId) }) == nagramiXOwnViewOnceCopy) else {
                                    strongSelf.present(nagramiXArchivedCopyAlert(context: strongSelf.context), in: .window(.root))
                                    return
                                }
                                nagramiXCopyCommitted = true
                                nagramiXCopyDidCommit = true
                                nagramiXCopyLease?.dispose(); nagramiXCopyLease = nil
                                strongController.dismiss()
                            }
                            var result = result
                            
                            strongSelf.updateChatPresentationInterfaceState(animated: false, interactive: true, { $0.updatedInterfaceState({ $0.withoutSelectionState() }).updatedSearch(nil) })
                            
                            var correlationIds: [Int64] = []
                            for i in 0 ..< result.count {
                                let correlationId = Int64.random(in: Int64.min ... Int64.max)
                                correlationIds.append(correlationId)
                                result[i] = result[i].withUpdatedCorrelationId(correlationId)
                            }
                            
                            let targetPeersShouldDivertSignals: [Signal<(EnginePeer, Bool), NoError>] = peers.map { peer -> Signal<(EnginePeer, Bool), NoError> in
                                return strongSelf.shouldDivertMessagesToScheduled(targetPeer: peer, messages: result)
                                |> map { shouldDivert -> (EnginePeer, Bool) in
                                    return (peer, shouldDivert)
                                }
                            }
                            let targetPeersShouldDivert: Signal<[(EnginePeer, Bool)], NoError> = combineLatest(targetPeersShouldDivertSignals) |> take(1)
                            let _ = (targetPeersShouldDivert
                            |> deliverOnMainQueue).startStandalone(next: { targetPeersShouldDivert in
                                guard let strongSelf = self else {
                                    return
                                }
                                
                                // A native destination diversion must not silently
                                // turn a one-shot recording into a scheduled message.
                                if nagramiXOwnViewOnceCopy && targetPeersShouldDivert.contains(where: { $0.1 }) {
                                    strongSelf.present(textAlertController(context: strongSelf.context, title: nil, text: strongSelf.presentationData.strings.Forward_ErrorDisabledForChat, actions: [TextAlertAction(type: .defaultAction, title: strongSelf.presentationData.strings.Common_OK, action: {})]), in: .window(.root))
                                    return
                                }
                                var displayConvertingTooltip = false
                                
                                guard !transferMode.copiesAsNew || (nagramiXCanCopyMessagesAsNew(messages, accountPeerId: strongSelf.context.account.peerId) && messages.contains(where: { $0.nagramiXAllowsOwnViewOnceCopy(accountPeerId: strongSelf.context.account.peerId) }) == nagramiXOwnViewOnceCopy) else {
                                    strongSelf.present(nagramiXArchivedCopyAlert(context: strongSelf.context), in: .window(.root))
                                    return
                                }
                                var displayPeers: [EnginePeer] = []
                                var copyEnqueueSignals: [Signal<[EngineMessage.Id?], NoError>] = []
                                var copyExpectedCounts: [Int] = []
                                var copyRecipientCorrelations: [[Int64]] = []
                                for (destinationIndex, target) in targetPeersShouldDivert.enumerated() {
                                    let (peer, shouldDivert) = target
                                    var peerMessages = result
                                    var peerCorrelations = correlationIds
                                    if let batch = nagramiXRecipientCopies {
                                        guard let recipientMessages = batch.messages(forRecipientAt: destinationIndex, template: result) else {
                                            strongSelf.present(nagramiXArchivedCopyAlert(context: strongSelf.context), in: .window(.root))
                                            return
                                        }
                                        var recipientCorrelationIds: [Int64] = []
                                        peerMessages = recipientMessages.map { message in
                                            let id = Int64.random(in: Int64.min ... Int64.max)
                                            recipientCorrelationIds.append(id)
                                            return message.withUpdatedCorrelationId(id)
                                        }
                                        peerCorrelations = recipientCorrelationIds
                                        if peer.id == strongSelf.context.account.peerId { correlationIds = recipientCorrelationIds }
                                    }
                                    if transferMode.copiesAsNew, let threadId = destinationThreadIds[peer.id] {
                                        peerMessages = peerMessages.map { $0.withUpdatedThreadId(threadId) }
                                        if case let .channel(channel) = peer, channel.isForum {
                                            // A local threadId alone does not create the RPC reply target.
                                            // Copies are new messages: explicitly address the chosen topic,
                                            // just as native forwarding does when converting to .message.
                                            let replySubject = EngineMessageReplySubject(messageId: EngineMessage.Id(peerId: peer.id, namespace: Namespaces.Message.Cloud, id: Int32(clamping: threadId)), quote: nil, innerSubject: nil)
                                            peerMessages = peerMessages.map { $0.withUpdatedReplyToMessageId(replySubject) }
                                        }
                                    }
                                    if shouldDivert {
                                        displayConvertingTooltip = true
                                        peerMessages = peerMessages.map { message -> EnqueueMessage in
                                            return message.withUpdatedAttributes { attributes in
                                                var attributes = attributes
                                                attributes.removeAll(where: { $0 is OutgoingScheduleInfoMessageAttribute })
                                                attributes.append(OutgoingScheduleInfoMessageAttribute(scheduleTime: Int32(Date().timeIntervalSince1970) + 10 * 24 * 60 * 60, repeatPeriod: nil))
                                                return attributes
                                            }
                                        }
                                    }
                                    
                                    if let maybeAmount = sendPaidMessageStars[peer.id], let amount = maybeAmount {
                                        peerMessages = peerMessages.map { message -> EnqueueMessage in
                                            return message.withUpdatedAttributes { attributes in
                                                var attributes = attributes
                                                attributes.append(PaidStarsMessageAttribute(stars: amount, postponeSending: false))
                                                return attributes
                                            }
                                        }
                                    }
                                    
                                    let enqueue = enqueueMessages(account: strongSelf.context.account, peerId: peer.id, messages: peerMessages) |> deliverOnMainQueue
                                    if nagramiXRecipientCopies != nil {
                                        copyEnqueueSignals.append(enqueue)
                                        copyExpectedCounts.append(peerMessages.count)
                                        copyRecipientCorrelations.append(peerCorrelations)
                                    } else {
                                        let _ = enqueue.startStandalone(next: { messageIds in
                                            if let strongSelf = self {
                                                let signals: [Signal<Bool, NoError>] = messageIds.compactMap({ id -> Signal<Bool, NoError>? in
                                                    guard let id = id else {
                                                        return nil
                                                    }
                                                    return strongSelf.context.account.pendingMessageManager.pendingMessageStatus(id)
                                                    |> mapToSignal { status, _ -> Signal<Bool, NoError> in
                                                        if status != nil {
                                                            return .never()
                                                        } else {
                                                            return .single(true)
                                                        }
                                                    }
                                                    |> take(1)
                                                })
                                                if strongSelf.shareStatusDisposable == nil {
                                                    strongSelf.shareStatusDisposable = MetaDisposable()
                                                }
                                                strongSelf.shareStatusDisposable?.set((combineLatest(signals)
                                                |> deliverOnMainQueue).startStrict())
                                            }
                                        })
                                    }
                                    
                                    if case let .secretChat(secretPeer) = peer {
                                        if let peer = peerMap[secretPeer.regularPeerId] {
                                            displayPeers.append(peer)
                                        }
                                    } else {
                                        displayPeers.append(peer)
                                    }
                                }
                                
                                let showForwardResult: () -> Void = { [weak self] in
                                    guard let strongSelf = self else { return }
                                    let presentationData = strongSelf.context.sharedContext.currentPresentationData.with { $0 }
                                    let text: String
                                    var savedMessages = false
                                    if displayPeers.count == 1, let peerId = displayPeers.first?.id, peerId == strongSelf.context.account.peerId {
                                        text = messages.count == 1 ? presentationData.strings.Conversation_ForwardTooltip_SavedMessages_One : presentationData.strings.Conversation_ForwardTooltip_SavedMessages_Many
                                        savedMessages = true
                                    } else {
                                        if displayPeers.count == 1, let peer = displayPeers.first {
                                            var peerName = peer.id == strongSelf.context.account.peerId ? presentationData.strings.DialogList_SavedMessages : peer.displayTitle(strings: presentationData.strings, displayOrder: presentationData.nameDisplayOrder)
                                            peerName = peerName.replacingOccurrences(of: "**", with: "")
                                            text = messages.count == 1 ? presentationData.strings.Conversation_ForwardTooltip_Chat_One(peerName).string : presentationData.strings.Conversation_ForwardTooltip_Chat_Many(peerName).string
                                        } else if displayPeers.count == 2, let firstPeer = displayPeers.first, let secondPeer = displayPeers.last {
                                            var firstPeerName = firstPeer.id == strongSelf.context.account.peerId ? presentationData.strings.DialogList_SavedMessages : firstPeer.displayTitle(strings: presentationData.strings, displayOrder: presentationData.nameDisplayOrder)
                                            firstPeerName = firstPeerName.replacingOccurrences(of: "**", with: "")
                                            var secondPeerName = secondPeer.id == strongSelf.context.account.peerId ? presentationData.strings.DialogList_SavedMessages : secondPeer.displayTitle(strings: presentationData.strings, displayOrder: presentationData.nameDisplayOrder)
                                            secondPeerName = secondPeerName.replacingOccurrences(of: "**", with: "")
                                            text = messages.count == 1 ? presentationData.strings.Conversation_ForwardTooltip_TwoChats_One(firstPeerName, secondPeerName).string : presentationData.strings.Conversation_ForwardTooltip_TwoChats_Many(firstPeerName, secondPeerName).string
                                        } else if let peer = displayPeers.first {
                                            var peerName = peer.displayTitle(strings: presentationData.strings, displayOrder: presentationData.nameDisplayOrder)
                                            peerName = peerName.replacingOccurrences(of: "**", with: "")
                                            text = messages.count == 1 ? presentationData.strings.Conversation_ForwardTooltip_ManyChats_One(peerName, "\(displayPeers.count - 1)").string : presentationData.strings.Conversation_ForwardTooltip_ManyChats_Many(peerName, "\(displayPeers.count - 1)").string
                                        } else {
                                            text = ""
                                        }
                                    }
                                
                                    let reactionItems: Signal<[ReactionItem], NoError>
                                    if savedMessages && messages.count > 0 {
                                        reactionItems = tagMessageReactions(context: strongSelf.context, subPeerId: nil)
                                    } else {
                                        reactionItems = .single([])
                                    }
                                
                                    let _ = (reactionItems
                                    |> deliverOnMainQueue).startStandalone(next: { [weak strongSelf] reactionItems in
                                        guard let strongSelf else {
                                            return
                                        }
                                    
                                        strongSelf.present(UndoOverlayController(presentationData: presentationData, content: .forward(savedMessages: savedMessages, text: text), elevatedLayout: false, position: savedMessages && messages.count > 0 ? .top : .bottom, animateInAsReplacement: true, action: { action in
                                            if savedMessages, let self, action == .info {
                                                let _ = (self.context.engine.data.get(TelegramEngine.EngineData.Item.Peer.Peer(id: self.context.account.peerId))
                                                         |> deliverOnMainQueue).start(next: { [weak self] peer in
                                                    guard let self, let peer else {
                                                        return
                                                    }
                                                    guard let navigationController = self.navigationController as? NavigationController else {
                                                        return
                                                    }
                                                    self.context.sharedContext.navigateToChatController(NavigateToChatControllerParams(navigationController: navigationController, context: self.context, chatLocation: .peer(peer), forceOpenChat: true))
                                                })
                                            }
                                            return false
                                        }, additionalView: (savedMessages && messages.count > 0) ? chatShareToSavedMessagesAdditionalView(strongSelf, reactionItems: reactionItems, correlationIds: correlationIds) : nil), in: .current)
                                    })
                                
                                    if displayConvertingTooltip {
                                    }
                                }
                                if let batch = nagramiXRecipientCopies {
                                    // All recipients are prepared. Start native enqueue for
                                    // every destination together, never await another upload.
                                    batch.commit()
                                    let copyEnqueueResults: Signal<[[EngineMessage.Id?]], NoError> = combineLatest(copyEnqueueSignals)
                                    let _ = (copyEnqueueResults
                                    |> take(1)
                                    |> deliverOnMainQueue).startStandalone(next: { [weak self] (accepted: [[EngineMessage.Id?]]) in
                                        self?.nagramiXHandleCopyEnqueued(accepted, peers: peers, copyExpectedCounts: copyExpectedCounts, copyRecipientCorrelations: copyRecipientCorrelations, showForwardResult: showForwardResult)
                                    })
                                } else {
                                    showForwardResult()
                                }
                            })
                        }
                        
                        let transformForSend: (Bool, Int32?, Int32?) -> [EnqueueMessage] = { [weak self] silentPosting, scheduleTime, repeatPeriod in
                            guard let strongSelf = self else {
                                return []
                            }
                            let transformedMessages = strongSelf.transformEnqueueMessages(result, silentPosting: silentPosting, scheduleTime: scheduleTime, repeatPeriod: repeatPeriod)
                            guard transferMode.copiesAsNew else {
                                return transformedMessages
                            }
                            // The stock transform also applies the SOURCE chat's reply,
                            // topic, send-as, suggested post and paid-message defaults.
                            // Copies keep their content and only take the selected send mode;
                            // destination topic/payment handling remains in commit below.
                            return zip(result, transformedMessages).map { original, transformed in
                                let sendAttributes = transformed.attributes.filter { $0 is NotificationInfoMessageAttribute || $0 is OutgoingScheduleInfoMessageAttribute }
                                return original.withUpdatedAttributes { attributes in
                                    return attributes.filter { !($0 is NotificationInfoMessageAttribute) && !($0 is OutgoingScheduleInfoMessageAttribute) } + sendAttributes
                                }
                            }
                        }
                        switch mode {
                        case .generic:
                            commit(result)
                        case .silent:
                            commit(transformForSend(true, nil, nil))
                        case .schedule:
                            strongSelf.presentScheduleTimePicker(completion: { [weak self] timeResult in
                                if self != nil {
                                    commit(transformForSend(timeResult.silentPosting, timeResult.time, timeResult.repeatPeriod))
                                }
                            })
                        case .whenOnline:
                            commit(transformForSend(strongSelf.presentationInterfaceState.interfaceState.silentPosting, scheduleWhenOnlineTimestamp, nil))
                        }
                    }
                    
                    if totalAmount.value > 0 {
                        let controller = chatMessagePaymentAlertController(
                            context: nil,
                            presentationData: strongSelf.presentationData,
                            updatedPresentationData: nil,
                            peers: chargingPeers,
                            count: count,
                            amount: totalAmount,
                            totalAmount: totalAmount,
                            hasCheck: false,
                            navigationController: strongSelf.navigationController as? NavigationController,
                            completion: { _ in
                                proceed()
                            }
                        )
                        strongSelf.present(controller, in: .window(.root))
                    } else {
                        proceed()
                    }
                }, completed: { [weak self, weak controller] in
                    guard !lookupReceived.swap(true) else { return }
                    nagramiXCopyLookingUp = false
                    nagramiXCopyLease?.dispose(); nagramiXCopyLease = nil
                    if transferMode.copiesAsNew, let self {
                        controller?.present(nagramiXArchivedCopyAlert(context: self.context), in: .window(.root))
                    }
                })
                }
                if transferMode.copiesAsNew && !nagramiXProtectedMediaPrepared {
                    guard let self, let controller else { return }
                    nagramiXCopyPreparing = true
                    nagramiXCopyPreparationGeneration += 1
                    let generation = nagramiXCopyPreparationGeneration
                    self.nagramiXPrepareCopyUpload(messages: messages, present: { [weak controller] progress in
                        controller?.present(progress, in: .window(.root))
                    }) { [weak self, weak controller] lease, cancelled in
                        guard generation == nagramiXCopyPreparationGeneration else { lease?.dispose(); return }
                        nagramiXCopyPreparing = false
                        guard let controller, controller.navigationController != nil else { lease?.dispose(); return }
                        guard let lease else {
                            if !cancelled, let self {
                                let strings = self.presentationData.strings
                                controller.present(textAlertController(context: context, title: nil, text: strings.nagramiXArchivedCopyUnavailable, actions: [
                                    TextAlertAction(type: .genericAction, title: strings.Common_Cancel, action: {}),
                                    TextAlertAction(type: .defaultAction, title: strings.nagramiXArchiveStorageRetry, action: { [weak controller] in controller?.multiplePeersSelected?(peers, peerMap, messageText, mode, forwardOptions, nil) })
                                ]), in: .window(.root))
                            }
                            return
                        }
                        nagramiXCopyLease = lease
                        beginSend()
                    }
                } else {
                    beginSend()
                }
            }
            controller.peerSelected = { [weak self, weak controller] peer, threadId in
                guard let strongSelf = self, let strongController = controller else {
                    return
                }
                let peerId = peer.id
                let accountPeerId = strongSelf.context.account.peerId

                if transferMode.copiesAsNew {
                    // Assign nil as well: a previous topic may not leak into a
                    // new selection of this destination.
                    nagramiXCopyThreadIds[peer.id] = threadId
                    strongController.nagramiXSelectCopyRecipient(peer, threadId: threadId)
                    return
                }

                if resetCurrent {
                    strongSelf.updateChatPresentationInterfaceState(animated: false, interactive: true, { $0.updatedInterfaceState({ $0.withUpdatedForwardMessageIds(nil).withUpdatedForwardOptionsState(nil) }) })
                }
                
                var isPinnedMessages = false
                if case .pinnedMessages = strongSelf.presentationInterfaceState.subject {
                    isPinnedMessages = true
                }
                
                var hasNotOwnMessages = false
                for message in messages {
                    if message.id.peerId == accountPeerId && message.forwardInfo == nil {
                    } else {
                        hasNotOwnMessages = true
                    }
                }
                
                if case .peer(peerId) = strongSelf.chatLocation, strongSelf.parentController == nil, !isPinnedMessages, !strongSelf.nagramiXReadHistoryDisabled, (!transferMode.singleRecipient || strongSelf.chatLocation.threadId == threadId) {
                    strongSelf.updateChatPresentationInterfaceState(animated: false, interactive: true, { $0.updatedInterfaceState({ $0.withUpdatedForwardMessageIds(messages.map { $0.id }).withUpdatedForwardOptionsState(ChatInterfaceForwardOptionsState(hideNames: transferMode.singleRecipient || !hasNotOwnMessages, hideCaptions: false, unhideNamesOnCaptionChange: false)).withoutSelectionState() }).updatedSearch(nil) })
                    strongSelf.updateItemNodesSearchTextHighlightStates()
                    strongSelf.searchResultsController = nil
                    strongController.dismiss()
                } else {
                    if let navigationController = strongSelf.navigationController as? NavigationController {
                        for controller in navigationController.viewControllers {
                            if let maybeChat = controller as? ChatControllerImpl {
                                if case .peer(peerId) = maybeChat.chatLocation {
                                    var isChatPinnedMessages = false
                                    if case .pinnedMessages = maybeChat.presentationInterfaceState.subject {
                                        isChatPinnedMessages = true
                                    }
                                    if !isChatPinnedMessages, !maybeChat.nagramiXReadHistoryDisabled, (!transferMode.singleRecipient || maybeChat.chatLocation.threadId == threadId) {
                                        maybeChat.updateChatPresentationInterfaceState(animated: false, interactive: true, { $0.updatedInterfaceState({ state in
                                            var state = state.withUpdatedForwardMessageIds(messages.map { $0.id }).withoutSelectionState()
                                            if transferMode.singleRecipient {
                                                state = state.withUpdatedForwardOptionsState(ChatInterfaceForwardOptionsState(hideNames: true, hideCaptions: false, unhideNamesOnCaptionChange: false))
                                            }
                                            return state
                                        }) })
                                        strongSelf.dismiss()
                                        strongController.dismiss()
                                        return
                                    }
                                }
                            }
                        }
                    }

                    let _ = (ChatInterfaceState.update(engine: strongSelf.context.engine, peerId: peerId, threadId: threadId, { currentState in
                        return currentState.withUpdatedForwardMessageIds(messages.map { $0.id }).withUpdatedForwardOptionsState(ChatInterfaceForwardOptionsState(hideNames: transferMode.singleRecipient || !hasNotOwnMessages, hideCaptions: false, unhideNamesOnCaptionChange: false))
                    })
                    |> deliverOnMainQueue).startStandalone(completed: {
                        if let strongSelf = self {
                            let proceed: (ChatController) -> Void = { chatController in
                                strongSelf.updateChatPresentationInterfaceState(animated: false, interactive: true, { $0.updatedInterfaceState({ $0.withoutSelectionState() }) })
                                
                                let navigationController: NavigationController?
                                if let parentController = strongSelf.parentController {
                                    navigationController = (parentController.navigationController as? NavigationController)
                                } else {
                                    navigationController = strongSelf.effectiveNavigationController
                                }
                                
                                if let navigationController = navigationController {
                                    var viewControllers = navigationController.viewControllers
                                    if threadId != nil {
                                        viewControllers.insert(chatController, at: viewControllers.count - 2)
                                    } else {
                                        viewControllers.insert(chatController, at: viewControllers.count - 1)
                                    }
                                    navigationController.setViewControllers(viewControllers, animated: false)
                                    
                                    strongSelf.controllerNavigationDisposable.set((chatController.ready.get()
                                    |> SwiftSignalKit.filter { $0 }
                                    |> take(1)
                                    |> deliverOnMainQueue).startStrict(next: { [weak navigationController] _ in
                                        viewControllers.removeAll(where: { $0 is PeerSelectionController })
                                        navigationController?.setViewControllers(viewControllers, animated: true)
                                    }))
                                }
                            }
                            if let threadId = threadId {
                                let _ = (strongSelf.context.sharedContext.chatControllerForForumThread(context: strongSelf.context, peerId: peerId, threadId: threadId)
                                |> deliverOnMainQueue).startStandalone(next: { chatController in
                                    proceed(chatController)
                                })
                            } else {
                                proceed(ChatControllerImpl(context: strongSelf.context, chatLocation: .peer(id: peerId)))
                            }
                        }
                    })
                }
            }
            self.chatDisplayNode.dismissInput()
            self.effectiveNavigationController?.pushViewController(controller)
        })
    }
}
