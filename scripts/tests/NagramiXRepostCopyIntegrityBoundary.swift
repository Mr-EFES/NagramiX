// Postbox storage and composer widgets are explicit boundaries. The production
// copier, file staging and complete composer assembly block execute unchanged.
extension MessageId: Comparable {
    static func < (lhs: Self, rhs: Self) -> Bool {
        if lhs.peerId.value != rhs.peerId.value { return lhs.peerId.value < rhs.peerId.value }
        if lhs.namespace != rhs.namespace { return lhs.namespace < rhs.namespace }
        return lhs.value < rhs.value
    }
}
enum SourceForwardGrouping { case auto }
struct ForwardOptionsMessageAttribute: MessageAttribute { let hideNames: Bool; let hideCaptions: Bool }
extension EnqueueMessage {
    static func forward(source: MessageId, threadId: Int64?, grouping: SourceForwardGrouping, attributes: [MessageAttribute], correlationId: Int64?) -> Self {
        var result = Self.message(text: "", attributes: attributes, inlineStickers: [:], mediaReference: nil, threadId: threadId, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: nil, correlationId: correlationId, bubbleUpEmojiOrStickersets: [])
        result.nativeForwardSource = source
        return result
    }
    func withUpdatedThreadId(_ thread: Int64?) -> Self {
        var result = Self.message(text: text, attributes: attributes, inlineStickers: inlineStickers, mediaReference: mediaReference, threadId: thread, replyToMessageId: replyToMessageId, replyToStoryId: replyToStoryId, localGroupingKey: localGroupingKey, correlationId: correlationId, bubbleUpEmojiOrStickersets: bubbleUpEmojiOrStickersets)
        result.nativeForwardSource = nativeForwardSource
        return result
    }
}
final class SourceArchive {
    var messages: [MessageId: Message] = [:]
    func deletedMessage(id: MessageId) -> Message? { messages[id] }
}
struct SourceContext { let account: Account }
struct SourceOptions { var hideNames = false; var hideCaptions = false }
struct SourceInterface { var forwardOptionsState: SourceOptions? }
struct SourcePresentation { var interfaceState = SourceInterface() }
final class SourceInteraction {
    var errors = 0
    func presentController(_ alert: String, _ arguments: Int?) { errors += 1 }
}
extension NagramiXArchivedMediaCopy {
    convenience init(account: Account) { self.init(mediaBox: account.postbox.mediaBox) }
}
final class SourcePaymentController {
    var quotes: [Int32] = []
    var confirmation: ((Bool) -> Void)?
    func presentPaidMessageAlertIfNeeded(count: Int32, completion: @escaping (Bool) -> Void) {
        quotes.append(count); confirmation = completion
    }
}
func nagramiXArchivedCopyAlert(context: SourceContext) -> String { "unavailable" }
final class SourceComposer {
    let context: SourceContext
    var chatPresentationInterfaceState = SourcePresentation()
    let interfaceInteraction: SourceInteraction? = SourceInteraction()
    let controller: SourcePaymentController? = SourcePaymentController()
    var preparedStaging: NagramiXArchivedMediaCopy?
    var sentModes: [Bool] = []
    var sentCounts: [Int] = []
    var output: [EnqueueMessage]?
    init(account: Account, hideNames: Bool = false, hideCaptions: Bool = false) {
        context = SourceContext(account: account)
        chatPresentationInterfaceState.interfaceState.forwardOptionsState = SourceOptions(hideNames: hideNames, hideCaptions: hideCaptions)
    }
    func assemble(_ forwardMessageIds: [MessageId], resolved nagramiXResolvedForwards: [MessageId: Message]?, thread replyThreadId: Int64? = nil, prefix: [EnqueueMessage] = []) {
        output = nil
        var messages = prefix
        var nagramiXForwardCopyStaging: NagramiXArchivedMediaCopy?
        let options = chatPresentationInterfaceState.interfaceState.forwardOptionsState
        let attributes: [MessageAttribute] = [ForwardOptionsMessageAttribute(hideNames: options?.hideNames == true, hideCaptions: options?.hideCaptions == true)]
        // PRODUCTION_COMPOSER_ASSEMBLY
        preparedStaging = nagramiXForwardCopyStaging
        output = messages
    }
    func submitPrepared(paid: Bool, postpone: Bool = false) {
        guard let messages = output else { return }
        let nagramiXForwardPaymentRequired = paid
        let sendPreparedForward: (Bool) -> Void = { [weak self] mode in
            guard let self else { return }
            self.preparedStaging?.commit(); self.preparedStaging = nil
            self.sentModes.append(mode)
            self.sentCounts.append(messages.count)
        }
        // PRODUCTION_COMPOSER_CONFIRMATION
    }
    func cancel() {
        controller?.confirmation = nil
        preparedStaging = nil
        output = nil
    }
}
