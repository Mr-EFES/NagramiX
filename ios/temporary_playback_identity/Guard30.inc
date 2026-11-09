import Foundation
import SwiftSignalKit
import Postbox

// Only TelegramCore owns the database transaction. Callers receive a snapshot
// or return replacement attributes; no Postbox handle escapes to UI modules.
public typealias EngineLocalMessageAttribute = MessageAttribute

/// A local send preflight; it never marks content read or fetches the server.
public enum NagramiXTemporaryReplyResolution {
    case native
    case copy(EngineRawMessage)
    case unavailable
}

public extension TelegramEngine.Messages {
    /// Resolve the current reply target in the same transaction that reads its
    /// live row. A vanished temporary source is copied only from retained data.
    func nagramiXResolveTemporaryReply(messageId: EngineMessage.Id, expectedTemporary: Bool = false) -> Signal<NagramiXTemporaryReplyResolution, NoError> {
        return self.account.postbox.transaction { transaction -> NagramiXTemporaryReplyResolution in
            let live = transaction.getMessage(messageId)
            let expectsTemporary = expectedTemporary || live.map { nagramiXIsTemporaryMessage($0) } == true
            if let live, !live.media.contains(where: { $0 is TelegramMediaExpiredContent }) {
                // A real server target keeps the native reply even when the
                // preservation switch has since been disabled.
                return .native
            }
            guard nagramiXTemporaryMessagesEnabled() else {
                return expectsTemporary ? .unavailable : .native
            }
            if let retained = NagramiXMessageArchive.forPostbox(self.account.postbox)?.temporaryInteractionMessage(id: messageId, liveMessage: live),
               nagramiXCanRetainTemporaryMessage(retained),
               !retained.media.contains(where: { $0 is TelegramMediaExpiredContent }) {
                return .copy(retained)
            }
            return expectsTemporary ? .unavailable : .native
        }
    }

    /// Snapshot deletion ownership inside TelegramCore; UI receives no Postbox handle.
    func nagramiXArchivePostDeletionPlan(messageIds: Set<EngineMessage.Id>, localCandidates: Set<EngineMessage.Id>) -> Signal<NagramiXArchivePostDeletionPlan, NoError> {
        self.account.postbox.transaction { transaction in
            guard let archive = NagramiXMessageArchive.forPostbox(self.account.postbox) else {
                return NagramiXArchivePostDeletionPlan(nativeMessageIds: messageIds, localMessageIds: [], liveMessageIds: Set(messageIds.filter { transaction.getMessage($0) != nil }))
            }
            return archive.postDeletionPlan(transaction: transaction, messageIds: messageIds, localCandidates: localCandidates)
        }
    }

    func nagramiXLocalMessages(_ ids: [EngineMessage.Id]) -> Signal<[EngineRawMessage], NoError> {
        self.account.postbox.transaction { transaction in
            Array(Set(ids)).compactMap { transaction.getMessage($0) }
        }
    }
    func nagramiXUpdateLocalMessageAttributes(messageId: EngineMessage.Id, transform: @escaping (EngineRawMessage) -> [EngineLocalMessageAttribute]?) -> Signal<Bool, NoError> {
        self.account.postbox.transaction { transaction -> Bool in
            guard let message = transaction.getMessage(messageId), let attributes = transform(message) else { return false }
            transaction.updateMessage(messageId, update: { current in
                .update(StoreMessage(id: current.id, customStableId: nil, globallyUniqueId: current.globallyUniqueId, groupingKey: current.groupingKey,
                    threadId: current.threadId, timestamp: current.timestamp, flags: StoreMessageFlags(current.flags), tags: current.tags,
                    globalTags: current.globalTags, localTags: current.localTags, forwardInfo: current.forwardInfo.flatMap(StoreMessageForwardInfo.init),
                    authorId: current.author?.id, text: current.text, attributes: attributes, media: current.media))
            })
            return true
        }
    }

    /// Resolve the same visible live/retained row without invoking open/consume.
    func nagramiXTranscriptionMessages(_ ids: [EngineMessage.Id]) -> Signal<[EngineRawMessage], NoError> {
        self.account.postbox.transaction { transaction in
            let archive = NagramiXMessageArchive.forPostbox(self.account.postbox)
            return Array(Set(ids)).compactMap { id in
                let live = transaction.getMessage(id)
                return archive?.transcriptionMessage(id: id, liveMessage: live) ?? live
            }
        }
    }

    func nagramiXUpdateTranscriptionAttributes(messageId: EngineMessage.Id, transform: @escaping (EngineRawMessage) -> [EngineLocalMessageAttribute]?) -> Signal<Bool, NoError> {
        return self.account.postbox.transaction { transaction -> Bool? in
            guard let message = transaction.getMessage(messageId),
                  !message.media.contains(where: { $0 is TelegramMediaExpiredContent }) else { return nil }
            guard let attributes = transform(message) else { return false }
            transaction.updateMessage(messageId, update: { current in
                .update(StoreMessage(id: current.id, customStableId: nil, globallyUniqueId: current.globallyUniqueId, groupingKey: current.groupingKey,
                    threadId: current.threadId, timestamp: current.timestamp, flags: StoreMessageFlags(current.flags), tags: current.tags,
                    globalTags: current.globalTags, localTags: current.localTags, forwardInfo: current.forwardInfo.flatMap(StoreMessageForwardInfo.init),
                    authorId: current.author?.id, text: current.text, attributes: attributes, media: current.media))
            })
            return true
        }
        |> mapToSignal { saved -> Signal<Bool, NoError> in
            guard saved != false, let archive = NagramiXMessageArchive.forPostbox(self.account.postbox) else { return .single(saved ?? false) }
            // Mirror a live result into an existing approved retained record, or
            // update only that record if the server original has disappeared.
            return archive.updateTranscriptionAttributes(id: messageId, transform: transform)
            |> map { archived in (saved ?? false) || archived }
        }
    }
}
