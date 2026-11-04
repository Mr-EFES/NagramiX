import Foundation
import SwiftSignalKit
import Postbox

// Only TelegramCore owns the database transaction. Callers receive a snapshot
// or return replacement attributes; no Postbox handle escapes to UI modules.
public typealias EngineLocalMessageAttribute = MessageAttribute

public extension TelegramEngine.Messages {
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
