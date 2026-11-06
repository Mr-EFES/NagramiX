import Foundation

// IO boundary: deterministic signal events and API records. Routing, preview merge,
// edit resolver and the three consumer handoffs are extracted from production.
struct Signal<T, E> {
    var values: [T] = []
    var error: E? = nil
    static func single(_ value: T) -> Self { Self(values: [value]) }
    static func fail(_ error: E) -> Self { Self(error: error) }
    static func complete() -> Self { Self() }
}
infix operator |> : AdditionPrecedence
func |> <A,B>(value: A, transform: (A)->B) -> B { transform(value) }
func map<T,U,E>(_ transform: @escaping (T)->U) -> (Signal<T,E>)->Signal<U,E> { { Signal(values: $0.values.map(transform), error: $0.error) } }
func mapToSignal<T,U,E>(_ transform: @escaping (T)->Signal<U,E>) -> (Signal<T,E>)->Signal<U,E> {
    { source in
        if let error=source.error { return .fail(error) }
        var output=Signal<U,E>()
        for value in source.values {
            let next=transform(value); output.values += next.values
            if let error=next.error { output.error=error; break }
        }
        return output
    }
}
func take<T,E>(_ count: Int)->(Signal<T,E>)->Signal<T,E> { { Signal(values: Array($0.values.prefix(count)), error: $0.error) } }
func castError<T,E,F>(_ type: F.Type)->(Signal<T,E>)->Signal<T,F> { { Signal(values: $0.values) } }
func `catch`<T,E,F>(_ recover: @escaping (E)->Signal<T,F>)->(Signal<T,E>)->Signal<T,F> { { source in if let error=source.error { return recover(error) }; return Signal(values:source.values) } }
enum NoError {}
enum Api {
    struct InputRichMessage: Equatable { var ids: [Int]; var blocks: [String] }
    struct Webpage: Equatable { let flags: Int32; let url: String }
    enum InputMedia: Equatable { case inputMediaWebPage(Webpage); case inputMediaStory(Story); case native(Int) }
    struct Story: Equatable { var peer: Int; var id: Int }
}
protocol Media {}
protocol MessageAttribute {}
struct PeerId { var namespace: Int32 = 0 }
enum Namespaces { enum Peer { static let SecretChat: Int32 = 3 } }
class Peer {}
func apiInputPeer(_ peer: Peer)->Int? { 1 }
class Transaction { func getPeer(_ id: PeerId)->Peer? { Peer() } }
class Postbox { func transaction<T>(_ body: (Transaction)->T)->Signal<T,NoError> { .single(body(Transaction())) } }
class Network {}
class AccountAuxiliaryMethods {}
class MessageMediaPreuploadManager {}
class MediaReferenceRevalidationContext {}
struct TransformOutgoingMessageMedia {}
struct MessageId {}
struct AnyMediaReference {}
struct PartialMediaReference {}
struct CachedSentMediaReferenceKey {}
struct PendingMessageReuploadInfo {}
struct TelegramMediaAction: Media { enum Action { case historyScreenshot, other }; var action: Action }
struct TelegramMediaStory: Media { struct StoryId { var peerId: PeerId; var id: Int }; var storyId: StoryId }
struct TelegramMediaWebpage: Media {
    struct LoadedContent { var url: String }
    enum Content { case Loaded(LoadedContent), Pending }
    var content: Content
}
struct TelegramMediaFile: Media { var id: Int }
struct OutgoingChatContextResultMessageAttribute: MessageAttribute {}
struct AutoremoveTimeoutMessageAttribute: MessageAttribute {}
struct AutoclearTimeoutMessageAttribute: MessageAttribute {}
struct OutgoingMessageInfoAttribute: MessageAttribute { var partialReference: PartialMediaReference? }
struct ForwardSourceInfoAttribute: MessageAttribute {}
struct WebpagePreviewMessageAttribute: MessageAttribute { var forceLargeMedia: Bool? }
struct OutgoingContentInfoMessageAttribute: MessageAttribute {
    struct Flags: OptionSet { let rawValue: Int; static let disableLinkPreviews=Self(rawValue:1) }
    var flags: Flags
}
struct RichTextMessageAttribute: MessageAttribute {
    struct Page { var rawMedia: [Int]; var blocks: [String] }
    var instantPage: Page
    func apiInputRichMessage()->Api.InputRichMessage { Api.InputRichMessage(ids: [], blocks: instantPage.blocks) }
}
enum PendingMessageUploadedContent {
    case text(String), media(Api.InputMedia,String), richMessage(Api.InputRichMessage)
    case messageScreenshot, forward(ForwardSourceInfoAttribute), chatContextResult(OutgoingChatContextResultMessageAttribute)
}
struct PendingMessageUploadedContentProgress { var progress: Float }
enum PendingMessageUploadedContentResult { case progress(PendingMessageUploadedContentProgress), content(PendingMessageUploadedContentAndReuploadInfo) }
enum PendingMessageUploadedContentType { case none,text,media }
enum PendingMessageUploadError { case generic }
enum MessageContentToUpload { case immediate(PendingMessageUploadedContentResult,PendingMessageUploadedContentType), signal(Signal<PendingMessageUploadedContentResult,PendingMessageUploadError>,PendingMessageUploadedContentType) }

