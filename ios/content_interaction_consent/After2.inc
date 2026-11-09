import Foundation
import NagramiXMediaSettings
import Postbox
internal import TelegramApi
import SwiftSignalKit

// Suppress only proven incoming temporary content. Ordinary history reading
// remains native, except the separately approved secret-chat history policy.
func nagramiXShouldSuppressViewOnceReceipt(_ message: Message) -> Bool {
    return message.flags.contains(.Incoming) && nagramiXCanRetainTemporaryMessage(message)
}

func nagramiXShouldSuppressTemporaryReceipt(transaction: Transaction, postbox: Postbox, messageId: MessageId, allowExplicitOpen: Bool = false) -> Bool {
    if allowExplicitOpen, NagramiXMessageArchive.forPostbox(postbox)?.hasExplicitTemporaryMediaOpen(id: messageId) == true { return false }
    guard nagramiXTemporaryMessagesEnabled() else { return false }
    if let message = transaction.getMessage(messageId), nagramiXShouldSuppressViewOnceReceipt(message) { return true }
    // A queued ID can already be represented only by the local retained record.
    // An unknown ordinary ID is not suppressed without that provenance.
    let archive = NagramiXMessageArchive.forPostbox(postbox)
    return archive?.shouldSuppressTemporaryContentReceipt(id: messageId) == true
        || (!allowExplicitOpen && archive?.hasExplicitTemporaryMediaOpen(id: messageId) == true)
}

