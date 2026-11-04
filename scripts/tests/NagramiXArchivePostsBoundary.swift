import Foundation

// Message codec, Postbox transaction, signal delivery and media I/O are explicit
// boundaries. JSON persistence, post planning, archive mutations and rendering
// below are extracted from the actual final source.
struct PeerId: Hashable, Codable, Comparable {
    let value: Int64
    init(_ value: Int64) { self.value=value }
    var namespace: Int32 { value < 0 ? 99 : 0 }
    func toInt64() -> Int64 { value }
    static func <(a: Self,b: Self)->Bool { a.value<b.value }
}
struct MessageId: Hashable, Codable, Comparable {
    typealias Namespace=Int32
    let peerId: PeerId;let namespace:Int32;let id:Int32
    static func <(a:Self,b:Self)->Bool { a.peerId != b.peerId ? a.peerId<b.peerId : a.namespace != b.namespace ? a.namespace<b.namespace : a.id<b.id }
}
enum Namespaces { enum Message { static let Cloud:Int32=0 };enum Peer { static let SecretChat:Int32=99 } }
struct MessageTextEntity: Codable, Equatable { let text:String }
protocol MessageAttribute {}
struct TextEntitiesMessageAttribute: MessageAttribute { let entities:[MessageTextEntity] }
struct NagramiXArchivedMessageAttribute: MessageAttribute {
    let deletedAt:Int32;let revisions:[NagramiXMessageRevision];let isTemporary:Bool;let isViewOnceReplay:Bool
}
struct AudioTranscriptionMessageAttribute: MessageAttribute {}
struct DerivedDataMessageAttribute: MessageAttribute {}
struct Flags: OptionSet { let rawValue:Int;init(rawValue:Int){self.rawValue=rawValue};init(_ flags:Flags){self.rawValue=flags.rawValue};static let Incoming=Flags(rawValue:1) }
typealias StoreMessageFlags=Flags
typealias MessageFlags=Flags
class Peer { let id:PeerId;init(_ id:PeerId){self.id=id} }
final class TelegramGroup:Peer { struct Migration {let peerId:PeerId};var migrationReference:Migration? }
final class TelegramChannel:Peer { var isMonoForum=false;var linkedMonoforumId:PeerId? }
struct MessageForwardInfo {
    struct Flags:OptionSet {let rawValue:Int32}
    let author:Peer?;let source:Peer?;let sourceMessageId:MessageId?;let date:Int32;let authorSignature:String?;let psaType:String?;let flags:Flags
}
struct StoreMessageForwardInfo {
    let authorId:PeerId?;let sourceId:PeerId?;let sourceMessageId:MessageId?;let date:Int32;let authorSignature:String?;let psaType:String?;let flags:MessageForwardInfo.Flags
}
struct MediaResource {let id:String}
class Media {let name:String;init(_ name:String){self.name=name};var peerIds:[PeerId]{[]} }
final class LocalFileReferenceMediaResource {}
final class TelegramMediaFile:Media {var resource:Any=LocalFileReferenceMediaResource()}
final class TelegramMediaImage:Media {
    struct Dimensions {let width:Int32;let height:Int32}
    struct Representation {let dimensions:Dimensions;let resource:Any}
    var representations:[Representation]=[]
}
struct SimpleDictionary<K:Hashable,V>:Sequence {
    private var items:[K:V]=[:]
    subscript(_ key:K)->V? {get{items[key]}set{items[key]=newValue}}
    func makeIterator()->Dictionary<K,V>.Iterator {items.makeIterator()}
}
struct MessageIndex:Comparable {let id:MessageId;let timestamp:Int32;static func <(a:Self,b:Self)->Bool {a.timestamp != b.timestamp ? a.timestamp<b.timestamp : a.id<b.id}}
struct Message {
    typealias AssociatedThreadInfo=Int
    let stableId:UInt32;let stableVersion:UInt32;let id:MessageId;let globallyUniqueId:Int64?;let groupingKey:Int64?;let groupInfo:Int?;let threadId:Int64?;let timestamp:Int32;let flags:Flags;let tags:Int;let globalTags:Int;let localTags:[Int];let customTags:[Int];let forwardInfo:MessageForwardInfo?;let author:Peer?;let text:String;let attributes:[MessageAttribute];let media:[Media];let peers:SimpleDictionary<PeerId,Peer>;let associatedMessages:SimpleDictionary<MessageId,Message>;let associatedMessageIds:[MessageId];let associatedMedia:[Int:Int];let associatedThreadInfo:Int?;let associatedStories:[Int:Int]
    var index:MessageIndex {MessageIndex(id:id,timestamp:timestamp)}
}
enum StoreMessageId {case Id(MessageId);case Partial}
struct StoreMessage {
    let id:StoreMessageId;let customStableId:UInt32?;let globallyUniqueId:Int64?;let groupingKey:Int64?;let threadId:Int64?;let timestamp:Int32;let flags:Flags;let tags:Int;let globalTags:Int;let localTags:[Int];let forwardInfo:StoreMessageForwardInfo?;let authorId:PeerId?;let text:String;let attributes:[MessageAttribute];let media:[Media]
}
func tagsForStoreMessage(incoming:Bool,attributes:[MessageAttribute],media:[Media],textEntities:[MessageTextEntity],isPinned:Bool)->(Int,Int){(media.count,0)}
final class Atomic<T> {var value:T;init(value:T){self.value=value};func with<R>(_ f:(T)->R)->R{f(value)};func swap(_ value:T)->T{let old=self.value;self.value=value;return old};func modify(_ f:(T)->T)->T{value=f(value);return value}}
final class Queue {var jobs:[()->Void]=[];func async(_ f:@escaping()->Void){jobs.append(f)};func drain(){while !jobs.isEmpty {jobs.removeFirst()()}}}
struct NoError:Error {}
struct Disposable {}
let EmptyDisposable=Disposable()
struct Subscriber<T> {let next:(T)->Void;let completed:()->Void;func putNext(_ value:T){next(value)};func putCompletion(){completed()}}
final class Signal<T,E:Error> {
    let generator:(Subscriber<T>)->Disposable
    init(_ f:@escaping(Subscriber<T>)->Disposable){generator=f}
    static func complete()->Signal {Signal{$0.putCompletion();return EmptyDisposable}}
    @discardableResult func startStandalone(next:@escaping(T)->Void={_ in},completed:@escaping()->Void={}) -> Disposable {generator(Subscriber(next:next,completed:completed))}
}
struct NagramiXMessageArchiveSettings {
    static var current=Self()
    var showDeletedMessages=true;var saveTemporaryMessages=false;var replayViewOnce=false;var messageEditHistory=true
}
struct NagramiXArchiveMediaRequest {let name:String}
final class MediaStore {
    var sequence:Int64=0
    var reservations:[String:(Int64,[String])]=[:]
    var owners:[String:[String]]=[:]
    var files:Set<String>=[]
    var removed:[String]=[]
    func barrier()->Int64 {sequence+=1;return sequence}
    func reserve(key:String,requests:[NagramiXArchiveMediaRequest])->Int64 {let t=barrier();reservations[key]=(t,requests.map(\.name));return t}
    func retain(key:String,requests:[NagramiXArchiveMediaRequest],ticket:Int64){guard reservations[key]?.0==ticket else{return};owners[key]=requests.map(\.name);files.formUnion(requests.map(\.name))}
    func remove(keys:Set<String>,before:Int64){for key in keys where (reservations[key]?.0 ?? 0)<=before {reservations.removeValue(forKey:key);owners.removeValue(forKey:key)};prune()}
    func clear(before:Int64){remove(keys:Set(owners.keys).union(reservations.keys),before:before)}
    func prune(){let keep=Set(owners.values.flatMap{$0});for file in files.subtracting(keep){removed.append(file)};files.formIntersection(keep)}
}
final class Transaction {
    var messages:[MessageId:Message]=[:]
    var groups:[MessageId:[Message]]=[:]
    func getMessage(_ id:MessageId)->Message?{messages[id]}
    func getMessageGroup(_ id:MessageId)->[Message]?{groups[id]}
}
