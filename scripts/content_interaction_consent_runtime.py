"""Исполнение настоящих политик, JSON-архива, producer и queued filters."""
from validate_quick_format import block
from validate_temporary_interaction_archive import clean,ARCHIVE,POLICY
import temporary_playback_identity_runtime as identity
import validate_temporary_interaction_consumption as receipts

MARK=receipts.MARK
MANAGED=receipts.CORE+'State/ManagedSynchronizeConsumeMessageContentsOperations.swift'
SECRET=receipts.SECRET
ENGINE=receipts.CORE+'TelegramEngine/Messages/TelegramEngineMessages.swift'
MENU='submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift'


def archive(source):
    text=identity.archive(source)
    text=text[:text.index('@main struct PlaybackIdentityArchiveTests')]
    text=text.replace('struct Disposable {}','struct Disposable {var cancel:(()->Void)?=nil;func dispose(){cancel?()}}\nfunc ActionDisposable(_ cancel:@escaping()->Void)->Disposable{Disposable(cancel:cancel)}')
    text+='\nextension Message {\n'+clean(block((source/'submodules/Postbox/Sources/Message.swift').read_text(),'    public func withUpdatedAttributes(_ attributes: [MessageAttribute]) -> Message {'))+'\n}\n'
    text+='\nfinal class ConsumableContentMessageAttribute:MessageAttribute {let consumed:Bool;init(consumed:Bool){self.consumed=consumed}}\n'
    text+='\n'+clean(block((source/POLICY).read_text(),'public func nagramiXCanMarkTemporaryMediaOpened('))+'\n'
    text+='\nextension Archive {\n'+'\n'.join(clean(block((source/ARCHIVE).read_text(),m)) for m in [
        '    public func canExplicitlyOpenTemporaryMedia(', '    public func hasExplicitTemporaryMediaOpen(',
        '    public func authorizeTemporaryMediaOpen('])+'\n}\n'
    return text+ARCHIVE_TESTS


def consumption(source):
    paths=[POLICY,MARK,SECRET,receipts.APPLY,receipts.SYNC,MANAGED,
           receipts.CORE+'State/AccountViewTracker.swift',receipts.CORE+'State/ManagedSynchronizeMarkAllUnseenPersonalMessagesOperations.swift']
    text=receipts.fixture({p:(source/p).read_text() for p in paths},source)
    assert text.endswith(receipts.TESTS)
    text=text[:-len(receipts.TESTS)]
    text=text.replace('final class NagramiXArchivedMessageAttribute:MessageAttribute {let isTemporary:',
                      'final class NagramiXArchivedMessageAttribute:MessageAttribute {let deletedAt:Int32=0;let isViewOnce=false;let isTemporary:')
    text=text.replace('final class NagramiXMessageArchive {var ids=',
                      'final class NagramiXMessageArchive {var explicit=Set<MessageId>();func hasExplicitTemporaryMediaOpen(id:MessageId)->Bool{explicit.contains(id)};var ids=')
    text=text.replace('nagramiXTemporaryMessagesEnabled() && ids.contains(id)',
                      'nagramiXTemporaryMessagesEnabled() && ids.contains(id) && !explicit.contains(id)')
    text=text.replace('nagramiXTemporaryMessagesEnabled() && globalIds.contains("\\(peerId.id):\\(globallyUniqueId)")',
                      'nagramiXTemporaryMessagesEnabled() && globalIds.contains("\\(peerId.id):\\(globallyUniqueId)") && !explicit.contains(where:{$0.peerId==peerId && $0.id==Int32(globallyUniqueId)})')
    text+='\nextension Message {\n'+clean(block((source/ARCHIVE).read_text(),'    var nagramiXShowsArchiveNotice: Bool {'))+'\n}\n'
    text+='\n'+clean(block((source/SECRET).read_text(),'private func nagramiXSecretPrivacyNoop('))+'\n'
    text+='\n'+clean(block((source/MARK).read_text(),'func _internal_markTemporaryMediaOpened('))+'\n'
    helpers=receipts.TESTS[:receipts.TESTS.index('let payloads:')]
    return text+helpers+CONSUMPTION_TESTS


