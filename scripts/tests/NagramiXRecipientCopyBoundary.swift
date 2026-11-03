// API boundaries only. Actual copier, file stager and pending-group collector
// are extracted from the composed native source by the validator.
struct NotificationInfoMessageAttribute: MessageAttribute { let muted: Bool }
struct OutgoingScheduleInfoMessageAttribute: MessageAttribute { let time: Int32 }
extension EngineMessage { typealias Id = MessageId }
extension EnqueueMessage {
    func withUpdatedAttributes(_ f: ([MessageAttribute]) -> [MessageAttribute]) -> Self {
        .message(text: text, attributes: f(attributes), inlineStickers: inlineStickers, mediaReference: mediaReference,
                 threadId: threadId, replyToMessageId: replyToMessageId, replyToStoryId: replyToStoryId,
                 localGroupingKey: localGroupingKey, correlationId: correlationId, bubbleUpEmojiOrStickersets: bubbleUpEmojiOrStickersets)
    }
}
typealias PendingMessageUploadedContentAndReuploadInfo = Int
typealias PendingMessageUploadedContentResult = Int
typealias PendingMessageUploadError = NoError
private final class PendingMessageContext {
    var state: PendingMessageState
    init(_ state: PendingMessageState) { self.state = state }
}
final class MetaDisposable: Disposable {
    private var value: Disposable?
    func set(_ value: Disposable?) { self.value?.dispose(); self.value = value }
    func dispose() { value?.dispose(); value = nil }
}
extension Signal {
    static func never() -> Signal { Signal { _ in ActionDisposable {} } }
    @discardableResult func startStrict() -> Disposable { start() }
    @discardableResult func startStandalone(next: @escaping (T) -> Void) -> Disposable { start(next: next) }
}
func deliverOnMainQueue<T, E>(_ source: Signal<T, E>) -> Signal<T, E> { source }
func mapToSignal<A, B, E>(_ body: @escaping (A) -> Signal<B, E>) -> (Signal<A, E>) -> Signal<B, E> {
    { source in Signal { out in
        let set = DisposableSet()
        set.add(source.start(next: { value in set.add(body(value).start(next: out.putNext, error: out.putError)) }, error: out.putError))
        return set
    } }
}
final class PendingStatusBoundary {
    var watched: [MessageId] = []
    func pendingMessageStatus(_ id: MessageId) -> Signal<(Int?, Bool), NoError> { watched.append(id); return .single((nil, false)) }
}
private final class SenderContext {
    let account: Account
    init(_ account: Account) { self.account = account }
}
private enum SenderSurface { case window(SenderPosition) }
private enum SenderPosition { case root }
private func nagramiXArchivedCopyAlert(context: SenderContext) -> Int { 1 }
private final class ManualEnqueue {
    var starts = 0
    var subscriber: Subscriber<[MessageId?], NoError>?
    var signal: Signal<[MessageId?], NoError> { Signal { out in self.starts += 1; self.subscriber = out; return ActionDisposable {} } }
    func accept(peer: Int, count: Int) { subscriber?.putNext((0..<count).map { MessageId(peerId: PeerId(value: peer), value: $0 + 1) }) }
}