func _internal_markMessageContentAsConsumedInteractively(postbox: Postbox, messageId: MessageId) -> Signal<Void, NoError> {
    return postbox.transaction { transaction -> Void in
        if let message = transaction.getMessage(messageId), message.flags.contains(.Incoming) {
            NagramiXMessageArchive.forPostbox(postbox)?.captureTemporaryBeforeViewing(message: message)
            if nagramiXShouldSuppressTemporaryReceipt(transaction: transaction, postbox: postbox, messageId: messageId) { return }
            var updateMessage = false
            var updatedAttributes = message.attributes
            var updatedTags = message.tags
            
            for i in 0 ..< updatedAttributes.count {
                if let attribute = updatedAttributes[i] as? ConsumableContentMessageAttribute {
                    if !attribute.consumed {
                        updatedAttributes[i] = ConsumableContentMessageAttribute(consumed: true)
                        updateMessage = true
                        
                        if message.id.peerId.namespace == Namespaces.Peer.SecretChat {
                            if let state = transaction.getPeerChatState(message.id.peerId) as? SecretChatState {
                                var layer: SecretChatLayer?
                                switch state.embeddedState {
                                    case .terminated, .handshake:
                                        break
                                    case .basicLayer:
                                        layer = .layer8
                                    case let .sequenceBasedLayer(sequenceState):
                                        layer = sequenceState.layerNegotiationState.activeLayer.secretChatLayer
                                }
                                if let layer = layer, !NagramiXGhostSettings.current.hidesMessageReads {
                                    var globallyUniqueIds: [Int64] = []
                                    if let globallyUniqueId = message.globallyUniqueId {
                                        globallyUniqueIds.append(globallyUniqueId)
                                        let updatedState = addSecretChatOutgoingOperation(transaction: transaction, peerId: message.id.peerId, operation: SecretChatOutgoingOperationContents.readMessagesContent(layer: layer, actionGloballyUniqueId: Int64.random(in: Int64.min ... Int64.max), globallyUniqueIds: globallyUniqueIds), state: state)
                                        if updatedState != state {
                                            transaction.setPeerChatState(message.id.peerId, state: updatedState)
                                        }
                                    }
                                }
                            }
                        } else {
                            addSynchronizeConsumeMessageContentsOperation(transaction: transaction, messageIds: [message.id])
                        }
                    }
                } else if let attribute = updatedAttributes[i] as? ConsumablePersonalMentionMessageAttribute, !attribute.consumed {
                    if NagramiXGhostSettings.current.hidesMessageReads {
                        transaction.setPendingMessageAction(type: .consumeUnseenPersonalMessage, id: messageId, action: nil)
                        updatedAttributes[i] = ConsumablePersonalMentionMessageAttribute(consumed: true, pending: false)
                        updatedTags.remove(.unseenPersonalMessage)
                        updateMessage = true
                    } else {
                    transaction.setPendingMessageAction(type: .consumeUnseenPersonalMessage, id: messageId, action: ConsumePersonalMessageAction())
                    updatedAttributes[i] = ConsumablePersonalMentionMessageAttribute(consumed: attribute.consumed, pending: true)
                    }
                }
            }
            
            let timestamp = Int32(CFAbsoluteTimeGetCurrent() + NSTimeIntervalSince1970)
            for i in 0 ..< updatedAttributes.count {
                if let attribute = updatedAttributes[i] as? AutoremoveTimeoutMessageAttribute {
                    if attribute.countdownBeginTime == nil || attribute.countdownBeginTime == 0 {
                        var timeout = attribute.timeout
                        if let duration = message.secretMediaDuration {
                            timeout = max(timeout, Int32(duration))
                        }
                        updatedAttributes[i] = AutoremoveTimeoutMessageAttribute(timeout: timeout, countdownBeginTime: timestamp)
                        updateMessage = true
                        
                        if messageId.peerId.namespace == Namespaces.Peer.SecretChat {
                            var layer: SecretChatLayer?
                            let state = transaction.getPeerChatState(message.id.peerId) as? SecretChatState
                            if let state = state {
                                switch state.embeddedState {
                                    case .terminated, .handshake:
                                        break
                                    case .basicLayer:
                                        layer = .layer8
                                    case let .sequenceBasedLayer(sequenceState):
                                        layer = sequenceState.layerNegotiationState.activeLayer.secretChatLayer
                                }
                            }
                            
                            if let state = state, let layer = layer, let globallyUniqueId = message.globallyUniqueId, !NagramiXGhostSettings.current.hidesMessageReads {
                                let updatedState = addSecretChatOutgoingOperation(transaction: transaction, peerId: messageId.peerId, operation: .readMessagesContent(layer: layer, actionGloballyUniqueId: Int64.random(in: Int64.min ... Int64.max), globallyUniqueIds: [globallyUniqueId]), state: state)
                                if updatedState != state {
                                    transaction.setPeerChatState(messageId.peerId, state: updatedState)
                                }
                            }
                        }
                    }
                } else if let attribute = updatedAttributes[i] as? AutoclearTimeoutMessageAttribute {
                    if attribute.countdownBeginTime == nil || attribute.countdownBeginTime == 0 {
                        var timeout = attribute.timeout
                        if let duration = message.secretMediaDuration, timeout != viewOnceTimeout {
                            timeout = max(timeout, Int32(duration))
                        }
                        updatedAttributes[i] = AutoclearTimeoutMessageAttribute(timeout: timeout, countdownBeginTime: timestamp)
                        updateMessage = true
                        
                        if messageId.peerId.namespace == Namespaces.Peer.SecretChat {
                            var layer: SecretChatLayer?
                            let state = transaction.getPeerChatState(message.id.peerId) as? SecretChatState
                            if let state = state {
                                switch state.embeddedState {
                                    case .terminated, .handshake:
                                        break
                                    case .basicLayer:
                                        layer = .layer8
                                    case let .sequenceBasedLayer(sequenceState):
                                        layer = sequenceState.layerNegotiationState.activeLayer.secretChatLayer
                                }
                            }
                            
                            if let state = state, let layer = layer, let globallyUniqueId = message.globallyUniqueId, !NagramiXGhostSettings.current.hidesMessageReads {
                                let updatedState = addSecretChatOutgoingOperation(transaction: transaction, peerId: messageId.peerId, operation: .readMessagesContent(layer: layer, actionGloballyUniqueId: Int64.random(in: Int64.min ... Int64.max), globallyUniqueIds: [globallyUniqueId]), state: state)
                                if updatedState != state {
                                    transaction.setPeerChatState(messageId.peerId, state: updatedState)
                                }
                            }
                        }
                    }
                }
            }
            
            if updateMessage {
                transaction.updateMessage(message.id, update: { currentMessage in
                    var storeForwardInfo: StoreMessageForwardInfo?
                    if let forwardInfo = currentMessage.forwardInfo {
                        storeForwardInfo = StoreMessageForwardInfo(authorId: forwardInfo.author?.id, sourceId: forwardInfo.source?.id, sourceMessageId: forwardInfo.sourceMessageId, date: forwardInfo.date, authorSignature: forwardInfo.authorSignature, psaType: forwardInfo.psaType, flags: forwardInfo.flags)
                    }
                    return .update(StoreMessage(id: currentMessage.id, customStableId: nil, globallyUniqueId: currentMessage.globallyUniqueId, groupingKey: currentMessage.groupingKey, threadId: currentMessage.threadId, timestamp: currentMessage.timestamp, flags: StoreMessageFlags(currentMessage.flags), tags: updatedTags, globalTags: currentMessage.globalTags, localTags: currentMessage.localTags, forwardInfo: storeForwardInfo, authorId: currentMessage.author?.id, text: currentMessage.text, attributes: updatedAttributes, media: currentMessage.media))
                })
            }
        }
    }
}

