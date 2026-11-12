"""Настоящий commit editMessage, native API getters и pending manager; явные transport/Postbox doubles."""
from validate_quick_format import block
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EDIT='submodules/TelegramCore/Sources/PendingMessages/RequestEditMessage.swift'
UTIL='submodules/TelegramCore/Sources/State/UpdatesApiUtils.swift'
MANAGER='submodules/TelegramCore/Sources/PendingMessages/PendingUpdateMessageManager.swift'
MEDIA='submodules/TelegramCore/Sources/PendingMessages/ChatUpdatingMessageMedia.swift'

def fixture(source,original=False):
    text=(source/EDIT).read_text()
    if original:
        import json
        plan=json.loads((ROOT/'ios/edit_result_consistency_patches.json').read_text());text=(ROOT/'ios'/plan['previous'][EDIT]).read_text()
    enums='\n'.join(block(text,marker) for marker in ['public enum RequestEditMessageMedia','public enum RequestEditMessageResult','public enum RequestEditMessageError'])
    accepted=block(text,'                        return postbox.transaction { transaction -> RequestEditMessageResult in')
    utils=(source/UTIL).read_text()
    getters='\n'.join(block(utils,marker) for marker in ['    var allUpdates:','    var users: [Api.User] {','    var messages: [Api.Message] {','    var chats: [Api.Chat] {'])
    update_message=block(utils,'    var message: Api.Message? {')
    pending=(source/MANAGER).read_text();prefix=pending[:pending.index('\npublic final class PendingUpdateMessageManager {')]
    convenience=block(prefix,'    convenience init(queue: Queue, postbox: Postbox,');prefix=prefix.replace(convenience,'',1)
    clean=lambda s:'\n'.join(x for x in s.splitlines() if not x.startswith('import ')).replace('public ','')
    return 'import Foundation\n'+BOUNDARY+clean(enums)+'\nextension Api.Updates {\n'+getters+'\n}\nextension Api.Update {\n'+update_message+'\n}\n'+clean((source/MEDIA).read_text())+'\n'+clean(prefix)+'''
func applyAccepted(_ result:Api.Updates,postbox:Postbox,stateManager:AccountStateManager,media:RequestEditMessageMedia = .keep,richText:RichTextMessageAttribute?=nil)->Signal<RequestEditMessageResult,NoError> {
 let accountPeerId=1;let peer=Peer()
'''+accepted+'\n}\n'+TESTS