ARCHIVE_TESTS=r'''
@main struct ArchiveConsentTests {
 static func main() throws {
  var count=0
  func check(_ value:@autoclosure()->Bool,_ why:String){count+=1;if !value(){print("FAIL "+why);exit(91)}}
  let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
  try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true)
  defer{try? FileManager.default.removeItem(at:root);UserDefaults.standard.removeVolatileDomain(forName:UserDefaults.argumentDomain)}
  var ordinal:Int32=20
  for secret in [false,true]{for kind in ["voice","round","video","photo"]{for deleted in [false,true]{
   ordinal+=1;configure(true,deleted)
   let archive=Archive(root.appendingPathComponent("\(ordinal).json").path)
   let media:[Media]=kind=="photo" ? [TelegramMediaImage(kind)]:[TelegramMediaFile(kind)]
   let (store,peers)=sample(ordinal,secret:secret,incoming:true,ttl:viewOnceTimeout,media:media,global:Int64(ordinal))
   let live=locallyRenderedMessage(message:store,peers:peers)!
   check(nagramiXCanMarkTemporaryMediaOpened(live),"all four live incoming kinds eligible")
   archive.captureIncoming(store,peers:peers);archive.queue.drain()
   check(!archive.hasExplicitTemporaryMediaOpen(id:live.id),"capture is never consent")
   check(archive.shouldSuppressTemporaryContentReceipt(id:live.id),"playback is private before consent")
   check(archive.canExplicitlyOpenTemporaryMedia(id:live.id),"durable local bytes ready")
   var accepted=false
   _=archive.authorizeTemporaryMediaOpen(id:live.id).startStandalone(next:{accepted=$0});archive.queue.drain()
   check(accepted && archive.hasExplicitTemporaryMediaOpen(id:live.id),"selected durable consent committed")
   check(!archive.shouldSuppressTemporaryContentReceipt(id:live.id),"queued receipt accepts selected consent")
   let encoded=try JSONEncoder().encode(archive.saved)
   let restored=try JSONDecoder().decode(NagramiXMessageArchiveState.self,from:encoded)
   check(restored.records.values.first?.explicitlyOpened==true,"consent survives Codable restart")
   let json=try JSONSerialization.jsonObject(with:encoded) as! [String:Any]
   var old=json;var records=old["records"] as! [String:[String:Any]]
   for k in records.keys{records[k]?.removeValue(forKey:"explicitlyOpened")};old["records"]=records
   let oldState=try JSONDecoder().decode(NagramiXMessageArchiveState.self,from:JSONSerialization.data(withJSONObject:old))
   check(oldState.records.values.first?.explicitlyOpened==nil,"legacy archive is never consent")
   archive.markTemporaryExpired(id:live.id,expiredAt:2000);archive.queue.drain()
   let retained=archive.snapshotForExpiredMessage(id:live.id)
   check(retained != nil,"temporary snapshot remains with Deleted OFF or ON")
   check(retained!.nagramiXShowsArchiveNotice==deleted,"deleted styling belongs only to Deleted switch")
   check(archive.containsArchivedMessage(id:live.id),"temporary snapshot owns visible history")
   check(archive.deletedMessages(peerId:live.id.peerId,threadId:nil,minIndex:nil,maxIndex:nil).count==1,"history injects retained temporary row")
   check(!nagramiXCanMarkTemporaryMediaOpened(retained!),"archive-only copy cannot notify sender")
   check(!archive.canExplicitlyOpenTemporaryMedia(id:live.id),"expired record cannot receive new consent")
   configure(false,deleted)
   check((archive.snapshotForExpiredMessage(id:live.id) != nil) == deleted,"OFF restores deleted visibility independently")
  }}}
  configure(true,false)
  let archive=Archive(root.appendingPathComponent("incomplete.json").path)
  let incomplete=TelegramMediaFile("voice");incomplete.resource="remote"
  let(store,peers)=sample(500,ttl:viewOnceTimeout,media:[incomplete]);let live=locallyRenderedMessage(message:store,peers:peers)!
  archive.captureIncoming(store,peers:peers);archive.queue.drain()
  check(!archive.canExplicitlyOpenTemporaryMedia(id:live.id),"incomplete retained file denies consent")
  var accepted=true;_=archive.authorizeTemporaryMediaOpen(id:live.id).startStandalone(next:{accepted=$0});archive.queue.drain()
  check(!accepted && !archive.hasExplicitTemporaryMediaOpen(id:live.id),"incomplete file cannot persist consent")
  archive.clearAll();archive.queue.drain()
  check(!archive.canExplicitlyOpenTemporaryMedia(id:live.id),"clear cannot resurrect consent or content")
  let cancelled=Archive(root.appendingPathComponent("cancelled.json").path)
  let(cancelStore,cancelPeers)=sample(502,ttl:viewOnceTimeout,media:[TelegramMediaFile("voice")])
  let cancelId=locallyRenderedMessage(message:cancelStore,peers:cancelPeers)!.id
  cancelled.captureIncoming(cancelStore,peers:cancelPeers);cancelled.queue.drain()
  let disposable=cancelled.authorizeTemporaryMediaOpen(id:cancelId).startStandalone()
  disposable.dispose();cancelled.queue.drain()
  check(!cancelled.hasExplicitTemporaryMediaOpen(id:cancelId),"cancelled queued consent never commits")
  let failed=Archive(root.appendingPathComponent("failed.json").path)
  let(good,goodPeers)=sample(501,ttl:viewOnceTimeout,media:[TelegramMediaFile("voice")])
  let goodId=locallyRenderedMessage(message:good,peers:goodPeers)!.id
  failed.captureIncoming(good,peers:goodPeers);failed.queue.drain()
  try FileManager.default.removeItem(atPath:failed.path)
  try FileManager.default.createDirectory(atPath:failed.path,withIntermediateDirectories:false)
  accepted=true;_=failed.authorizeTemporaryMediaOpen(id:goodId).startStandalone(next:{accepted=$0});failed.queue.drain()
  check(!accepted && !failed.hasExplicitTemporaryMediaOpen(id:goodId),"failed JSON write cannot authorize receipt")
  print("PASS archive consent and retained visibility: \(count)")
 }
}
'''