// PRODUCTION_UPLOADED_RECORD
// PRODUCTION_PREVIEW_MERGE
// PRODUCTION_UPLOAD_ROUTE
// PRODUCTION_EDIT_RESOLVER

var richUploads=0
var nativeUploads=0
var uploadFails=false
func richMessageContentToUpload(network: Network, postbox: Postbox, auxiliaryMethods: AccountAuxiliaryMethods, messageMediaPreuploadManager: MessageMediaPreuploadManager, forceReupload: Bool, peerId: PeerId, instantPage: RichTextMessageAttribute.Page)->Signal<PendingMessageUploadedContentResult,PendingMessageUploadError> {
    richUploads += 1
    if uploadFails { return .fail(.generic) }
    let value=PendingMessageUploadedContentAndReuploadInfo(content: .richMessage(Api.InputRichMessage(ids: instantPage.rawMedia, blocks: instantPage.blocks)), reuploadInfo:nil, cacheReferenceKey:nil)
    return Signal(values:[.progress(.init(progress:0.1)), .progress(.init(progress:0.7)), .content(value)])
}
func mediaContentToUpload(accountPeerId: PeerId, network: Network, postbox: Postbox, auxiliaryMethods: AccountAuxiliaryMethods, transformOutgoingMessageMedia: TransformOutgoingMessageMedia?, messageMediaPreuploadManager: MessageMediaPreuploadManager, revalidationContext: MediaReferenceRevalidationContext, forceReupload: Bool, isGrouped: Bool, passFetchProgress: Bool, forceNoBigParts: Bool, peerId: PeerId, media: Media, text: String, autoremoveMessageAttribute: AutoremoveTimeoutMessageAttribute?, autoclearMessageAttribute: AutoclearTimeoutMessageAttribute?, messageId: MessageId?, attributes: [MessageAttribute], mediaReference: AnyMediaReference?, explicitPartialReference: PartialMediaReference?)->Signal<PendingMessageUploadedContentResult,PendingMessageUploadError>? {
    guard let file=media as? TelegramMediaFile else { return nil }
    nativeUploads += 1
    return .single(.content(.init(content:.media(.native(file.id),text),reuploadInfo:nil,cacheReferenceKey:nil)))
}

func route(media: [Media], attributes: [MessageAttribute], secret: Bool=false)->Signal<PendingMessageUploadedContentResult,PendingMessageUploadError> {
    let result=messageContentToUpload(accountPeerId:PeerId(),network:Network(),postbox:Postbox(),auxiliaryMethods:AccountAuxiliaryMethods(),transformOutgoingMessageMedia:nil,messageMediaPreuploadManager:MessageMediaPreuploadManager(),revalidationContext:MediaReferenceRevalidationContext(),forceReupload:false,isGrouped:false,passFetchProgress:false,forceNoBigParts:false,peerId:PeerId(namespace:secret ? 3 : 0),messageId:nil,attributes:attributes,text:"post",media:media)
    switch result { case let .signal(signal,_):return signal; case let .immediate(value,_):return .single(value) }
}
func pendingRich(_ content: PendingMessageUploadedContentAndReuploadInfo)->Api.InputRichMessage? {
    var apiRichMessage: Api.InputRichMessage? = nil
    var flags: Int32=0
    // PRODUCTION_PENDING_HANDOFF
    _ = flags
    return apiRichMessage
}
func standaloneRich(_ content: PendingMessageUploadedContentAndReuploadInfo)->Api.InputRichMessage? {
    var apiRichMessage: Api.InputRichMessage? = nil
    var flags: Int32=0
    // PRODUCTION_STANDALONE_HANDOFF
    _ = flags
    return apiRichMessage
}
func ephemeralRich(_ content: PendingMessageUploadedContentAndReuploadInfo)->Api.InputRichMessage? {
    let media: Api.InputMedia?
    let richMessage: Api.InputRichMessage?
    let messageText: String
    var flags: Int32=0
    switch content.content {
    // PRODUCTION_EPHEMERAL_HANDOFF
    default: return nil
    }
    _ = (media,messageText,flags)
    return richMessage
}

