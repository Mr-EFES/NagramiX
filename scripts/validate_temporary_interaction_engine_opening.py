#!/usr/bin/env python3
"""Проверить local reply preflight, зеркало ASR и native viewer routes временных сообщений."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
LOCAL = 'submodules/TelegramCore/Sources/TelegramEngine/Messages/NagramiXLocalMessageData.swift'
ENGINE = 'submodules/TelegramCore/Sources/TelegramEngine/Messages/TelegramEngineMessages.swift'
GALLERY = 'submodules/GalleryData/Sources/GalleryData.swift'
OPEN = 'submodules/TelegramUI/Sources/Chat/ChatControllerOpenViewOnceMediaMessage.swift'
ROUND = 'submodules/TelegramUI/Components/Chat/ChatMessageInstantVideoBubbleContentNode/Sources/ChatMessageInstantVideoBubbleContentNode.swift'
POLICY = 'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift'
ARCHIVE = 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift'
PATHS = [LOCAL, ENGINE, GALLERY, OPEN, ROUND]

ENGINE_BOUNDARY = r'''
import Foundation
// Postbox scheduling, serialization/persistence and archive rendering are explicit
// boundaries. Actual engine and archive public guard/transform bodies execute.
final class Disposable {}
let EmptyDisposable = Disposable()
enum NoError {}
final class Subscriber<V,E> {
    let next: (V) -> Void
    let completion: () -> Void
    init(_ next: @escaping (V) -> Void, _ completion: @escaping () -> Void = {}) { self.next=next;self.completion=completion }
    func putNext(_ value: V) { self.next(value) }
    func putCompletion() { self.completion() }
}
final class Signal<V,E> {
    let body: (Subscriber<V,E>) -> Disposable
    init(_ body: @escaping (Subscriber<V,E>) -> Disposable) { self.body=body }
    @discardableResult func start(next: @escaping (V)->Void = {_ in}, completed: @escaping () -> Void = {}) -> Disposable { self.body(Subscriber(next,completed)) }
    @discardableResult func startStandalone() -> Disposable { self.start() }
}
infix operator |> : AdditionPrecedence
func |> <T,U>(_ value:T,_ f:(T)->U)->U {f(value)}
func ignoreValues<V,E>(_ input:Signal<V,E>)->Signal<Never,E> { Signal { subscriber in input.start(next: {_ in}, completed: {subscriber.putCompletion()}) } }
struct PeerId: Hashable {
    var namespace: Int32 = 0
    var value: Int64 = 10
    var isVerificationCodes = false
    func toInt64()->Int64 { self.value + Int64(namespace)*1_000_000 }
}
struct MessageId: Hashable { var peerId=PeerId();var namespace:Int32=0;var id:Int32=1 }
struct Namespaces {
    struct Peer { static let CloudUser:Int32=0;static let CloudGroup:Int32=1;static let CloudChannel:Int32=2;static let SecretChat:Int32=3 }
    struct Message { static let Cloud:Int32=0;static let Local:Int32=1;static let SecretIncoming:Int32=2 }
}
struct MessageFlags: OptionSet {
    let rawValue:Int
    static let Incoming=Self(rawValue:1);static let Failed=Self(rawValue:2);static let Sending=Self(rawValue:4);static let Unsent=Self(rawValue:8)
    var isSending:Bool {self.contains(.Sending) || self.contains(.Unsent)}
}
struct StoreMessageFlags: OptionSet {
    let rawValue:Int
    init(rawValue:Int){self.rawValue=rawValue}
    init(_ value:MessageFlags){self.rawValue=value.rawValue}
    static let Incoming=Self(rawValue:1);static let Failed=Self(rawValue:2);static let Sending=Self(rawValue:4);static let Unsent=Self(rawValue:8)
}
class Media {}
final class TelegramMediaFile:Media {var isVoice=true;var isInstantVideo=false}
final class TelegramMediaExpiredContent:Media {}
final class TelegramMediaPaidContent:Media {}
final class TelegramMediaAction:Media {}
final class TelegramMediaImage:Media {}
protocol PostboxCoding:AnyObject {}
protocol MessageAttribute:PostboxCoding {}
final class AutoremoveTimeoutMessageAttribute:MessageAttribute {let timeout:Int32;init(_ value:Int32){timeout=value}}
final class AutoclearTimeoutMessageAttribute:MessageAttribute {let timeout:Int32;init(_ value:Int32){timeout=value}}
final class NagramiXArchivedMessageAttribute:MessageAttribute {let isTemporary:Bool;init(_ value:Bool=true){isTemporary=value}}
final class EphemeralMessageAttribute:MessageAttribute {}
final class EphemeralOutgoingMessageAttribute:MessageAttribute {}
final class DerivedDataMessageAttribute:MessageAttribute {}
final class AudioTranscriptionMessageAttribute:MessageAttribute {
    enum TranscriptionError {case generic}
    let id:Int64;let text:String;let isPending:Bool;let didRate:Bool;let error:TranscriptionError?
    init(id:Int64,text:String,isPending:Bool,didRate:Bool,error:TranscriptionError?){self.id=id;self.text=text;self.isPending=isPending;self.didRate=didRate;self.error=error}
}
final class Peer {let id:PeerId;init(_ id:PeerId){self.id=id}}
struct ForwardInfo {let value:Int}
struct StoreMessageForwardInfo {let value:Int;init(_ value:ForwardInfo){self.value=value.value}}
final class Message {
    var id=MessageId();var flags:MessageFlags=[.Incoming];var attributes:[MessageAttribute]=[];var media:[Media]=[TelegramMediaFile()]
    var globallyUniqueId:Int64?=3;var groupingKey:Int64?=7;var threadId:Int64?=12;var timestamp:Int32=100
    var tags:Set<Int>=[1];var globalTags:Set<Int>=[2];var localTags:Set<Int>=[3];var forwardInfo:ForwardInfo?=ForwardInfo(value:8)
    var author:Peer?=Peer(PeerId(value:9));var text="source body"
    var paidContent:Media? {media.first {$0 is TelegramMediaPaidContent}}
    func copy()->Message {let m=Message();m.id=id;m.flags=flags;m.attributes=attributes;m.media=media;m.globallyUniqueId=globallyUniqueId;m.groupingKey=groupingKey;m.threadId=threadId;m.timestamp=timestamp;m.tags=tags;m.globalTags=globalTags;m.localTags=localTags;m.forwardInfo=forwardInfo;m.author=author;m.text=text;return m}
}
enum StoreMessageId {case Id(MessageId)}
struct StoreMessage {
    let id:StoreMessageId;let globallyUniqueId:Int64?;let groupingKey:Int64?;let threadId:Int64?;let timestamp:Int32;let flags:StoreMessageFlags
    let tags:Set<Int>;let globalTags:Set<Int>;let localTags:Set<Int>;let forwardInfo:StoreMessageForwardInfo?;let authorId:PeerId?;let text:String;let attributes:[MessageAttribute];let media:[Media]
    init(id:MessageId,customStableId:Int64?,globallyUniqueId:Int64?,groupingKey:Int64?,threadId:Int64?,timestamp:Int32,flags:StoreMessageFlags,tags:Set<Int>,globalTags:Set<Int>,localTags:Set<Int>,forwardInfo:StoreMessageForwardInfo?,authorId:PeerId?,text:String,attributes:[MessageAttribute],media:[Media]) {self.id = .Id(id);self.globallyUniqueId=globallyUniqueId;self.groupingKey=groupingKey;self.threadId=threadId;self.timestamp=timestamp;self.flags=flags;self.tags=tags;self.globalTags=globalTags;self.localTags=localTags;self.forwardInfo=forwardInfo;self.authorId=authorId;self.text=text;self.attributes=attributes;self.media=media}
}
typealias EngineRawMessage=Message
enum EngineMessage {typealias Id=MessageId}
enum MessageUpdate {case update(StoreMessage)}
final class Transaction {
    var messages:[MessageId:Message]=[:];var writes=0
    func getMessage(_ id:MessageId)->Message? {messages[id]}
    func updateMessage(_ id:MessageId,update:(Message)->MessageUpdate){guard let old=messages[id] else{return};switch update(old){case let .update(value):let m=Message();if case let .Id(mid)=value.id{m.id=mid};m.flags=MessageFlags(rawValue:value.flags.rawValue);m.attributes=value.attributes;m.media=value.media;m.globallyUniqueId=value.globallyUniqueId;m.groupingKey=value.groupingKey;m.threadId=value.threadId;m.timestamp=value.timestamp;m.tags=value.tags;m.globalTags=value.globalTags;m.localTags=value.localTags;m.forwardInfo=value.forwardInfo.map{ForwardInfo(value:$0.value)};m.author=value.authorId.map(Peer.init);m.text=value.text;messages[id]=m;writes += 1}}
}
final class Postbox {
    let value=Transaction();var transactions=0;var beforeTransaction:(()->Void)?
    func transaction<V>(_ f:@escaping(Transaction)->V)->Signal<V,NoError>{Signal {subscriber in self.beforeTransaction?();self.transactions += 1;subscriber.putNext(f(self.value));subscriber.putCompletion();return EmptyDisposable}}
}
final class Account {let postbox=Postbox()}
enum TelegramEngine {final class Messages {let account:Account;init(_ account:Account){self.account=account}}}
final class DefaultsBoundary {
    static let shared=DefaultsBoundary();var values:[String:Bool]=[:]
    func bool(forKey key:String)->Bool {values[key] ?? false}
    func set(_ value:Bool,forKey key:String){values[key]=value}
}
struct NagramiXPrivacySettings {static var current:Self{.init()};let bypassScreenshots=false}
final class Atomic<Value> {var value:Value;init(_ value:Value){self.value=value};func with<R>(_ f:(Value)->R)->R{f(value)}}
final class SerialArchiveQueue {var deferred=false;var actions:[()->Void]=[];func async(_ f:@escaping()->Void){if deferred{actions.append(f)}else{f()}};func flush(){let old=actions;actions=[];old.forEach{$0()}}}
struct Record {let message:Message;var transcriptionAttributes:[Data]?;var messageId:MessageId{message.id};var wasTemporary:Bool{message.attributes.contains{($0 as? NagramiXArchivedMessageAttribute)?.isTemporary == true}}}
struct ArchiveState {var records:[String:Record]=[:]}
final class NagramiXMessageArchive {
    static var registry:[ObjectIdentifier:NagramiXMessageArchive]=[:]
    static func forPostbox(_ postbox:Postbox)->NagramiXMessageArchive? {registry[ObjectIdentifier(postbox)]}
    let state=Atomic(ArchiveState());let queue=SerialArchiveQueue();var published=0;var persistCalls=0;var allowPersist=true
    var mutationState:ArchiveState {state.value}
    static var codecs:[Int:PostboxCoding]=[:]
    static func encodedRootObject(_ value:PostboxCoding)->Data {let id=codecs.count+1;codecs[id]=value;return Data(String(id).utf8)}
    static func decode(_ value:Data)->MessageAttribute? {guard let key=Int(String(data:value,encoding:.utf8) ?? "") else{return nil};return codecs[key] as? MessageAttribute}
    func renderDeletedRecord(_ record:Record,requireCompleteMedia:Bool=true)->Message? {
        // Rendering and codecs are the bounded adapter, not the eligibility guard.
        guard nagramiXTemporaryMessagesEnabled() else{return nil}
        let m=record.message.copy();m.attributes=m.attributes.filter{!($0 is AudioTranscriptionMessageAttribute) && !($0 is DerivedDataMessageAttribute)}+(record.transcriptionAttributes ?? []).compactMap(Self.decode);return m
    }
    func persist(_ value:ArchiveState)->Bool {persistCalls += 1;if allowPersist{state.value=value};return allowPersist}
    func publishUpdate(){published += 1}
// REAL_ARCHIVE_METHODS
}
private var count=0
private func check(_ value:@autoclosure()->Bool,_ label:String){count += 1;if !value(){FileHandle.standardError.write(Data(("FAIL "+label+"\n").utf8));exit(91)}}
'''

ENGINE_TESTS = r'''
private let id=MessageId()
private func enable(_ on:Bool){DefaultsBoundary.shared.values=["nagramix.messages.saveTemporaryMessages":on,"nagramix.messages.replayViewOnce":false]}
private func fixture()->(Account,TelegramEngine.Messages,NagramiXMessageArchive){let account=Account();let archive=NagramiXMessageArchive();NagramiXMessageArchive.registry=[ObjectIdentifier(account.postbox):archive];return(account,TelegramEngine.Messages(account),archive)}
private func message(_ id:MessageId=id,temporary:Bool=true,expired:Bool=false)->Message {let m=Message();m.id=id;if temporary{m.attributes=[AutoremoveTimeoutMessageAttribute(10)]};if expired{m.media=[TelegramMediaExpiredContent()]};return m}
private func retain(_ archive:NagramiXMessageArchive,_ source:Message){let m=source.copy();m.attributes=[NagramiXArchivedMessageAttribute()];archive.state.value.records[NagramiXMessageArchive.key(m.id)]=Record(message:m)}
private func result(_ engine:TelegramEngine.Messages,_ id:MessageId=id,expected:Bool=true)->NagramiXTemporaryReplyResolution{var result:NagramiXTemporaryReplyResolution = .unavailable;engine.nagramiXResolveTemporaryReply(messageId:id,expectedTemporary:expected).start(next:{result=$0});return result}
private func native(_ value:NagramiXTemporaryReplyResolution)->Bool{if case .native=value{return true};return false}
private func unavailable(_ value:NagramiXTemporaryReplyResolution)->Bool{if case .unavailable=value{return true};return false}
private func copy(_ value:NagramiXTemporaryReplyResolution)->Message?{if case let .copy(message)=value{return message};return nil}
private func saved(_ archive:NagramiXMessageArchive,_ id:MessageId=id)->AudioTranscriptionMessageAttribute?{archive.state.value.records[NagramiXMessageArchive.key(id)]?.transcriptionAttributes?.compactMap(NagramiXMessageArchive.decode).compactMap{$0 as? AudioTranscriptionMessageAttribute}.first}
@main struct TemporaryEngineChecks {
 static func main(){
    for enabled in [false,true] {
        enable(enabled);let(a,e,ar)=fixture();let m=message();a.postbox.value.messages[id]=m;retain(ar,m)
        check(native(result(e)),"live native reply is preserved")
        check(a.postbox.value.writes==0 && ar.persistCalls==0,"preflight is read only")
        a.postbox.value.messages[id]=message(expired:true)
        if enabled{check(copy(result(e))?.id==id,"expired reply uses retained copy")}else{check(unavailable(result(e)),"OFF expired temporary reply unavailable")}
        a.postbox.value.messages.removeAll()
        if enabled{check(copy(result(e))?.text==m.text,"absent original uses full retained source")}else{check(unavailable(result(e)),"OFF absent temporary reply unavailable")}
        ar.state.value.records.removeAll()
        check(unavailable(result(e)),"cleared temporary reply never recreated")
        check(native(result(e,expected:false)),"unknown ordinary missing ID stays native")
        check(a.postbox.value.writes==0 && ar.persistCalls==0,"missing preflight never writes")
    }
    enable(true)
    let(a,e,ar)=fixture();let m=message();retain(ar,m)
    let request=e.nagramiXResolveTemporaryReply(messageId:id,expectedTemporary:true)
    check(a.postbox.transactions==0,"reply preflight is lazy")
    enable(false);var late:NagramiXTemporaryReplyResolution = .native;request.start(next:{late=$0})
    check(unavailable(late),"OFF before transaction rejects stale copy")
    enable(true);retain(ar,m);a.postbox.beforeTransaction={ar.state.value.records.removeAll()}
    check(unavailable(result(e)),"clear before transaction rejects stale copy")
    a.postbox.beforeTransaction=nil;retain(ar,m)
    var second=id;second.id=2;let other=message(second);other.text="other source";a.postbox.value.messages[second]=other
    check(copy(result(e))?.id==id,"reply cannot switch to another local source")
    check(native(result(e,second)),"new selected local source resolves its own live row")
    let secretId=MessageId(peerId:PeerId(namespace:Namespaces.Peer.SecretChat,value:90),namespace:Namespaces.Message.Local,id:9)
    let local=message(secretId);retain(ar,local)
    check(copy(result(e,secretId))?.id==secretId,"local-only secret retained target copies")
    a.postbox.value.messages[secretId]=local
    check(native(result(e,secretId)),"live secret local target keeps native reply")
    // Full experimental native ASR method, with the actual archive guard/transform.
    for incoming in [false,true] {
        enable(true);let(a,e,ar)=fixture();let live=message();live.flags=incoming ? [.Incoming] : [];a.postbox.value.messages[id]=live;retain(ar,live)
        let media=live.media[0];let oldText=live.text;let oldGroup=live.groupingKey
        e.storeLocallyTranscribedAudio(messageId:id,text:"partial",isFinal:false,error:nil).startStandalone()
        check(saved(ar)?.text=="partial" && saved(ar)?.isPending==true,"pending local ASR mirrors")
        e.storeLocallyTranscribedAudio(messageId:id,text:"completed",isFinal:true,error:nil).startStandalone()
        check(saved(ar)?.text=="completed" && saved(ar)?.isPending==false,"completed local ASR mirrors")
        e.storeLocallyTranscribedAudio(messageId:id,text:"old partial",isFinal:false,error:nil).startStandalone()
        check(saved(ar)?.text=="completed" && saved(ar)?.isPending==false,"late pending cannot replace completed local text")
        e.storeLocallyTranscribedAudio(messageId:id,text:"error",isFinal:true,error:.generic).startStandalone()
        check(saved(ar)?.text=="completed","failed ASR does not destroy retained text")
        let current=a.postbox.value.messages[id]!
        check(current.text==oldText && current.groupingKey==oldGroup && current.media[0] === media,"native ASR preserves original payload")
        check(current.timestamp==live.timestamp && current.threadId==live.threadId && current.flags==live.flags && current.forwardInfo?.value==live.forwardInfo?.value,"native ASR preserves message metadata")
        ar.queue.deferred=true
        e.storeLocallyTranscribedAudio(messageId:id,text:"late after clear",isFinal:true,error:nil).startStandalone()
        ar.state.value.records.removeAll();ar.queue.flush()
        check(ar.state.value.records.isEmpty,"late ASR never recreates cleared archive")
        retain(ar,live)
        e.storeLocallyTranscribedAudio(messageId:id,text:"late after off",isFinal:true,error:nil).startStandalone()
        enable(false);ar.queue.flush()
        check(saved(ar)==nil,"OFF rejects late mirror")
        enable(true);ar.queue.deferred=false;ar.allowPersist=false
        e.storeLocallyTranscribedAudio(messageId:id,text:"not persisted",isFinal:true,error:nil).startStandalone()
        check(saved(ar)==nil,"failed persistence not published as saved text")
    }
    enable(true);let(_,e2,ar2)=fixture();let retained=message();retain(ar2,retained)
    e2.storeLocallyTranscribedAudio(messageId:id,text:"server original gone",isFinal:true,error:nil).startStandalone()
    check(saved(ar2)?.text=="server original gone","retained mirror survives original absent from Postbox")
    check(ar2.state.value.records.count==1,"mirror never inserts unrelated record")
    print("PASS temporary engine production checks: \(count)")
 }
}
'''


def stripped(text):
    return '\n'.join(line for line in text.splitlines() if not line.startswith('import ')).replace('public ', '')


def engine_harness(texts, variant=None):
    local, engine, archive, policy = texts[LOCAL], texts[ENGINE], texts[ARCHIVE], texts[POLICY]
    resolver = block(local, '    func nagramiXResolveTemporaryReply(')
    store = block(engine, '        public func storeLocallyTranscribedAudio(').replace('public ', '')
    archive_methods = '\n'.join(block(archive, marker).replace('private ', '').replace('public ', '') for marker in [
        '    private static func key(', '    private static func isRegularArchiveIdentifier(',
        '    public func temporaryInteractionMessage(', '    public func updateTranscriptionAttributes(', '    func retainTelegramTranscription('])
    if variant=='preflight_off_bypass':
        resolver=resolver.replace('return expectsTemporary ? .unavailable : .native', 'return .native', 1)
    if variant=='mirror_missing':
        store=store.replace('                NagramiXMessageArchive.forPostbox(self.account.postbox)?.retainTelegramTranscription(id: messageId, attribute: AudioTranscriptionMessageAttribute(id: 0, text: text, isPending: !isFinal, didRate: false, error: error))','')
    if variant=='pending_overwrite':
        archive_methods=archive_methods.replace('            if attribute.isPending, current.attributes.contains(where: {','            if false, current.attributes.contains(where: {')
    if variant=='off_archive_write':
        # Rendering is a boundary; this mutation specifically removes the real
        # Core policy decision in the public update guard.
        archive_methods=archive_methods.replace('nagramiXCanTranscribeTemporaryMedia(current),','true,')
    boundary=ENGINE_BOUNDARY.replace('// REAL_ARCHIVE_METHODS',archive_methods)
    if variant=='off_archive_write':
        boundary=boundary.replace('        guard nagramiXTemporaryMessagesEnabled() else{return nil}','')
    enum=block(local,'public enum NagramiXTemporaryReplyResolution').replace('public ', '')
    return boundary+stripped(policy).replace('UserDefaults.standard','DefaultsBoundary.shared')+'\n'+enum+'\nextension TelegramEngine.Messages {\n'+resolver+'\n'+store+'\n}\n'+ENGINE_TESTS


ROUTE_TESTS = r'''
private var checks=0
private func check(_ value:@autoclosure()->Bool,_ label:String){checks += 1;if !value(){FileHandle.standardError.write(Data(("FAIL "+label+"\n").utf8));exit(91)}}
func nagramiXCanPlayTemporaryVoiceInline(_ message:Message)->Bool {temporaryEnabled && message.minAutoremoveOrClearTimeout != nil && (message.media.first as? TelegramMediaFile)?.isVoice==true && (message.media.first as? TelegramMediaFile)?.isInstantVideo==false}
func nagramiXCanTranscribeTemporaryMedia(_ message:Message)->Bool {temporaryEnabled && message.minAutoremoveOrClearTimeout != nil && ((message.media.first as? TelegramMediaFile)?.isVoice==true || (message.media.first as? TelegramMediaFile)?.isInstantVideo==true)}
func nagramiXCanRetainTemporaryMessage(_ message:Message)->Bool {temporaryEnabled && message.minAutoremoveOrClearTimeout != nil}
func nagramiXCanUseTemporaryMediaActions(_ message:Message)->Bool {nagramiXCanRetainTemporaryMessage(message)}
private var temporaryEnabled=false
// GALLERY_BOUNDARY
// NATIVE_ROUTES
@main struct TemporaryRouteChecks {
 static func main(){
    for enabled in [false,true] {
     temporaryEnabled=enabled
     for archived in [false,true] {
      for incoming in [false,true] {
       for kind in [0,1,2] {
        let message=Message();message.flags=incoming ? [.Incoming] : []
        let file=TelegramMediaFile();file.isVoice=kind==0;file.isInstantVideo=kind==1;message.media=kind==2 ? [TelegramMediaImage()] : [file]
        if archived{message.attributes=[NagramiXArchivedMessageAttribute(true)]}
        let chat=ChatControllerImpl();chat.openViewOnceMediaMessage(EngineMessage(raw:message))
        check(chat.context.sharedContext.opened.count==1,"one actual open call")
        let supported=kind==0 || kind==1
        if enabled && supported {
         check(chat.overlays.isEmpty,"approved voice/round bypasses one-time context")
         check(chat.context.sharedContext.opened[0].standalone==archived,"retained open standalone matches archive")
         switch chat.context.sharedContext.opened[0].playlistLocation {
          case let .singleMessage(mid):check(!archived && mid==message.id,"live normal playlist uses original ID")
          case let .recentActions(snapshot):check(archived && snapshot===message,"retained normal playlist owns selected snapshot")
         }
        }else{
         check(chat.overlays.count==1,"OFF/other media native overlay unchanged")
         check(!chat.context.sharedContext.opened[0].standalone,"native single-message open stays native")
        }
        check(!message.consumed && !message.deleted,"opening route itself never consumes or deletes")
        let blocked=ChatControllerImpl();blocked.screenCaptureManager?.isRecordingActive=true;blocked.openViewOnceMediaMessage(EngineMessage(raw:message))
        check(blocked.alerts==1 && blocked.context.sharedContext.opened.isEmpty,"native screen-recording protection preserved")
       }
      }
     }
     for supplied in [false,true] {
      for standalone in [false,true] {
       for secret in [false,true] {
        let m=Message();if !secret{m.minAutoremoveOrClearTimeout=nil}
        let provided:GalleryControllerItemSource?=supplied ? .provided(44) : nil
        let now=galleryRoute(m,standalone:standalone,source:provided)
        let previous=previousGalleryRoute(m,standalone:standalone,source:provided)
        if enabled && secret {
         check(!now.secret,"retained secret media uses standard gallery")
         if case let .standaloneMessage(snapshot,_)=now.source {check(snapshot===m,"gallery keeps actual selected snapshot")}else{check(false,"temporary gallery standalone overrides provided source")}
        }else{
         check(now.secret==previous.secret,"ordinary/OFF secret viewer choice unchanged")
         check(now.source.tag==previous.source.tag,"ordinary/OFF gallery source unchanged")
        }
        for setup in [false,true] {
         let a=roundRoute(m,didSetupFileNode:setup),b=previousRoundRoute(m,didSetupFileNode:setup)
         if enabled && secret{check(!a,"retained round uses ordinary playback layout")}
         else{check(a==b,"ordinary/OFF round force-playing unchanged")}
        }
       }
      }
     }
    }
    print("PASS temporary opening production checks: \(checks)")
 }
}
'''

GALLERY_BOUNDARY = r'''
enum GalleryMediaSubject {case document}
struct ChatLocation {let peerId:PeerId;static func peer(id:PeerId)->Self{.init(peerId:id)}}
struct ChatLocationContextHolder {}
struct Atomic<Value> {let value:Value;init(value:Value){self.value=value}}
enum GalleryControllerItemSource {
 case standaloneMessage(Message,GalleryMediaSubject?)
 case peerMessagesAtId(messageId:MessageId,chatLocation:ChatLocation,customTag:Int?,chatLocationContextHolder:Atomic<ChatLocationContextHolder?>)
 case provided(Int)
 var tag:String {switch self{case .standaloneMessage:return "standalone";case .peerMessagesAtId:return "peer";case .provided:return "provided"}}
}
'''


def route_function(text, name):
    start=text.index('    var standalone = standalone',text.index('public func chatMessageGalleryControllerData('))
    stop=text.index('    var candidateMedia',start)
    preparation=text[start:stop]
    condition='message.containsSecretMedia && !nagramiXTemporaryInteraction' if 'else if message.containsSecretMedia && !nagramiXTemporaryInteraction {' in text else 'message.containsSecretMedia'
    marker='                    let gallery = GalleryController(context: context, source: '
    expression=text[text.index(marker,text.index('let isInChatLocationHistory:'))+len(marker):]
    expression=expression[:expression.index(', invertItemOrder:')]
    return f'''func {name}(_ message:Message,standalone:Bool,source:GalleryControllerItemSource?)->(secret:Bool,source:GalleryControllerItemSource) {{
    let mediaSubject:GalleryMediaSubject?=nil
    let openChatLocation=ChatLocation.peer(id:message.id.peerId)
    let chatFilterTag:Int?=nil
    let openChatLocationContextHolder=Atomic<ChatLocationContextHolder?>(value:nil)
{preparation}
    let selected:GalleryControllerItemSource={expression}
    return ({condition},selected)
}}\n'''


def opening_harness(texts, before, variant=None):
    opening=block(texts[OPEN],'func openViewOnceMediaMessage(')
    gallery=texts[GALLERY]
    round_text=texts[ROUND]
    if variant=='round_one_time_window':
        opening=opening.replace(' || nagramiXCanTranscribeTemporaryMedia(message._asMessage())','')
    if variant=='temporary_secret_gallery':
        gallery=gallery.replace('else if message.containsSecretMedia && !nagramiXTemporaryInteraction {','else if message.containsSecretMedia {')
    if variant=='lost_standalone_snapshot':
        gallery=gallery.replace('nagramiXTemporaryInteraction ? .standaloneMessage(message, mediaSubject) : (source ??','false ? .standaloneMessage(message, mediaSubject) : (source ??')
    boundary=(ROOT/'scripts/tests/NagramiXInlineTemporaryVoiceBoundary.swift').read_text().split('struct PlaybackStatus {')[0]
    # The existing full-opener UIKit boundary owns the real 13.2 initializer labels.
    routes=route_function(gallery,'galleryRoute')+route_function(before[GALLERY],'previousGalleryRoute')
    for code,name in [(round_text,'roundRoute'),(before[ROUND],'previousRoundRoute')]:
        a=code.index('            let isViewOnceMessage = item.message.minAutoremoveOrClearTimeout == viewOnceTimeout')
        b=code.index('\n            var incoming =',a)
        body=code[a:b].replace('item.message','message')
        routes+=f'func {name}(_ message:Message,didSetupFileNode:Bool)->Bool{{\n{body}\nreturn forceIsPlaying\n}}\n'
    tests=ROUTE_TESTS.replace('// GALLERY_BOUNDARY',GALLERY_BOUNDARY).replace('// NATIVE_ROUTES',routes)
    return boundary+'\nextension ChatControllerImpl {\n'+opening+'\n}\n'+tests


def verify_native_rest(texts,before):
    # New route expressions must not replace native implementations elsewhere.
    engine_before=before[ENGINE];engine_after=texts[ENGINE]
    mirror='''                // Mirror only into an existing approved retained record. The
                // archive rejects OFF/clear races and never recreates a row.
                NagramiXMessageArchive.forPostbox(self.account.postbox)?.retainTelegramTranscription(id: messageId, attribute: AudioTranscriptionMessageAttribute(id: 0, text: text, isPending: !isFinal, didRate: false, error: error))
'''
    assert engine_after.count(mirror)==1 and engine_after.replace(mirror,'')==engine_before,'Native engine changed outside ASR mirror'
    assert texts[OPEN].replace(' || nagramiXCanTranscribeTemporaryMedia(message._asMessage())','')==before[OPEN],'Native open method changed outside route admission'
    assert texts[ROUND].replace(' && !nagramiXCanUseTemporaryMediaActions(item.message)','')==before[ROUND],'Native round layout changed outside approved predicate'
    gallery=texts[GALLERY]
    prefix='''    let nagramiXTemporaryInteraction = nagramiXCanRetainTemporaryMessage(message)
    if nagramiXTemporaryInteraction {
        // Retained/one-time media may be absent from the ordinary shared-media
        // index. Keep the actual selected file available without a TTL viewer.
        standalone = true
    }
'''
    assert gallery.count(prefix)==1
    gallery=gallery.replace(prefix,'').replace('message.containsSecretMedia && !nagramiXTemporaryInteraction','message.containsSecretMedia')
    new='nagramiXTemporaryInteraction ? .standaloneMessage(message, mediaSubject) : (source ?? (standalone ? .standaloneMessage(message, mediaSubject) : .peerMessagesAtId(messageId: message.id, chatLocation: openChatLocation, customTag: chatFilterTag, chatLocationContextHolder: openChatLocationContextHolder)))'
    old='source ?? (standalone ? .standaloneMessage(message, mediaSubject) : .peerMessagesAtId(messageId: message.id, chatLocation: openChatLocation, customTag: chatFilterTag, chatLocationContextHolder: openChatLocationContextHolder))'
    assert gallery.count(new)==1 and gallery.replace(new,old)==before[GALLERY],'Native gallery changed outside preservation route'
    local=texts[LOCAL]
    enum_start=local.index('/// A local send preflight;')
    enum_end=local.index('\npublic extension TelegramEngine.Messages',enum_start)
    local=local[:enum_start]+local[enum_end+1:]
    method_start=local.index('    /// Resolve the current reply target')
    method_end=local.index('    /// Snapshot deletion ownership',method_start)
    assert local[:method_start]+local[method_end:]==before[LOCAL],'Existing engine helpers changed'


def run(texts,before,swiftc,temp):
    def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    result=[];negative=[]
    suites=[('engine',engine_harness,{'preflight_off_bypass':'OFF expired temporary reply unavailable','mirror_missing':'pending local ASR mirrors','pending_overwrite':'late pending cannot replace completed local text','off_archive_write':'OFF rejects late mirror'}),
            ('opening',lambda data,variant=None:opening_harness(data,before,variant),{'round_one_time_window':'approved voice/round bypasses one-time context','temporary_secret_gallery':'retained secret media uses standard gallery','lost_standalone_snapshot':'temporary gallery standalone overrides provided source'})]
    for optimized in [False,True]:
      mode='optimized' if optimized else 'debug'
      for label,builder,variants in suites:
       for variant in [None,*variants]:
        text=builder(texts,variant)
        file=temp/(label+'-'+mode+'-'+(variant or 'production')+'.swift');binary=file.with_suffix('');file.write_text(text)
        command=[str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache'),str(file),'-o',str(binary)]
        if optimized:command.insert(1,'-O')
        compiled=subprocess.run(command,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        assert compiled.returncode==0,compiled.stdout
        completed=subprocess.run([str(binary)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,preexec_fn=no_core)
        if variant:
         assert completed.returncode==91 and ('FAIL '+variants[variant]) in completed.stdout,(variant,completed.returncode,completed.stdout)
         negative.append({'mode':mode,'suite':label,'variant':variant})
        else:
         assert completed.returncode==0 and 'PASS temporary' in completed.stdout,completed.stdout
         result.append({'mode':mode,'suite':label,'result':completed.stdout.strip()})
    return result,negative


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--baseline',type=Path);parser.add_argument('--policy-root',type=Path);parser.add_argument('--archive-root',type=Path);parser.add_argument('--swiftc',type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args()
    texts={n:(args.source/n).read_text() for n in PATHS}
    texts[POLICY]=((args.policy_root or args.source)/POLICY).read_text();texts[ARCHIVE]=((args.archive_root or args.source)/ARCHIVE).read_text()
    if args.baseline:before={n:(args.baseline/n).read_text() for n in PATHS}
    else:
      plan=json.loads((ROOT/'ios/temporary_message_interaction_patches.json').read_text());before={}
      for name in PATHS:
       p=ROOT/'ios'/plan['previous'][name];assert hashlib.sha256(p.read_bytes()).hexdigest()==plan['inputs'][name];before[name]=p.read_text()
    verify_native_rest(texts,before)
    with tempfile.TemporaryDirectory(prefix='temporary-engine-opening-') as folder:
      temp=Path(folder);runs,negative=run(texts,before,args.swiftc,temp) if args.swiftc else ([],[])
      if args.swiftc:
       for i,name in enumerate(PATHS):
        p=temp/('parse-'+str(i)+'.swift');p.write_text(texts[name]);subprocess.run([str(args.swiftc),'-frontend','-parse',str(p)],check=True)
    report={'production_runs':runs,'semantic_negative_runs':negative,'full_swift_parse_files':len(PATHS) if args.swiftc else 0,'source_sha256':{n:hashlib.sha256(t.encode()).hexdigest() for n,t in texts.items()},'native_rest':'Five full files restored byte-exact after removing only the agreed new enum/preflight/mirror/route expressions','boundaries':'Actual reply transaction, native storeLocallyTranscribedAudio, archive public guards/transforms, full view-once open method and gallery/round route expressions execute. Postbox scheduling, archive serialization/rendering/persistence, UIKit/AVKit, and policy for opening routes are explicit adapters. Core policy executes in engine suite. No account, network, consume, read receipt or Apple SDK invoked.','apple_sdk':'pending','physical_device':'pending'}
    if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