CONSUMPTION_TESTS=r'''
@main struct ContentReceiptTests {static func main(){
 for peer in [cloud,group,channel,secret]{for kind in ["voice","round","video","photo"]{for once in [false,true]{for ghost in [false,true]{
  enabled();NagramiXGhostSettings.current.hidesMessageReads=ghost
  let payload:[Media]=kind=="photo" ? [TelegramMediaImage()]:[TelegramMediaFile(voice:kind=="voice",round:kind=="round",video:kind=="video")]
  let value=message(44,peer:peer,namespace:peer==secret ? 2:0,ttl:once ? viewOnceTimeout:30,media:payload)
  value.globallyUniqueId=44
  let neighbour=message(45,peer:peer,namespace:value.id.namespace,media:payload)
  neighbour.globallyUniqueId=45
  let(t,p)=prepare([value,neighbour]);p.archive.ids=[value.id,neighbour.id]
  p.archive.globalIds=["\(peer.id):44","\(peer.id):45"]
  execute(_internal_markMessageContentAsConsumedInteractively(postbox:p,messageId:value.id))
  check(t.cloudEnqueued.isEmpty && t.secretEnqueued.isEmpty && !consumed(value) && countdown(value)==nil,"automatic playback sends no content receipt or timer")
  execute(_internal_markTemporaryMediaOpened(postbox:p,messageId:value.id))
  check(t.cloudEnqueued.isEmpty && t.secretEnqueued.isEmpty,"producer requires durable consent")
  p.archive.explicit.insert(value.id)
  execute(_internal_markTemporaryMediaOpened(postbox:p,messageId:value.id))
  check(consumed(value) && countdown(value)==nil,"explicit open keeps original local TTL inactive")
  check(t.cloudEnqueued==(peer==secret ? []:[value.id]) && t.secretEnqueued==(peer==secret ? [44]:[]),"exactly one selected native receipt enqueued")
  execute(_internal_markTemporaryMediaOpened(postbox:p,messageId:value.id))
  check(t.cloudEnqueued.count+t.secretEnqueued.count==1,"double action idempotent after transaction")
  let operation=SynchronizeConsumeMessageContentsOperation(messageIds:[value.id,neighbour.id])
  check(fixtureQueuedContentIds(transaction:t,postbox:p,operation:operation)==[value.id],"mixed queued IDs only explicit open bypasses privacy and Ghost")
  let action=SecretMessageAction.readMessageContents(layer:.layer144,actionGloballyUniqueId:2,globallyUniqueIds:[44,45])
  if peer==secret {let filtered=nagramiXTemporarySafeSecretServiceAction(action,transaction:t,postbox:p,peerId:peer)
   if case let .readMessageContents(_,_,ids)=filtered{check(ids==[44],"secret final worker excludes unselected media")}else{check(false,"explicit secret operation retained")}}
  t.messages.removeValue(forKey:value.id)
  check(fixtureQueuedContentIds(transaction:t,postbox:p,operation:operation)==[value.id],"consent survives missing native row")
  check(nagramiXShouldSuppressTemporaryReceipt(transaction:t,postbox:p,messageId:value.id),"automatic producer remains suppressed even after consent")
 }}}}
 for kind in ["outgoing","ordinary","expired","archive","text","paid","failed","consumed"]{
  enabled();let attrs:[MessageAttribute]=kind=="archive" ? [NagramiXArchivedMessageAttribute(true)]:kind=="consumed" ? [ConsumableContentMessageAttribute(consumed:true)]:[]
  let media:[Media]=kind=="text" ? []:kind=="paid" ? [TelegramMediaPaidContent()]:kind=="expired" ? [TelegramMediaExpiredContent()]:[TelegramMediaImage()]
  let m=message(incoming:kind != "outgoing",ttl:kind=="ordinary" ? nil:viewOnceTimeout,media:media,extra:attrs)
  if kind=="failed"{m.flags.insert(.Failed)}
  check(!nagramiXCanMarkTemporaryMediaOpened(m),"unsupported or stale action rejected: "+kind)
  let(t,p)=prepare([m]);p.archive.explicit.insert(m.id);execute(_internal_markTemporaryMediaOpened(postbox:p,messageId:m.id))
  check(t.cloudEnqueued.isEmpty && t.secretEnqueued.isEmpty,"invalid message sends no receipt")
 }
 enabled(false);let m=message(media:[TelegramMediaImage()]);let(t,p)=prepare([m]);p.archive.explicit.insert(m.id)
 execute(_internal_markTemporaryMediaOpened(postbox:p,messageId:m.id));check(t.cloudEnqueued.isEmpty,"stale menu OFF rejected")
 for layer in [SecretChatLayer.layer8,.layer46,.layer73,.layer101,.layer144] {
  let(t,p)=prepare([])
  let action=SecretMessageAction.screenshotMessages(layer:layer,actionGloballyUniqueId:321,globallyUniqueIds:[44],messageId:MessageId(peerId:secret,namespace:2,id:44))
  NagramiXPrivacySettings.current.bypassScreenshots=true
  let hidden=nagramiXTemporarySafeSecretServiceAction(action,transaction:t,postbox:p,peerId:secret)
  if case let .screenshotMessages(_,_,ids,_)=hidden {check(ids.isEmpty,"capture bypass replaces queued screenshot")}else{check(true,"capture bypass uses native noop")}
  check(hidden.globallyUniqueId==321,"native secret action identity retained")
  NagramiXPrivacySettings.current.bypassScreenshots=false
  let native=nagramiXTemporarySafeSecretServiceAction(action,transaction:t,postbox:p,peerId:secret)
  if case let .screenshotMessages(_,_,ids,_)=native{check(ids==[44],"Free Content OFF preserves screenshot notification")}else{check(false,"native screenshot action retained")}
 }
 print("PASS explicit and automatic content receipt production checks: \(assertions)")
}}
'''