BOUNDARY=r'''
// These are explicit deterministic storage / RPC / queue adapters. No UIKit,
// real Telegram connection or physical-device behavior is claimed by this test.
typealias MessageId=Int;typealias MediaId=Int;typealias TransformOutgoingMessageMedia=Int
protocol Media:AnyObject{}
final class TestMedia:Media {let name:String;init(_ name:String){self.name=name}}
final class TelegramMediaPaidContent:Media {enum Extended {case full,preview};var extendedMedia:[Extended];init(full:Bool){extendedMedia=full ? [.full]:[.preview]}}
struct AnyMediaReference:Equatable {var media:Media;static func ==(a:Self,b:Self)->Bool{a.media === b.media}}
protocol MessageAttribute:AnyObject{}
final class RichTextMessageAttribute:NSObject,MessageAttribute {let resource:String;init(_ resource:String){self.resource=resource}}
final class TextEntitiesMessageAttribute:NSObject,MessageAttribute {}
final class InvertMediaMessageAttribute:NSObject,MessageAttribute {}
final class WebpagePreviewMessageAttribute:NSObject,MessageAttribute {}
struct MessageFlags:OptionSet {let rawValue:Int;static let Incoming=Self(rawValue:1)}
struct LocalTags:OptionSet {let rawValue:Int;static let OutgoingLiveLocation=Self(rawValue:1);static let Other=Self(rawValue:2)}
struct StoreMessage {
 enum Id {case Id(Int)}
 var id:Id;var text:String;var flags:MessageFlags;var localTags:LocalTags;var media:[Media];var attributes:[MessageAttribute]
 init(_ id:Int,text:String,flags:MessageFlags=[],tags:LocalTags=[],media:[Media]=[],attributes:[MessageAttribute]=[]){self.id = .Id(id);self.text=text;self.flags=flags;self.localTags=tags;self.media=media;self.attributes=attributes}
 init?(apiMessage:Api.Message,accountPeerId:Int,peerIsForum:Bool){guard let message=apiMessage.payload else{return nil};self=message}
 func withUpdatedFlags(_ value:MessageFlags)->Self {var v=self;v.flags=value;return v}
 func withUpdatedLocalTags(_ value:LocalTags)->Self {var v=self;v.localTags=value;return v}
 func withUpdatedMedia(_ value:[Media])->Self {var v=self;v.media=value;return v}
}
// Nominal payload adapters expose the actual fields consumed by the copied
// native getters. TL encoding/transport are outside this fixture.
enum Api {
 struct User {var id:Int};struct Chat {var id:Int};struct Message {var payload:StoreMessage?}
 enum Update {
  struct Cons_message {var message:Message}
  case updateEditMessage(Cons_message),updateNewMessage(Cons_message),updateEditChannelMessage(Cons_message),updateNewChannelMessage(Cons_message),updateNewScheduledMessage(Cons_message),updateQuickReplyMessage(Cons_message),other
 }
 enum Updates {
  struct Cons_updates {var updates:[Update];var users:[User];var chats:[Chat]}
  struct Cons_updateShort {var update:Update}
  case updates(Cons_updates),updatesCombined(Cons_updates),updateShort(Cons_updateShort),updatesTooLong
 }
}
final class Peer {var isForumOrMonoForum=false}
enum StoreMessageUpdate {case update(StoreMessage)}
final class Transaction {
 var messages:[Int:StoreMessage];var peerIds:[Int]=[]
 init(_ messages:[Int:StoreMessage]){self.messages=messages}
 func updateMessage(_ id:Int,update:(StoreMessage)->StoreMessageUpdate){guard let previous=messages[id] else{return};if case let .update(value)=update(previous){messages[id]=value}}
}
final class Postbox {
 let transactionValue:Transaction;var commits=0;var resourceChanges:[String]=[]
 init(_ messages:[Int:StoreMessage]){transactionValue=Transaction(messages)}
 func transaction<T>(_ body:@escaping(Transaction)->T)->Signal<T,NoError>{Signal {s in let value=body(self.transactionValue);self.commits+=1;s.putNext(value);s.putCompletion();return EmptyDisposable}}
}
struct AccumulatedPeers {var ids:[Int];init(transaction:Transaction,chats:[Api.Chat],users:[Api.User]){ids=chats.map{$0.id}+users.map{$0.id}}}
func updatePeers(transaction:Transaction,accountPeerId:Int,peers:AccumulatedPeers){transaction.peerIds+=peers.ids}
func applyMediaResourceChanges(from:Media,to:Media,postbox:Postbox,force:Bool){precondition(force);postbox.resourceChanges.append("media")}
func applyMediaResourceChanges(from:RichTextMessageAttribute,to:RichTextMessageAttribute,postbox:Postbox,force:Bool){precondition(force);postbox.resourceChanges.append("rich")}
final class AccountStateManager {var queued:[Api.Updates]=[];func addUpdates(_ value:Api.Updates){queued.append(value)}}
enum NoError {}
protocol Disposable:AnyObject {func dispose()}
final class ActionDisposable:Disposable {var action:(()->Void)?;init(_ action:@escaping()->Void){self.action=action};func dispose(){let a=action;action=nil;a?()}}
let EmptyDisposable:Disposable=ActionDisposable{}
final class MetaDisposable:Disposable {var item:Disposable?;var disposed=false;func set(_ value:Disposable?){if disposed{value?.dispose()}else{item?.dispose();item=value}};func dispose(){disposed=true;item?.dispose();item=nil}}
final class Subscriber<T,E>{let next:(T)->Void;let error:(E)->Void;let completed:()->Void;var active=true
 init(_ next:@escaping(T)->Void,_ error:@escaping(E)->Void,_ completed:@escaping()->Void){self.next=next;self.error=error;self.completed=completed}
 func putNext(_ value:T){if active{next(value)}};func putError(_ value:E){if active{active=false;error(value)}};func putCompletion(){if active{active=false;completed()}}
}
final class Signal<T,E> {
 let generator:(Subscriber<T,E>)->Disposable
 init(_ generator:@escaping(Subscriber<T,E>)->Disposable){self.generator=generator}
 func start(next:@escaping(T)->Void={_ in},error:@escaping(E)->Void={_ in},completed:@escaping()->Void={})->Disposable{let s=Subscriber(next,error,completed);let d=generator(s);return ActionDisposable{s.active=false;d.dispose()}}
 static func single(_ value:T)->Signal<T,E>{Signal{s in s.putNext(value);s.putCompletion();return EmptyDisposable}}
}
final class Queue {var work:[()->Void]=[];func async(_ body:@escaping()->Void){work.append(body)};func drain(){while !work.isEmpty{work.removeFirst()()}}}
infix operator |> : AdditionPrecedence
func |> <T,U>(value:T,f:(T)->U)->U{f(value)}
func deliverOn<T,E>(_ queue:Queue)->(Signal<T,E>)->Signal<T,E> {
 return { signal in
  return Signal { subscriber in
   return signal.start(next: { value in queue.async {subscriber.putNext(value)} }, error: {error in queue.async {subscriber.putError(error)} }, completed: {queue.async {subscriber.putCompletion()} })
  }
 }
}
final class Promise<T>{var value:T?;var listeners:[(T)->Void]=[];func set(_ signal:Signal<T,NoError>){_ = signal.start(next:{v in self.value=v;for l in self.listeners{l(v)}})};func get()->Signal<T,NoError>{Signal{s in self.listeners.append{s.putNext($0)};if let v=self.value{s.putNext(v)};return EmptyDisposable}}}
final class ValuePipe<T>{var listeners:[(T)->Void]=[];func putNext(_ value:T){for l in listeners{l(value)}};func signal()->Signal<T,NoError>{Signal{s in self.listeners.append{s.putNext($0)};return EmptyDisposable}}}
final class RPCSource {var next:((RequestEditMessageResult)->Void)?;var error:((RequestEditMessageError)->Void)?;var complete:(()->Void)?;var result:((Api.Updates)->Void)?;var disposed=false;var disposalCount=0}
final class EditFixture {
 let queue=Queue();let postbox:Postbox;let state=AccountStateManager()
 var manager:PendingUpdateMessageManagerImpl!;var sources:[RPCSource]=[];var snapshots:[String]=[];var results:[String]=[];var errors=0
 var latest:[Int:ChatUpdatingMessageMedia]=[:]
 init(original:StoreMessage) {
  postbox=Postbox([1:original]);let postbox=self.postbox;let state=self.state
  manager=PendingUpdateMessageManagerImpl(queue:queue,makeRequest:{[weak self] request,_ in
   let source=RPCSource();self?.sources.append(source)
   return Signal{s in
    source.next={s.putNext($0)};source.error={s.putError($0)};source.complete={s.putCompletion()}
    source.result={value in guard !source.disposed else{return};_ = applyAccepted(value,postbox:postbox,stateManager:state,media:request.value.media,richText:request.value.richText).start(next:{s.putNext($0)},completed:{s.putCompletion()})}
    return ActionDisposable{source.disposed=true;source.disposalCount+=1}
   }
  })
  _ = manager.updatingMessageMedia.start(next:{[weak self] values in guard let self else{return};self.latest=values;self.snapshots.append(values[1]?.text ?? self.postbox.transactionValue.messages[1]!.text)})
  _ = manager.errors.start(next:{[weak self] _ in self?.errors+=1})
 }
 func add(_ text:String){manager.add(messageId:1,text:text,media:.keep,entities:nil,richText:nil,inlineStickers:[:],webpagePreviewAttribute:nil,invertMediaAttribute:nil,disableUrlPreview:false,completion:{[weak self] result in
  switch result {case .applied:self?.results.append("applied");case .unconfirmed:self?.results.append("unconfirmed");case .failed:self?.results.append("failed");case .superseded:self?.results.append("superseded");case .cancelled:self?.results.append("cancelled");case .interrupted:self?.results.append("interrupted")}
 })}
 func finish(_ index:Int,_ result:Api.Updates){sources[index].result?(result);queue.drain()}
}
'''
TESTS=r'''
@main struct EditResultTests {
 static func main(){
  var checks=0
  func check(_ value:@autoclosure()->Bool,_ why:String){if !value(){FileHandle.standardError.write(Data(("Edit result regression: "+why+"\n").utf8));exit(96)};checks+=1}
  let constructors:[(Api.Message)->Api.Update] = [{.updateEditMessage(.init(message:$0))},{.updateNewMessage(.init(message:$0))},{.updateEditChannelMessage(.init(message:$0))},{.updateNewChannelMessage(.init(message:$0))}]
  let containers:[([Api.Update])->Api.Updates] = [{.updates(.init(updates:$0,users:[.init(id:7)],chats:[.init(id:8)]))},{.updatesCombined(.init(updates:$0,users:[.init(id:7)],chats:[.init(id:8)]))},{.updateShort(.init(update:$0[0]))}]
  for (containerIndex,container) in containers.enumerated() {for construct in constructors {for incoming in [true,false] {for preservePaid in [true,false] {
   let paid=TelegramMediaPaidContent(full:preservePaid)
   let original=StoreMessage(1,text:"original",flags:incoming ? [.Incoming]:[],tags:[.OutgoingLiveLocation],media:preservePaid ? [paid]:[])
   let f=EditFixture(original:original)
   f.add("changed")
   check(f.snapshots.last=="changed" && f.results.isEmpty,"pending edit is visible without network acceptance")
   f.queue.drain();check(f.results.isEmpty && f.state.queued.isEmpty,"no network response keeps pending draft")
   f.sources[0].next?(.progress(0.7));f.queue.drain();check(f.snapshots.last=="changed","progress preserves pending text")
   let serverMedia=TestMedia("remote")
   let server=StoreMessage(1,text:"changed",flags:incoming ? []:[.Incoming],tags:[.Other],media:[serverMedia])
   f.finish(0,container([construct(.init(payload:server))]))
   check(f.results==["applied"] && f.latest.isEmpty,"native pending result emitted once")
   check(f.postbox.transactionValue.messages[1]?.text=="changed","accepted edit is stored before pending disappears")
   check(f.snapshots.last=="changed" && !f.snapshots.dropFirst().contains("original"),"no old-text flash while global updates wait")
   check(f.state.queued.count==1 && f.postbox.commits==1,"global updates still queued exactly once")
   let stored=f.postbox.transactionValue.messages[1]!
   check(stored.flags.contains(.Incoming)==incoming,"original incoming direction retained")
   check(stored.localTags.contains(.OutgoingLiveLocation) && stored.localTags.contains(.Other),"live location and server local tags retained")
   check(preservePaid ? stored.media.first === paid : stored.media.first === serverMedia,"full paid content remains available")
   check(containerIndex==2 ? f.postbox.transactionValue.peerIds.isEmpty : Set(f.postbox.transactionValue.peerIds)==[7,8],"native peers are updated for container payload")
   check(f.sources[0].disposalCount==1,"completed native request disposed once")
  }}}}
  let f=EditFixture(original:StoreMessage(1,text:"original"));f.add("first");f.add("second")
  check(f.results==["superseded"] && f.snapshots.last=="second","replacement keeps latest pending edit")
  f.finish(0,containers[1]([constructors[0](.init(payload:StoreMessage(1,text:"first")))]))
  check(f.snapshots.last=="second" && f.postbox.transactionValue.messages[1]?.text=="original","disposed request cannot apply late")
  f.finish(1,containers[1]([constructors[0](.init(payload:StoreMessage(1,text:"second")))]))
  check(f.snapshots.last=="second" && f.results==["superseded","applied"],"replacement confirmation keeps latest text")
  let failed=EditFixture(original:StoreMessage(1,text:"original"));failed.add("unsaved");failed.sources[0].error?(.restricted);failed.queue.drain()
  check(failed.results==["failed"] && failed.errors==1 && failed.postbox.transactionValue.messages[1]?.text=="original","server refusal remains an error without fabricating success")
  let unconfirmed=EditFixture(original:StoreMessage(1,text:"original"));unconfirmed.add("draft");unconfirmed.sources[0].next?(.done(false));unconfirmed.queue.drain()
  check(unconfirmed.results==["unconfirmed"],"done false is not acceptance")
  for container in containers {
   let box=Postbox([1:StoreMessage(1,text:"original")]);let manager=AccountStateManager()
   let from=TestMedia("local");let to=TestMedia("server");let sourceRich=RichTextMessageAttribute("local rich");let targetRich=RichTextMessageAttribute("server rich")
   let server=StoreMessage(1,text:"caption",media:[to],attributes:[targetRich])
   _ = applyAccepted(container([constructors[0](.init(payload:server))]),postbox:box,stateManager:manager,media:.update(.init(media:from)),richText:sourceRich).start()
   check(box.resourceChanges==["media","rich"] && box.transactionValue.messages[1]?.text=="caption","media and rich resource mappings preserved")
   let missing=Postbox([:]);_ = applyAccepted(container([constructors[0](.init(payload:server))]),postbox:missing,stateManager:AccountStateManager()).start()
   check(missing.transactionValue.messages.isEmpty,"missing message is not created by edit result")
  }
  let untouched=Postbox([1:StoreMessage(1,text:"original")]);let state=AccountStateManager()
  _ = applyAccepted(.updatesTooLong,postbox:untouched,stateManager:state).start()
  check(untouched.transactionValue.messages[1]?.text=="original" && state.queued.count==1,"unsupported payload still goes through native global handling")
  print("Edit result production checks: \(checks)")
 }
}
'''


def negatives(code):
    variants=[('missing-combined','case let .updatesCombined(updatesCombinedData):\n            let updates = updatesCombinedData.updates\n            return updates','case .updatesCombined:\n            return []','accepted edit is stored before pending disappears'),('missing-short','return [update]','_ = update; return []','accepted edit is stored before pending disappears'),('drop-peers','updatePeers(transaction: transaction, accountPeerId: accountPeerId, peers: peers)','_ = peers','native peers are updated for container payload'),('drop-incoming','updatedFlags.insert(.Incoming)','updatedFlags.remove(.Incoming)','original incoming direction retained'),('drop-paid-media','updatedMedia = previousMessage.media','updatedMedia = message.media','full paid content remains available')]
    for name,old,new,label in variants:
        assert old in code,name
        yield name,code.replace(old,new),label
