import Foundation
import TelegramCore

/// Add the same visible attribution as a retained repost without flattening a
/// rich source or shifting its existing UTF-16 entities onto the author's name.
func nagramiXTemporaryReplySignedSource(_ source: EngineRawMessage, authorName: String) -> EngineRawMessage {
    let prefix = authorName + ":\n"
    let offset = prefix.utf16.count
    let entities = (source.attributes.compactMap { $0 as? TextEntitiesMessageAttribute }.first?.entities ?? []).map {
        MessageTextEntity(range: ($0.range.lowerBound + offset) ..< ($0.range.upperBound + offset), type: $0.type)
    }
    var attributes = source.attributes.filter { !($0 is TextEntitiesMessageAttribute) && !($0 is RichTextMessageAttribute) }
    attributes.append(TextEntitiesMessageAttribute(entities: entities))
    if let richText = source.attributes.compactMap({ $0 as? RichTextMessageAttribute }).first {
        let page = richText.fullInstantPage ?? richText.instantPage
        let signedPage = InstantPage(blocks: [.paragraph(.plain(authorName + ":"))] + page.blocks, media: page.media, isComplete: page.isComplete, rtl: page.rtl, url: page.url, views: nil)
        attributes.append(RichTextMessageAttribute(instantPage: signedPage, fullInstantPage: nil))
    }
    return source.withUpdatedText(prefix + source.text).withUpdatedAttributes(attributes)
}

/// The native multi-source-forward path sends one batch per source peer. Keep
/// the copied source and the user's comment too, in their original positions.
/// Non-forward runs stay intact so their album keys and rich payloads survive.
func nagramiXTemporaryReplyEnqueueGroups(_ messages: [EnqueueMessage]) -> [[EnqueueMessage]] {
    var result: [[EnqueueMessage]] = []
    for message in messages {
        var appendToLast = false
        if let previous = result.last?.last {
            switch (previous, message) {
            case let (.forward(previousSource, _, _, _, _), .forward(source, _, _, _, _)):
                appendToLast = previousSource.peerId == source.peerId
            case (.message, .message):
                appendToLast = true
            default:
                break
            }
        }
        if appendToLast {
            result[result.count - 1].append(message)
        } else {
            result.append([message])
        }
    }
    return result
}

/// The native send callback claims this object by correlation ID. Its prepared
/// files remain uncommitted through Stars confirmation and schedule diversion.
/// Rejection, cancellation and controller release roll them back automatically.
final class NagramiXTemporaryReplySend {
    let correlationId: Int64
    private let prepare: (@escaping (Bool) -> Void) -> Void
    private let ready: () -> Void
    private let mediaCopy: NagramiXArchivedMediaCopy?
    private var began = false
    private var committed = false

    var includesLocalCopy: Bool { return self.mediaCopy != nil }

    init(correlationId: Int64, mediaCopy: NagramiXArchivedMediaCopy?, prepare: @escaping (@escaping (Bool) -> Void) -> Void, ready: @escaping () -> Void) {
        self.correlationId = correlationId
        self.mediaCopy = mediaCopy
        self.prepare = prepare
        self.ready = ready
    }

    func matches(_ messages: [EnqueueMessage]) -> Bool {
        return messages.contains { message in
            switch message {
            case let .message(_, _, _, _, _, _, _, _, correlationId, _):
                return correlationId == self.correlationId
            case let .forward(_, _, _, _, correlationId):
                return correlationId == self.correlationId
            }
        }
    }

    func beforeEnqueue(_ completion: @escaping (Bool) -> Void) {
        guard !self.began else { completion(false); return }
        self.began = true
        // Keep the lease alive until the asynchronous authoritative lookup has
        // completed even if the gallery/chat goes away in the meantime.
        self.prepare { allowed in
            guard allowed, !self.committed else { completion(false); return }
            self.committed = true
            self.mediaCopy?.commit()
            self.ready()
            completion(true)
        }
    }
}
