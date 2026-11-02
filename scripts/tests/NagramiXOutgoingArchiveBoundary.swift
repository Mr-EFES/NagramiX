import Foundation

// Engine/Postbox identities and event delivery are boundaries. The archive
// methods/models and the complete media store are extracted production source.
enum NoError: Error {}
enum FetchError: Error { case unavailable }
protocol Disposable { func dispose() }
final class EmptyDisposable: Disposable { func dispose() {} }
final class MetaDisposable: Disposable {
    var value: Disposable?
    func set(_ value: Disposable) { self.value?.dispose();self.value=value }
    func dispose() { value?.dispose();value=nil }
}
final class Queue {
    var work: [()->Void]=[]
    func async(_ action: @escaping ()->Void) { work.append(action) }
    func drain() { while !work.isEmpty { work.removeFirst()() } }
}
final class Atomic<T> {
    var value: T
    init(value: T) { self.value=value }
    func with<R>(_ f: (T)->R) -> R { f(value) }
    func swap(_ next: T) -> T { let old=value;value=next;return old }
    func modify(_ f: (T)->T) -> T { value=f(value);return value }
}
enum SwiftSignalKit {
    final class Timer {
        init(timeout: Double,repeat: Bool,completion: @escaping ()->Void,queue: Queue) {}
        func start() {}
        func invalidate() {}
    }
}
final class Signal<T,E:Error> {
    let emit: (((T)->Void)?,((E)->Void)?)->Void
    init(_ emit: @escaping (((T)->Void)?,((E)->Void)?)->Void) { self.emit=emit }
    static func single(_ value: T) -> Signal { Signal { next,_ in next?(value) } }
    static func never() -> Signal { Signal { _,_ in } }
    func start(next: ((T)->Void)? = nil,error: ((E)->Void)? = nil) -> Disposable { emit(next,error);return EmptyDisposable() }
}
infix operator |> : AdditionPrecedence
func |> <A,B>(value: A, f: (A)->B) -> B { f(value) }
func filter<T,E>(_ f: @escaping (T)->Bool) -> (Signal<T,E>)->Signal<T,E> { { source in Signal { next,error in _=source.start(next:{ if f($0) { next?($0) } },error:error) } } }
func take<T,E>(_ count: Int) -> (Signal<T,E>)->Signal<T,E> { { $0 } }
func deliverOn<T,E>(_ queue: Queue) -> (Signal<T,E>)->Signal<T,E> {
    { source in Signal { next,error in _=source.start(next:{ value in queue.async { next?(value) } },error:{ value in queue.async { error?(value) } }) } }
}
final class Logger { static let shared=Logger();func log(_ category: String,_ value: String) {} }
struct PeerId: Hashable,Codable {
    let namespace: Int32
    let value: Int32
    init(_ raw: Int64) { namespace=Int32(raw>>32);value=Int32(truncatingIfNeeded:raw) }
    init(_ value: Int32,namespace: Int32=0) { self.namespace=namespace;self.value=value }
    func toInt64() -> Int64 { Int64(namespace)<<32 | Int64(UInt32(bitPattern:value)) }
    var isVerificationCodes: Bool { value==777000 }
}
enum Namespaces { enum Message { static let Cloud: Int32=0;static let Local: Int32=1 };enum Peer { static let SecretChat: Int32=1;static let CloudChannel: Int32=2 } }
struct MessageId: Hashable,Codable { let peerId: PeerId;let namespace: Int32;let id: Int32 }
enum StoreMessageId { case Id(MessageId),Partial(PeerId);var peerId: PeerId { switch self { case let .Id(id):return id.peerId;case let .Partial(id):return id } } }
struct MessageIndex: Comparable {
    let id: MessageId;let timestamp: Int32
    static func <(a:Self,b:Self)->Bool { a.timestamp == b.timestamp ? a.id.id<b.id.id : a.timestamp<b.timestamp }
}
struct StoreMessageFlags: OptionSet {
    let rawValue: Int
    init(rawValue: Int) { self.rawValue=rawValue }
    init(_ value: Self) { self=value }
    static let Incoming=Self(rawValue:1),CopyProtected=Self(rawValue:2)
}
public struct MessageTextEntity: Codable,Equatable { let value: Int }
protocol PostboxCoding: AnyObject {}
protocol Peer: PostboxCoding { var id: PeerId { get };var isCopyProtectionEnabled: Bool { get } }
final class TestPeer: Peer {
    let id: PeerId;let isCopyProtectionEnabled: Bool
    init(_ id: PeerId,protected: Bool=false) { self.id=id;isCopyProtectionEnabled=protected }
}
protocol MessageAttribute: AnyObject {}
final class AutoremoveTimeoutMessageAttribute: MessageAttribute {}
final class AutoclearTimeoutMessageAttribute: MessageAttribute {}
final class EphemeralMessageAttribute: MessageAttribute {}
final class EphemeralOutgoingMessageAttribute: MessageAttribute {}
final class EditedMessageAttribute: MessageAttribute { let date: Int32;init(_ value:Int32){date=value} }
final class TextEntitiesMessageAttribute: MessageAttribute { let entities:[MessageTextEntity];init(entities:[MessageTextEntity]){self.entities=entities} }
final class NagramiXArchivedMessageAttribute: MessageAttribute {
    let deletedAt:Int32;let revisions:[NagramiXMessageRevision]
    init(deletedAt:Int32,revisions:[NagramiXMessageRevision]){self.deletedAt=deletedAt;self.revisions=revisions}
}
struct MediaResourceId: Hashable { let stringRepresentation:String }
protocol MediaResource { var id: MediaResourceId { get } }
typealias TelegramMediaResource=MediaResource
struct TestResource: MediaResource { let id: MediaResourceId;init(_ value:String){id=MediaResourceId(stringRepresentation:value)} }
struct EmptyMediaResource: MediaResource { let id=MediaResourceId(stringRepresentation:"empty") }
struct LocalFileReferenceMediaResource: MediaResource {
    let localFilePath:String;let randomId:Int64;let isUniquelyReferencedTemporaryFile:Bool;let size:Int64
    var id:MediaResourceId { MediaResourceId(stringRepresentation:"local-\(randomId)") }
}
protocol Media:PostboxCoding { var peerIds:[PeerId] { get } }
extension Media { var peerIds:[PeerId] { [] } }
final class TelegramMediaExpiredContent:Media {}
final class TelegramMediaPaidContent:Media {}
final class TelegramMediaImageRepresentation {
    let resource:TelegramMediaResource
    let dimensions=(width:Int32(40),height:Int32(40))
    init(_ resource:TelegramMediaResource){self.resource=resource}
}
final class TelegramMediaImage:Media {
    let representations:[TelegramMediaImageRepresentation]
    var videoRepresentations:[TelegramMediaImageRepresentation]=[]
    var video:TelegramMediaFile?=nil
    init(_ resource:TelegramMediaResource){representations=[TelegramMediaImageRepresentation(resource)]}
}
final class TelegramMediaFile:Media {
    let resource:TelegramMediaResource;let kind:String
    var previewRepresentations:[TelegramMediaImageRepresentation]=[]
    var videoThumbnails:[TelegramMediaImageRepresentation]=[]
    var videoCover:TelegramMediaImage?=nil
    var alternativeRepresentations:[TelegramMediaFile]=[]
    init(_ resource:TelegramMediaResource,kind:String="file"){self.resource=resource;self.kind=kind}
}
struct MessageReference {
    let peer:Peer;let author:Peer?;let id:MessageId;let timestamp:Int32;let incoming:Bool;let secret:Bool;let threadId:Int64?
}
struct MediaResourceReference { let resource:MediaResource;let incoming:Bool }
enum AnyMediaReference {
    case message(message:MessageReference,media:Media)
    func resourceReference(_ resource:TelegramMediaResource)->MediaResourceReference { switch self { case let .message(reference,_):return MediaResourceReference(resource:resource,incoming:reference.incoming) } }
}
struct MediaResourceData { let path:String;let size:Int64;let complete:Bool;let offset:Int64 }
final class MediaBox {
    let cache:String
    var sources:[MediaResourceId:String]=[:]
    var fetched=0
    init(_ path:String){cache=path;try! FileManager.default.createDirectory(atPath:path,withIntermediateDirectories:true)}
    func keepResource(id:MediaResourceId)->Signal<Void,NoError>{.never()}
    func storePathsForId(_ id:MediaResourceId)->(complete:String,partial:String){(cache+"/"+id.stringRepresentation,cache+"/part-"+id.stringRepresentation)}
    func completedResourcePath(_ resource:MediaResource)->String?{let p=storePathsForId(resource.id).complete;return FileManager.default.fileExists(atPath:p) ? p:nil}
    func resourceData(_ resource:MediaResource)->Signal<MediaResourceData,NoError>{
        let path=(resource as? LocalFileReferenceMediaResource)?.localFilePath ?? sources[resource.id] ?? storePathsForId(resource.id).complete
        guard let data=try? FileManager.default.attributesOfItem(atPath:path),let size=data[.size] as? NSNumber else{return .never()}
        return .single(MediaResourceData(path:path,size:size.int64Value,complete:true,offset:0))
    }
    func removeCachedResources(_ ids:[MediaResourceId],force:Bool)->Signal<Void,NoError>{
        for id in ids {try? FileManager.default.removeItem(atPath:sources[id] ?? storePathsForId(id).complete)}
        return .single(())
    }
}
enum ResourceLocation {case other}
func fetchedMediaResource(mediaBox:MediaBox,userLocation:ResourceLocation,userContentType:ResourceLocation,reference:MediaResourceReference,reportResultStatus:Bool)->Signal<Void,FetchError>{mediaBox.fetched += 1;return .never()}
final class Codec {
    static var values:[Data:PostboxCoding]=[:]
    static func encode(_ value:PostboxCoding)->Data{let key=Data(UUID().uuidString.utf8);values[key]=value;return key}
}
final class Transaction {
    var peers:[PeerId:Peer]
    init(_ peers:[PeerId:Peer]){self.peers=peers}
    func getPeer(_ id:PeerId)->Peer?{peers[id]}
}
struct StoreMessage {
    let id:StoreMessageId;let customStableId:Int?;let globallyUniqueId:Int64?;let groupingKey:Int64?;let threadId:Int64?;let timestamp:Int32
    let flags:StoreMessageFlags;let tags:Set<Int>;let globalTags:Set<Int>;let localTags:Set<Int>;let forwardInfo:Int?;let authorId:PeerId?
    let text:String;let attributes:[MessageAttribute];let media:[Media]
}
final class Message {
    let store:StoreMessage;let peers:[PeerId:Peer]
    init(_ store:StoreMessage,peers:[PeerId:Peer]){self.store=store;self.peers=peers}
    var id:MessageId {if case let .Id(id)=store.id{return id};fatalError()}
    var globallyUniqueId:Int64?{store.globallyUniqueId};var groupingKey:Int64?{store.groupingKey};var threadId:Int64?{store.threadId};var timestamp:Int32{store.timestamp}
    var flags:StoreMessageFlags{store.flags};var tags:Set<Int>{store.tags};var globalTags:Set<Int>{store.globalTags};var localTags:Set<Int>{store.localTags}
    var author:Peer?{store.authorId.flatMap{peers[$0]}};var text:String{store.text};var attributes:[MessageAttribute]{store.attributes};var media:[Media]{store.media}
    var index:MessageIndex{MessageIndex(id:id,timestamp:timestamp)}
    func withUpdatedStableVersion(stableVersion:UInt32)->Message{self}
}
enum TagSpy {static var incoming:[Bool]=[]}
func tagsForStoreMessage(incoming:Bool,attributes:[MessageAttribute],media:[Media],textEntities:[MessageTextEntity],isPinned:Bool)->(Set<Int>,Set<Int>){TagSpy.incoming.append(incoming);return ([],[])}
func locallyRenderedMessage(message:StoreMessage,peers:[PeerId:Peer])->Message?{Message(message,peers:peers)}