func _internal_markReactionsOrPollVotesAsSeenInteractively(postbox: Postbox, messageId: MessageId) -> Signal<Void, NoError> {
    return postbox.transaction { transaction -> Void in
        if let message = transaction.getMessage(messageId), (message.tags.contains(.unseenReaction) || message.tags.contains(.unseenPollVote)) {
            var updateMessage = false
            var updatedAttributes = message.attributes
            var updatedMedia = message.media
            
            for i in 0 ..< updatedAttributes.count {
                if let attribute = updatedAttributes[i] as? ReactionsMessageAttribute, attribute.hasUnseen {
                    updatedAttributes[i] = attribute.withAllSeen()
                    updateMessage = true
                    
                    if message.id.peerId.namespace == Namespaces.Peer.SecretChat {
                    } else {
                        transaction.setPendingMessageAction(type: .readReactionOrPollVote, id: messageId, action: ReadReactionAction())
                    }
                }
            }
            for i in 0 ..< updatedMedia.count {
                if let poll = updatedMedia[i] as? TelegramMediaPoll {
                    updatedMedia[i] = poll.withoutUnreadResults()
                    updateMessage = true
                    
                    if message.id.peerId.namespace == Namespaces.Peer.SecretChat {
                    } else {
                        transaction.setPendingMessageAction(type: .readReactionOrPollVote, id: messageId, action: ReadReactionAction())
                    }
                }
            }
            
            if updateMessage {
                transaction.updateMessage(message.id, update: { currentMessage in
                    var storeForwardInfo: StoreMessageForwardInfo?
                    if let forwardInfo = currentMessage.forwardInfo {
                        storeForwardInfo = StoreMessageForwardInfo(authorId: forwardInfo.author?.id, sourceId: forwardInfo.source?.id, sourceMessageId: forwardInfo.sourceMessageId, date: forwardInfo.date, authorSignature: forwardInfo.authorSignature, psaType: forwardInfo.psaType, flags: forwardInfo.flags)
                    }
                    var tags = currentMessage.tags
                    tags.remove(.unseenReaction)
                    tags.remove(.unseenPollVote)
                    return .update(StoreMessage(id: currentMessage.id, customStableId: nil, globallyUniqueId: currentMessage.globallyUniqueId, groupingKey: currentMessage.groupingKey, threadId: currentMessage.threadId, timestamp: currentMessage.timestamp, flags: StoreMessageFlags(currentMessage.flags), tags: tags, globalTags: currentMessage.globalTags, localTags: currentMessage.localTags, forwardInfo: storeForwardInfo, authorId: currentMessage.author?.id, text: currentMessage.text, attributes: updatedAttributes, media: updatedMedia))
                })
            }
        }
    }
}

