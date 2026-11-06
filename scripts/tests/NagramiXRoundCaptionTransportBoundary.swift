// Storage is an explicit boundary. Production copy preparation and retry run
// together: the transaction receives the attributes from the generated output.
struct RoundCaptionRandomId: MessageAttribute { let value: Int64 }
struct StoreMessage {
    let id: MessageId
    let customStableId: Int?
    let globallyUniqueId: Int64?
    let groupingKey: Int64?
    let threadId: Int64?
    let timestamp: Int32
    let flags: MessageFlags
    let tags: Int
    let globalTags: Int
    let localTags: Int
    let forwardInfo: Int?
    let authorId: PeerId?
    let text: String
    let attributes: [MessageAttribute]
    let media: [Media]
}
enum RoundCaptionUpdate { case skip, update(StoreMessage) }
final class RoundCaptionTransaction {
    var messages: [MessageId: Message] = [:]
    var updates: [StoreMessage] = []
    func updateMessage(_ id: MessageId, update: (Message) -> RoundCaptionUpdate) {
        guard var old = messages[id] else { return }
        if case let .update(value) = update(old) {
            updates.append(value)
            old.flags = value.flags
            old.attributes = value.attributes
            old.text = value.text
            old.media = value.media
            messages[id] = old
        }
    }
}
extension TestCopyPostbox {
    func transaction<T>(_ body: @escaping (RoundCaptionTransaction) -> T) -> Signal<T, NoError> {
        return .single(body(storage))
    }
}

// PRODUCTION_RETRY
