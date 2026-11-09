// External source/RPC and recursive uploader are explicit adapters. The decision
// branch connecting them is copied unchanged from messageContentToUpload.
struct MessageId: Equatable { let peerId: PeerId; let id: Int32 }
struct Network { var signalContent = false }
struct Postbox {}
struct AccountAuxiliaryMethods {}
struct TransformOutgoingMessageMedia {}
struct MessageMediaPreuploadManager {}
protocol MessageAttribute: AnyObject {}
struct OutgoingContentInfoFlags: OptionSet {
    let rawValue: Int32
    static let nagramiXCopy = OutgoingContentInfoFlags(rawValue: 2)
}
final class OutgoingContentInfoMessageAttribute: MessageAttribute {
    let flags: OutgoingContentInfoFlags
    init(_ flags: OutgoingContentInfoFlags = .nagramiXCopy) { self.flags = flags }
}
final class ForwardSourceInfoAttribute: MessageAttribute {}
struct AnyMediaReference { let partial: PartialMediaReference? }
enum PendingMessageUploadError { case generic }
enum PendingMessageUploadedContentType { case media }
enum PendingMessageUploadedContentResult { case sent(SenderRecord), bypassed }
enum MessageContentToUpload {
    case signal(Signal<PendingMessageUploadedContentResult, PendingMessageUploadError>, PendingMessageUploadedContentType)
    case immediate(PendingMessageUploadedContentResult, PendingMessageUploadedContentType)
}
final class MediaReferenceRevalidationContext {
    let result: Signal<Message, RevalidateMediaReferenceError>
    var requests = 0
    var requestedSource: Int64?
    var usedBackground: Bool?
    init(_ result: Signal<Message, RevalidateMediaReferenceError>) { self.result = result }
    func message(accountPeerId: PeerId, postbox: Postbox, network: Network, background: Bool, message: Int64) -> Signal<Message, RevalidateMediaReferenceError> {
        requests += 1; requestedSource = message; usedBackground = background
        return result
    }
}
struct SenderRecord {
    let forceReupload: Bool
    let peerId: PeerId
    let messageId: MessageId?
    let attributes: [MessageAttribute]
    let text: String
    let media: [Media]
    let mediaReference: AnyMediaReference?
    let isGrouped: Bool
    let passFetchProgress: Bool
    let forceNoBigParts: Bool
    let refreshAgain: Bool
}
func messageContentToUpload(accountPeerId: PeerId, network: Network, postbox: Postbox,
        auxiliaryMethods: AccountAuxiliaryMethods, transformOutgoingMessageMedia: TransformOutgoingMessageMedia?,
        messageMediaPreuploadManager: MessageMediaPreuploadManager, revalidationContext: MediaReferenceRevalidationContext,
        forceReupload: Bool, isGrouped: Bool, passFetchProgress: Bool, forceNoBigParts: Bool,
        peerId: PeerId, messageId: MessageId?, attributes: [MessageAttribute], text: String,
        media: [Media], mediaReference: AnyMediaReference? = nil, nagramiXRefreshCopyReferences: Bool = false) -> MessageContentToUpload {
    let record = SenderRecord(forceReupload: forceReupload, peerId: peerId, messageId: messageId,
        attributes: attributes, text: text, media: media, mediaReference: mediaReference,
        isGrouped: isGrouped, passFetchProgress: passFetchProgress, forceNoBigParts: forceNoBigParts,
        refreshAgain: nagramiXRefreshCopyReferences)
    if network.signalContent { return .signal(.single(.sent(record)), .media) }
    return .immediate(.sent(record), .media)
}
final class SenderResults {
    var records: [SenderRecord] = []
    var bypassed = 0
    var completed = 0
    func observe(_ content: MessageContentToUpload) -> Disposable {
        let signal: Signal<PendingMessageUploadedContentResult, PendingMessageUploadError>
        switch content {
        case let .signal(value, _): signal = value
        case let .immediate(value, _): signal = .single(value)
        }
        return signal.start(next: { result in
            switch result {
            case let .sent(record): self.records.append(record)
            case .bypassed: self.bypassed += 1
            }
        }, completed: { self.completed += 1 })
    }
}