@main struct EditorUploadTests {
    static func main() {
        var checks=0
        func check(_ ok: @autoclosure ()->Bool,_ message:String) { if !ok() { fatalError("Editor attachment regression: "+message) }; checks += 1 }
        let page=RichTextMessageAttribute(instantPage:.init(rawMedia:[9,2,4],blocks:["audio:9","paragraph:body","album:2,4"]))
        let preview=TelegramMediaWebpage(content:.Loaded(.init(url:"https://example.org/source")))
        for large: Bool? in [nil,false,true] {
            for top: [Media] in [[],[preview],[TelegramMediaWebpage(content:.Pending)]] {
                richUploads=0
                let stream=route(media:top,attributes:[page,WebpagePreviewMessageAttribute(forceLargeMedia:large)])
                check(stream.error==nil && richUploads==1,"all rich files must upload even alongside a preview")
                check(stream.values.count==3,"upload progress must survive")
                guard case let .content(content)=stream.values.last else { fatalError("missing content") }
                let expected=Api.InputRichMessage(ids:[9,2,4],blocks:page.instantPage.blocks)
                if top.first is TelegramMediaWebpage, case .Loaded = (top.first as! TelegramMediaWebpage).content {
                    check(content.resolvedRichMessage==expected,"preview retains the fully uploaded payload")
                    guard case let .media(.inputMediaWebPage(web),text)=content.content else { fatalError("preview lost") }
                    check(web.url=="https://example.org/source" && text=="post","original preview URL and text retained")
                    check(web.flags==(4 | (large == nil ? 0 : (large! ? 1 : 2))),"original preview size retained")
                    check(pendingRich(content)==expected,"pending sender consumes uploaded payload")
                    check(standaloneRich(content)==expected,"standalone sender consumes uploaded payload")
                    check(ephemeralRich(content)==expected,"ephemeral sender consumes uploaded payload")
                } else {
                    guard case let .richMessage(rich)=content.content else { fatalError("rich payload lost") }
                    check(rich==expected,"media-only and pending-preview rich path preserve all files and order")
                }
            }
        }
        let disabled=route(media:[preview],attributes:[page,OutgoingContentInfoMessageAttribute(flags:[.disableLinkPreviews])])
        guard case let .content(content)=disabled.values.last, case .richMessage=content.content else { fatalError("disabled preview returned") }
        check(content.resolvedRichMessage==nil,"disabled preview cannot reappear")
        nativeUploads=0; richUploads=0
        _=route(media:[TelegramMediaFile(id:99)],attributes:[])
        check(nativeUploads==1 && richUploads==0,"ordinary attachment sender is unchanged")
        richUploads=0
        _=route(media:[preview],attributes:[])
        check(richUploads==0,"ordinary text link does not upload rich media")
        uploadFails=true
        let failed=route(media:[preview],attributes:[page])
        check(failed.error != nil && failed.values.isEmpty,"failed upload must never emit a text-only post")
        let edit=uploadedRichMessage(network:Network(),postbox:Postbox(),auxiliaryMethods:AccountAuxiliaryMethods(),messageMediaPreuploadManager:MessageMediaPreuploadManager(),forceReupload:false,peerId:PeerId(),richText:page)
        check(edit.error != nil && edit.values.isEmpty,"failed edit must not silently strip attachments")
        uploadFails=false
        let successful=uploadedRichMessage(network:Network(),postbox:Postbox(),auxiliaryMethods:AccountAuxiliaryMethods(),messageMediaPreuploadManager:MessageMediaPreuploadManager(),forceReupload:false,peerId:PeerId(),richText:page)
        check(successful.values.count==1 && successful.values[0]?.ids==[9,2,4],"edit requests once after all embedded files are ready")
        let secret=uploadedRichMessage(network:Network(),postbox:Postbox(),auxiliaryMethods:AccountAuxiliaryMethods(),messageMediaPreuploadManager:MessageMediaPreuploadManager(),forceReupload:false,peerId:PeerId(namespace:3),richText:page)
        check(secret.error != nil && secret.values.isEmpty,"unsupported rich secret edit cannot become a partial edit")
        print("Editor upload checks: \(checks)")
    }
}