def orchestration(source):
    text=consumption(source)
    text=text[:text.index('@main struct ContentReceiptTests')]
    text=text.replace('final class NagramiXMessageArchive {var explicit=',
        'final class NagramiXMessageArchive {var ready=true;var save=true;var afterAuthorize:(()->Void)?;var explicit=')
    text+='''
final class Queue {static func concurrentDefaultQueue()->Queue{Queue()}}
final class MediaBox {}
extension Postbox {var mediaBox:MediaBox{MediaBox()}}
var fetched=true
func nagramiXFetchContentCopyMedia(mediaBox:MediaBox,messages:[Message])->Signal<Bool,NoError>{.single(fetched)}
func take<A,E>(_ count:Int)->(Signal<A,E>)->Signal<A,E>{{ $0 }}
func filter<A,E>(_ f:@escaping(A)->Bool)->(Signal<A,E>)->Signal<A,E>{{ s in Signal{switch s.run(){case let .value(v):return f(v) ? .value(v):.complete;case let .failure(e):return .failure(e);case .complete:return .complete}}}}
// The adapter advances the pending/no-value deadline immediately. This tests
// branch propagation, not SignalKit scheduling or real network timeouts.
func timeout<A,E>(_ seconds:Double,queue:Queue,alternate:Signal<A,E>)->(Signal<A,E>)->Signal<A,E>{{s in Signal{switch s.run(){case .complete:return alternate.run();case let v:return v}}}}
extension NagramiXMessageArchive {
 var updates:Signal<Int,NoError>{.single(0)}
 func canExplicitlyOpenTemporaryMedia(id:MessageId)->Bool{ready && nagramiXTemporaryMessagesEnabled()}
 func authorizeTemporaryMediaOpen(id:MessageId)->Signal<Bool,NoError>{Signal{if self.save{self.explicit.insert(id)};self.afterAuthorize?();return .value(self.save)}}
}
final class EngineFacade {let account:Account;init(_ p:Postbox){account=Account(p)}
'''
    text+=block((source/ENGINE).read_text(),'        public func markTemporaryMediaOpened(').replace('public ','')+'\n}\n'
    text+=r'''
@main struct EngineOpenTests {static func main(){
 for scenario in ["ready","fetch-fails","retain-incomplete","save-fails","removed-before-commit","OFF"]{
  enabled();fetched=scenario != "fetch-fails"
  let m=message(media:[TelegramMediaImage()]);let(t,p)=prepare([m]);let e=EngineFacade(p)
  p.archive.ready=scenario != "retain-incomplete";p.archive.save=scenario != "save-fails"
  if scenario=="removed-before-commit"{p.archive.afterAuthorize={t.messages.removeValue(forKey:m.id)}}
  if scenario=="OFF"{enabled(false)}
  let result=e.markTemporaryMediaOpened(messageId:m.id).run()
  if case let .value(accepted)=result{check(accepted==(scenario=="ready"),"engine preparation result: "+scenario)}else{check(false,"engine always returns a terminal Bool")}
  check(t.cloudEnqueued==(scenario=="ready" ? [m.id]:[]),"no receipt after failed preparation or stale message: "+scenario)
 }
 print("PASS production engine preparation branches: \(assertions)")
}}
'''
    return text
