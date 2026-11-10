// Only API, Postbox, network and byte I/O are boundaries. The poll builder,
// attachment resolver, retry functions and SignalKit execute production code.
struct MessageId: Equatable { let peerId: PeerId; let id: Int32 }
enum Namespaces {
    enum Peer { static let SecretChat: Int32 = 4 }
    enum Media { static let LocalPoll: Int32 = 3 }
}
extension Int64 { var namespace: Int32 { self < 0 ? Namespaces.Peer.SecretChat : 0 } }
final class MTRpcError { let errorCode: Int; let errorDescription: String; init(errorCode: Int,errorDescription: String){self.errorCode=errorCode;self.errorDescription=errorDescription} }
final class Buffer { let data: Data; init(data: Data){self.data=data} }
final class Peer {}
struct SimpleDictionary<Key:Hashable,Value> {}
struct TextEntitiesMessageAttribute { let entities:[MessageTextEntity];init(entities:[MessageTextEntity]){self.entities=entities} }
func apiEntitiesFromMessageTextEntities(_ values:[MessageTextEntity],associatedPeers:SimpleDictionary<PeerId,Peer>)->[MessageTextEntity]{values}
func apiTextAttributeEntities(_ value:TextEntitiesMessageAttribute,associatedPeers:SimpleDictionary<PeerId,Peer>)->[MessageTextEntity]?{value.entities}
enum Api {
    typealias InputPeer=PeerId
    typealias MessageEntity=MessageTextEntity
    enum TextWithEntities { case textWithEntities(TextData) }
    struct TextData { let text:String;let entities:[MessageEntity] }
    enum PollAnswer { case inputPollAnswer(InputAnswer),pollAnswer(ReceivedAnswer) }
    struct InputAnswer {let flags:Int32;let text:TextWithEntities;let media:InputMedia?}
    struct ReceivedAnswer {let flags:Int32;let text:TextWithEntities;let option:Buffer;let media:Int?;let addedBy:Int?;let date:Int?}
    enum Poll {case poll(PollData)}
    struct PollData {let id:Int64;let flags:Int32;let question:TextWithEntities;let answers:[PollAnswer];let closePeriod:Int32?;let closeDate:Int32?;let countriesIso2:[String]?;let hash:Int64}
    indirect enum InputMedia {case inputMediaPoll(PollMedia),document(TelegramMediaFile),photo(TelegramMediaImage),other(Int)}
    struct PollMedia {let flags:Int32;let poll:Poll;let correctAnswers:[Int32]?;let attachedMedia:InputMedia?;let solution:String?;let solutionEntities:[MessageEntity]?;let solutionMedia:InputMedia?}
    enum MessageMedia {case messageMediaPhoto(PhotoData),messageMediaDocument(DocumentData),unexpected}
    struct PhotoData {let photo:TelegramMediaImage?;let video:Int?}
    struct DocumentData {let document:TelegramMediaFile?;let altDocuments:[Int]?}
    struct Request {let flags:Int32;let businessConnectionId:Int?;let peer:InputPeer;let media:InputMedia}
    enum functions {enum messages {
        static func uploadMedia(flags:Int32,businessConnectionId:Int?,peer:InputPeer,media:InputMedia)->Request {.init(flags:flags,businessConnectionId:businessConnectionId,peer:peer,media:media)}
    }}
}
func telegramMediaImageFromApiPhoto(_ image:TelegramMediaImage,video:Int?)->TelegramMediaImage?{image}
func telegramMediaFileFromApiDocument(_ file:TelegramMediaFile,altDocuments:[Int]?)->TelegramMediaFile?{file}
func pollCloudMediaToInputMedia(_ media:Media)->Api.InputMedia? {
    if let file=media as? TelegramMediaFile,file.resource is CloudDocumentMediaResource{return .document(file)}
    if let photo=media as? TelegramMediaImage,photo.reference != nil{return .photo(photo)}
    if let other=media as? OtherMedia,let id=other.id{return .other(Int(id.id))}
    return nil
}
struct AccountAuxiliaryMethods {}
struct TransformOutgoingMessageMedia {}
struct MessageMediaPreuploadManager {}
protocol MessageAttribute:AnyObject {}
struct OutgoingContentInfoFlags:OptionSet {let rawValue:Int32;static let nagramiXCopy=Self(rawValue:2)}
final class OutgoingContentInfoMessageAttribute:MessageAttribute {let flags:OutgoingContentInfoFlags;init(_ flags:OutgoingContentInfoFlags = .nagramiXCopy){self.flags=flags}}
final class ForwardSourceInfoAttribute:MessageAttribute {}
struct AnyMediaReference {let partial:PartialMediaReference?}
enum PendingMessageUploadError {case generic}
enum PendingMessageUploadedContent {case media(Api.InputMedia,String)}
struct PendingMessageUploadedContentAndReuploadInfo {let content:PendingMessageUploadedContent;let reuploadInfo:Int?;let cacheReferenceKey:Int?}
struct PendingMessageUploadedContentProgress {let progress:Float}
enum PendingMessageUploadedContentResult {case content(PendingMessageUploadedContentAndReuploadInfo),progress(PendingMessageUploadedContentProgress)}
final class Network {
    var requests:[Api.Request]=[]
    var automaticWaits:[Bool]=[]
    var responders:[()->Signal<Api.MessageMedia,MTRpcError>]=[]
    var cancellations=0
    func request(_ request:Api.Request,automaticFloodWait:Bool)->Signal<Api.MessageMedia,MTRpcError> {
        Signal { subscriber in
            self.requests.append(request);self.automaticWaits.append(automaticFloodWait)
            let result:Signal<Api.MessageMedia,MTRpcError>
            if !self.responders.isEmpty{result=self.responders.removeFirst()()}
            else {switch request.media {
            case let .document(file):result = .single(.messageMediaDocument(.init(document:file,altDocuments:nil)))
            case let .photo(photo):result = .single(.messageMediaPhoto(.init(photo:photo,video:nil)))
            default:result = .single(.unexpected)
            }}
            let disposable=result.start(next:subscriber.putNext,error:subscriber.putError,completed:subscriber.putCompletion)
            return ActionDisposable {self.cancellations+=1;disposable.dispose()}
        }
    }
}
final class Postbox {
    var peerAvailable=true
    struct Upload {let peer:PeerId;let id:MediaId?;let partial:PartialMediaReference?;let forced:Bool;let grouped:Bool;let copyFlag:Bool}
    var uploads:[Upload]=[]
    var bytesResult:(()->Signal<PendingMessageUploadedContentResult,PendingMessageUploadError>)?
    final class Transaction {let available:Bool;init(_ available:Bool){self.available=available};func getPeer(_ id:PeerId)->Peer?{available ? Peer():nil}}
    func transaction<T>(_ f:@escaping(Transaction)->T)->Signal<T,NoError>{.single(f(Transaction(peerAvailable)))}
}
func apiInputPeer(_ peer:Peer)->Api.InputPeer?{2}
final class MediaReferenceRevalidationContext {
    var result:Signal<Message,RevalidateMediaReferenceError> = .complete()
    var requests=0
    func message(accountPeerId:PeerId,postbox:Postbox,network:Network,background:Bool,message:Int64)->Signal<Message,RevalidateMediaReferenceError>{requests+=1;return result}
}
func bytes(_ postbox:Postbox,_ peer:PeerId,_ media:Media,_ partial:PartialMediaReference?,_ force:Bool,_ grouped:Bool,_ attributes:[MessageAttribute])->Signal<PendingMessageUploadedContentResult,PendingMessageUploadError> {
    postbox.uploads.append(.init(peer:peer,id:media.id,partial:partial,forced:force,grouped:grouped,copyFlag:attributes.contains{($0 as? OutgoingContentInfoMessageAttribute)?.flags.contains(.nagramiXCopy)==true}))
    if let result=postbox.bytesResult{return result()}
    let input:Api.InputMedia
    if media is TelegramMediaFile {input = .document(doc(777,"uploaded"))}else{input = .photo(photo(888,"uploaded"))}
    return .single(.content(.init(content:.media(input,""),reuploadInfo:nil,cacheReferenceKey:nil)))
}
func uploadedMediaImageContent(network:Network,postbox:Postbox,transformOutgoingMessageMedia:TransformOutgoingMessageMedia?,messageMediaPreuploadManager:MessageMediaPreuploadManager,forceReupload:Bool,isGrouped:Bool,peerId:PeerId,image:TelegramMediaImage,messageId:MessageId?,text:String,attributes:[MessageAttribute],autoremoveMessageAttribute:Int?,autoclearMessageAttribute:Int?,auxiliaryMethods:AccountAuxiliaryMethods)->Signal<PendingMessageUploadedContentResult,PendingMessageUploadError>{bytes(postbox,peerId,image,image.partialReference,forceReupload,isGrouped,attributes)}
func uploadedMediaFileContent(network:Network,postbox:Postbox,auxiliaryMethods:AccountAuxiliaryMethods,transformOutgoingMessageMedia:TransformOutgoingMessageMedia?,messageMediaPreuploadManager:MessageMediaPreuploadManager,forceReupload:Bool,isGrouped:Bool,isPaid:Bool,passFetchProgress:Bool,forceNoBigParts:Bool,peerId:PeerId,messageId:MessageId?,text:String,attributes:[MessageAttribute],autoremoveMessageAttribute:Int?,autoclearMessageAttribute:Int?,file:TelegramMediaFile)->Signal<PendingMessageUploadedContentResult,PendingMessageUploadError>{bytes(postbox,peerId,file,file.partialReference,forceReupload,isGrouped,attributes)}
final class Probe {
    var values:[PendingMessageUploadedContentResult]=[];var errors=0;var completed=0;var disposable:Disposable?
    func start(_ source:Signal<PendingMessageUploadedContentResult,PendingMessageUploadError>){disposable=source.start(next:{self.values.append($0)},error:{_ in self.errors+=1},completed:{self.completed+=1})}
    var poll:Api.PollMedia? {for value in values {if case let .content(content)=value,case let .media(media,_)=content.content,case let .inputMediaPoll(poll)=media{return poll}};return nil}
}