func markMessageContentAsConsumedRemotely(transaction: Transaction, messageId: MessageId, consumeDate: Int32?, messageArchive: NagramiXMessageArchive? = nil) {
    if let message = transaction.getMessage(messageId) {
        var updateMessage = false
        var updatedAttributes = message.attributes
        var updatedMedia = message.media
        var updatedTags = message.tags
        
        for i in 0 ..< updatedAttributes.count {
            if let attribute = updatedAttributes[i] as? ConsumableContentMessageAttribute {
                if !attribute.consumed {
                    updatedAttributes[i] = ConsumableContentMessageAttribute(consumed: true)
                    updateMessage = true
                }
            } else if let attribute = updatedAttributes[i] as? ConsumablePersonalMentionMessageAttribute, !attribute.consumed {
                if attribute.pending {
                    transaction.setPendingMessageAction(type: .consumeUnseenPersonalMessage, id: messageId, action: nil)
                }
                updatedAttributes[i] = ConsumablePersonalMentionMessageAttribute(consumed: true, pending: false)
                updatedTags.remove(.unseenPersonalMessage)
                updateMessage = true
            }
        }
        
        let timestamp = Int32(CFAbsoluteTimeGetCurrent() + NSTimeIntervalSince1970)
        let countdownBeginTime = consumeDate ?? timestamp
        
        for i in 0 ..< updatedAttributes.count {
            if let attribute = updatedAttributes[i] as? AutoremoveTimeoutMessageAttribute {
                if (attribute.countdownBeginTime == nil || attribute.countdownBeginTime == 0) && message.containsSecretMedia {
                    updatedAttributes[i] = AutoremoveTimeoutMessageAttribute(timeout: attribute.timeout, countdownBeginTime: countdownBeginTime)
                    updateMessage = true
                                 
                    if message.id.peerId.namespace == Namespaces.Peer.SecretChat {
                    } else {
                        if attribute.timeout == viewOnceTimeout || timestamp >= autoremoveExpiryTimestamp(countdownBeginTime: countdownBeginTime, timeout: attribute.timeout) {
                            for i in 0 ..< updatedMedia.count {
                                if let _ = updatedMedia[i] as? TelegramMediaImage {
                                    updatedMedia[i] = TelegramMediaExpiredContent(data: .image)
                                } else if let file = updatedMedia[i] as? TelegramMediaFile {
                                    if file.isInstantVideo {
                                        updatedMedia[i] = TelegramMediaExpiredContent(data: .videoMessage)
                                    } else if file.isVoice {
                                        updatedMedia[i] = TelegramMediaExpiredContent(data: .voiceMessage)
                                    } else {
                                        updatedMedia[i] = TelegramMediaExpiredContent(data: .file)
                                    }
                                }
                            }
                        }
                    }
                }
            } else if let attribute = updatedAttributes[i] as? AutoclearTimeoutMessageAttribute {
                if (attribute.countdownBeginTime == nil || attribute.countdownBeginTime == 0) && message.containsSecretMedia {
                    updatedAttributes[i] = AutoclearTimeoutMessageAttribute(timeout: attribute.timeout, countdownBeginTime: countdownBeginTime)
                    updateMessage = true
                    
                    if message.id.peerId.namespace == Namespaces.Peer.SecretChat {
                    } else {
                        for i in 0 ..< updatedMedia.count {
                            if attribute.timeout == viewOnceTimeout || timestamp >= autoremoveExpiryTimestamp(countdownBeginTime: countdownBeginTime, timeout: attribute.timeout) {
                                if let _ = updatedMedia[i] as? TelegramMediaImage {
                                    updatedMedia[i] = TelegramMediaExpiredContent(data: .image)
                                } else if let file = updatedMedia[i] as? TelegramMediaFile {
                                    if file.isInstantVideo {
                                        updatedMedia[i] = TelegramMediaExpiredContent(data: .videoMessage)
                                    } else if file.isVoice {
                                        updatedMedia[i] = TelegramMediaExpiredContent(data: .voiceMessage)
                                    } else {
                                        updatedMedia[i] = TelegramMediaExpiredContent(data: .file)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        if updateMessage {
            if updatedMedia.contains(where: { $0 is TelegramMediaExpiredContent }) {
                messageArchive?.archiveTemporaryExpiration(message: message, expiredAt: consumeDate ?? Int32(Date().timeIntervalSince1970))
            }
            transaction.updateMessage(message.id, update: { currentMessage in
                var storeForwardInfo: StoreMessageForwardInfo?
                if let forwardInfo = currentMessage.forwardInfo {
                    storeForwardInfo = StoreMessageForwardInfo(authorId: forwardInfo.author?.id, sourceId: forwardInfo.source?.id, sourceMessageId: forwardInfo.sourceMessageId, date: forwardInfo.date, authorSignature: forwardInfo.authorSignature, psaType: forwardInfo.psaType, flags: forwardInfo.flags)
                }
                return .update(StoreMessage(id: currentMessage.id, customStableId: nil, globallyUniqueId: currentMessage.globallyUniqueId, groupingKey: currentMessage.groupingKey, threadId: currentMessage.threadId, timestamp: currentMessage.timestamp, flags: StoreMessageFlags(currentMessage.flags), tags: updatedTags, globalTags: currentMessage.globalTags, localTags: currentMessage.localTags, forwardInfo: storeForwardInfo, authorId: currentMessage.author?.id, text: currentMessage.text, attributes: updatedAttributes, media: updatedMedia))
            })
        }
    }
}


/// The sole explicit producer. No history read, global preference or local TTL
/// is changed; Telegram receives only this media's native content-read operation.
func _internal_markTemporaryMediaOpened(postbox: Postbox, messageId: MessageId) -> Signal<Bool, NoError> {
    return postbox.transaction { transaction -> Bool in
        guard let message = transaction.getMessage(messageId), nagramiXCanMarkTemporaryMediaOpened(message),
              NagramiXMessageArchive.forPostbox(postbox)?.hasExplicitTemporaryMediaOpen(id: messageId) == true else { return false }
        if messageId.peerId.namespace == Namespaces.Peer.SecretChat {
            guard let state = transaction.getPeerChatState(messageId.peerId) as? SecretChatState,
                  let globallyUniqueId = message.globallyUniqueId else { return false }
            let layer: SecretChatLayer
            switch state.embeddedState {
            case .terminated, .handshake: return false
            case .basicLayer: layer = .layer8
            case let .sequenceBasedLayer(sequenceState): layer = sequenceState.layerNegotiationState.activeLayer.secretChatLayer
            }
            let updatedState = addSecretChatOutgoingOperation(transaction: transaction, peerId: messageId.peerId,
                operation: .readMessagesContent(layer: layer, actionGloballyUniqueId: Int64.random(in: Int64.min ... Int64.max), globallyUniqueIds: [globallyUniqueId]), state: state)
            if updatedState != state { transaction.setPeerChatState(messageId.peerId, state: updatedState) }
        } else {
            addSynchronizeConsumeMessageContentsOperation(transaction: transaction, messageIds: [messageId], explicitMediaOpen: true)
        }
        transaction.updateMessage(messageId, update: { current in
            var attributes = current.attributes.filter { !($0 is ConsumableContentMessageAttribute) }
            attributes.append(ConsumableContentMessageAttribute(consumed: true))
            let forwardInfo = current.forwardInfo.map { StoreMessageForwardInfo(authorId: $0.author?.id, sourceId: $0.source?.id, sourceMessageId: $0.sourceMessageId, date: $0.date, authorSignature: $0.authorSignature, psaType: $0.psaType, flags: $0.flags) }
            return .update(StoreMessage(id: current.id, customStableId: nil, globallyUniqueId: current.globallyUniqueId,
                groupingKey: current.groupingKey, threadId: current.threadId, timestamp: current.timestamp,
                flags: StoreMessageFlags(current.flags), tags: current.tags, globalTags: current.globalTags,
                localTags: current.localTags, forwardInfo: forwardInfo, authorId: current.author?.id,
                text: current.text, attributes: attributes, media: current.media))
        })
        return true
    }
}
