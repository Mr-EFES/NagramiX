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
}
