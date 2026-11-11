"""Execute real archive/consumption bodies with explicit media and Postbox IO adapters."""
from validate_quick_format import block
from validate_temporary_interaction_archive import clean, ARCHIVE, POLICY
import content_interaction_consent_runtime as consent

CORE = 'submodules/TelegramCore/Sources/'
CONSUME = CORE + 'TelegramEngine/Messages/MarkMessageContentAsConsumedInteractively.swift'
TIMER = CORE + 'State/ManagedAutoremoveMessageOperations.swift'
HISTORY = 'submodules/TelegramUI/Sources/ChatHistoryEntriesForView.swift'


def archive(source):
    text = consent.archive(source)
    text = text[:text.index('@main struct ArchiveConsentTests')]
    return text + ARCHIVE_TESTS


def consumption(source):
    text = consent.consumption(source)
    text = text[:text.index('@main')]
    # Real native TTL recognition is outside this fixture's Postbox adapter.
    text = text.replace('var containsSecretMedia:Bool{false}', 'var containsSecretMedia:Bool{ attributes.contains{$0 is AutoremoveTimeoutMessageAttribute || $0 is AutoclearTimeoutMessageAttribute} && !media.isEmpty }')
    text = text.replace('final class TelegramMediaExpiredContent:Media{}', 'final class TelegramMediaExpiredContent:Media{enum Kind{case image,file,voiceMessage,videoMessage};init(data:Kind){}}')
    text = text.replace('var captures=0;static func forPostbox', 'var captures=0;var expirations=0;func archiveTemporaryExpiration(message:Message,expiredAt:Int32){expirations += 1};static func forPostbox')
    actual = (source / CONSUME).read_text()
    text += '\nimport CoreFoundation\n'
    text += '\n' + clean(block((source / (CORE + 'SyncCore/SyncCore_AutoremoveTimeoutMessageAttribute.swift')).read_text(), 'public func autoremoveExpiryTimestamp(')) + '\n'
    for name in ['func nagramiXTemporaryAttributesWithoutCountdown(', 'func nagramiXPreserveTemporaryMediaBeforeExpiration(', 'func markMessageContentAsConsumedRemotely(']:
        text += '\n' + clean(block(actual, name)) + '\n'
    timer = block((source / TIMER).read_text(), 'if nagramiXPreserveTemporaryMediaBeforeExpiration(transaction: transaction, postbox: postbox, message: message) {')
    text += '\nvar nativeExpirations = 0\nfunc performTimer(transaction:Transaction,postbox:Postbox,message:Message){\n' + timer + '\n nativeExpirations += 1\n}\n'
    return text + CONSUMPTION_TESTS


def history(source):
    ui = block((source / HISTORY).read_text(), 'private func nagramiXRetainedTemporaryMessageIsRead(')
    native = (source / 'submodules/Postbox/Sources/PeerReadState.swift').read_text()
    state = block(native, '    func isOutgoingMessageIndexRead(')
    combined = block(native, '    public func isOutgoingMessageIndexRead(')
    return READ_BOUNDARY + '\n' + clean(state) + '\n}\nstruct CombinedPeerReadState {\n let states:[(Int32,PeerReadState)]\n' + clean(combined) + '\n}\n' + clean(ui) + READ_TESTS


ARCHIVE_TESTS = r'''
@main struct TemporaryExpiryArchiveTests {
 static func main() throws {
  var count = 0
  func check(_ value: @autoclosure () -> Bool, _ diagnostic: String) {
   count += 1
   if !value() { FileHandle.standardError.write(Data(diagnostic.utf8)); exit(96) }
  }
  let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
  try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
  defer { try? FileManager.default.removeItem(at: root); UserDefaults.standard.removeVolatileDomain(forName: UserDefaults.argumentDomain) }
  var ordinal: Int32 = 200
  for incoming in [false,true] { for secret in [false,true] { for kind in ["voice","round","photo","video"] { for showDeleted in [false,true] {
   ordinal += 1; configure(true,showDeleted)
   let path = root.appendingPathComponent("\(ordinal).json").path
   let archive = Archive(path)
   let media: [Media] = kind == "photo" ? [TelegramMediaImage(kind)] : [TelegramMediaFile(kind)]
   let (store, peers) = sample(ordinal, secret:secret, incoming:incoming, ttl:viewOnceTimeout, media:media)
   let original = locallyRenderedMessage(message:store, peers:peers)!
   archive.captureIncoming(store, peers:peers); archive.queue.drain()
   archive.markTemporaryExpired(id:original.id, expiredAt:777); archive.queue.drain()
   let saved = archive.saved.records.values.first!
   check(saved.deletedAt == nil && saved.mediaExpiredAt == 777, "expiry is not a deletion")
   let rendered = archive.snapshotForExpiredMessage(id:original.id)!
   archive.queue.drain()
   check(!rendered.nagramiXShowsArchiveNotice, "expiry has no deletion label or opacity predicate")
   check(rendered.id == original.id && rendered.stableId == original.stableId, "expiry preserves row identity")
   check(rendered.media.count == 1, "expiry keeps retained attachment")
   check(archive.deletedMessage(id:original.id) == nil && !archive.isLocallyDeletedMessage(id:original.id), "expired media does not enter deleted-message phase")
   let replay = archive.temporaryInteractionMessage(id:original.id, liveMessage:nil)
   check(replay != nil && !replay!.nagramiXShowsArchiveNotice, "expired media remains interactive without deletion appearance")
   let entries = archive.deletedMessages(peerId:original.id.peerId, threadId:nil, minIndex:nil, maxIndex:nil)
   check(entries.count == 1 && !entries[0].nagramiXShowsArchiveNotice, "missing expired native row remains visible as ordinary retained media")
   check(!archive.canExplicitlyOpenTemporaryMedia(id:original.id), "expired original cannot authorize a new content receipt")
   archive.captureIncoming(store, peers:peers); archive.queue.drain()
   check(archive.saved.records.values.first?.mediaExpiredAt == 777, "history refresh preserves expiry provenance")
   let restored = Archive(path); restored.restore()
   check(restored.saved.records.values.first?.mediaExpiredAt == 777 && restored.saved.records.values.first?.deletedAt == nil, "separate expiry survives real JSON persistence")
   check(restored.render(original.id)?.nagramiXShowsArchiveNotice == false, "restart keeps ordinary appearance")
   let published = archive.revisions
   archive.markTemporaryExpired(id:original.id, expiredAt:888); archive.queue.drain()
   check(archive.revisions == published, "repeated expiry does not publish an endless history loop")
   if ordinal.isMultiple(of:2) { archive.archiveMessagesBeforeDeletion([original], deletedAt:999) }
   else { archive.archiveServerDeletion(messageIds:[original.id], deletedAt:999) }
   archive.queue.drain()
   check(archive.isLocallyDeletedMessage(id:original.id), "real deletion remains a real deletion")
   check(archive.render(original.id)?.nagramiXShowsArchiveNotice == showDeleted, "real deletion keeps configured notice and opacity")
   archive.markTemporaryExpired(id:original.id, expiredAt:1000); archive.queue.drain()
   check(archive.saved.records.values.first?.deletedAt == 999, "late expiry never clears genuine deletion")
  }}}}
  configure(false,true)
  let off = Archive(root.appendingPathComponent("off.json").path)
  let (store, peers) = sample(900, incoming:false, ttl:viewOnceTimeout, media:[TelegramMediaFile("voice")])
  let id = locallyRenderedMessage(message:store,peers:peers)!.id
  off.captureIncoming(store,peers:peers); off.queue.drain()
  off.markTemporaryExpired(id:id,expiredAt:700); off.queue.drain()
  check(off.snapshotForExpiredMessage(id:id) == nil, "OFF preserves native expired placeholder")
  off.archiveServerDeletion(messageIds:[id],deletedAt:800); off.queue.drain()
  check(off.deletedMessage(id:id)?.nagramiXShowsArchiveNotice == true, "OFF keeps real deleted-message feature")
  configure(true,true)
  let clear = Archive(root.appendingPathComponent("clear.json").path)
  clear.captureIncoming(store,peers:peers); clear.queue.drain()
  clear.markTemporaryExpired(id:id,expiredAt:700); clear.queue.drain()
  clear.clearAll(); clear.queue.drain()
  clear.captureIncoming(store,peers:peers); clear.queue.drain()
  check(clear.saved.records.isEmpty, "full clear tombstones expired retained rows")
  let removal = Archive(root.appendingPathComponent("removal.json").path)
  removal.captureIncoming(store,peers:peers); removal.queue.drain()
  removal.markTemporaryExpired(id:id,expiredAt:700); removal.queue.drain()
  let retained = removal.render(id)!
  let candidates = removal.localPostDeletionCandidates(messages:[retained])
  let plan = removal.postDeletionPlan(transaction:Transaction(),messageIds:[id],localCandidates:candidates)
  check(plan.localMessageIds == [id] && plan.nativeMessageIds.isEmpty, "expiry-only copy removal never sends a missing original to server")
  _ = removal.deleteArchivedPosts(messageIds:plan.localMessageIds).startStandalone(); removal.queue.drain()
  check(removal.saved.records.isEmpty, "expiry-only copy can be explicitly removed")
  removal.captureIncoming(store,peers:peers); removal.queue.drain()
  check(removal.saved.records.isEmpty, "explicitly removed expiry copy cannot revive")
  let legacyPath = root.appendingPathComponent("legacy.json")
  let legacy = Archive(legacyPath.path)
  legacy.captureIncoming(store,peers:peers); legacy.queue.drain()
  legacy.archiveServerDeletion(messageIds:[id],deletedAt:600); legacy.queue.drain()
  var object = try JSONSerialization.jsonObject(with:Data(contentsOf:legacyPath)) as! [String:Any]
  var records = object["records"] as! [String:[String:Any]]
  for key in records.keys { records[key]!.removeValue(forKey:"mediaExpiredAt") }
  object["records"] = records
  try JSONSerialization.data(withJSONObject:object).write(to:legacyPath)
  let previous = Archive(legacyPath.path); previous.restore()
  check(previous.saved.records.values.first?.mediaExpiredAt == nil, "old JSON decodes without a migration")
  check(previous.render(id)?.nagramiXShowsArchiveNotice == true, "unknown legacy deletion is never silently erased")
  print("temporary-expiry archive checks: \(count)")
 }
}
'''


CONSUMPTION_TESTS = r'''
@main struct TemporaryExpiryConsumptionTests {
 static func main() {
  var count = 0
  func verify(_ value: Bool, _ diagnostic: String) {
   count += 1
   if !value { FileHandle.standardError.write(Data(diagnostic.utf8)); exit(96) }
  }
  defer { enabled(false) }
  for incoming in [false,true] { for ttl: Int32 in [1,30,viewOnceTimeout] { for kind in 0..<4 { for autoclear in [false,true] { for pair in [(false,false),(true,false),(false,true)] {
   enabled(pair.0,pair.1)
   let media: [Media] = kind == 0 ? [TelegramMediaImage()] : [TelegramMediaFile(voice:kind == 1,round:kind == 2,video:kind == 3)]
   let m = message(incoming:incoming, ttl:nil, media:media)
   let countdown: Int32? = kind.isMultiple(of:2) ? 100 : nil
   m.attributes = [ConsumableContentMessageAttribute(consumed:false)]
   if autoclear { m.attributes.append(AutoclearTimeoutMessageAttribute(timeout:ttl,countdownBeginTime:countdown)) }
   else { m.attributes.append(AutoremoveTimeoutMessageAttribute(timeout:ttl,countdownBeginTime:countdown)) }
   let (transaction, postbox) = prepare([m])
   markMessageContentAsConsumedRemotely(transaction:transaction,messageId:m.id,consumeDate:100,messageArchive:postbox.archive)
   let preserving = pair.0 || pair.1
   verify((m.attributes.first as? ConsumableContentMessageAttribute)?.consumed == true, "remote consumption truth is preserved")
   verify(transaction.cloudEnqueued.isEmpty && transaction.secretEnqueued.isEmpty, "received confirmation never emits a new receipt")
   if preserving {
    verify(!(m.media[0] is TelegramMediaExpiredContent), "retained remote playback never expires media")
    verify(m.media[0] === media[0], "same native media and player source are preserved")
    verify(m.attributes.allSatisfy { ($0 as? AutoremoveTimeoutMessageAttribute)?.countdownBeginTime == nil && ($0 as? AutoclearTimeoutMessageAttribute)?.countdownBeginTime == nil }, "retention removes active and pending countdowns")
    verify(postbox.archive.expirations == 0 && postbox.archive.captures == 1, "remote playback captures without archiving a deletion")
   } else if countdown == nil {
    verify(m.media[0] is TelegramMediaExpiredContent, "OFF keeps native media consumption")
   }
  }}}}}
  for incoming in [false,true] { for secret in [false,true] { for autoclear in [false,true] {
   enabled()
   let m = message(peer:secret ? PeerId(namespace:3,id:8) : PeerId(namespace:0,id:8),namespace:secret ? (incoming ? 2:1):0,incoming:incoming,ttl:nil,media:[TelegramMediaFile(round:true)])
   m.attributes = [ConsumableContentMessageAttribute(consumed:true)]
   if autoclear { m.attributes.append(AutoclearTimeoutMessageAttribute(timeout:30,countdownBeginTime:100)) }
   else { m.attributes.append(AutoremoveTimeoutMessageAttribute(timeout:30,countdownBeginTime:100)) }
   let (transaction, postbox) = prepare([m]); let calls = nativeExpirations
   performTimer(transaction:transaction,postbox:postbox,message:m)
   verify(nativeExpirations == calls && !(m.media[0] is TelegramMediaExpiredContent), "queued timer cannot erase approved media")
   verify(!nagramiXTemporaryAttributesWithoutCountdown(m.attributes).changed, "queued timer removes its scheduling attribute")
   verify((m.attributes.first as? ConsumableContentMessageAttribute)?.consumed == true, "queued timer preserves confirmed consumption")
   enabled(false)
   performTimer(transaction:transaction,postbox:postbox,message:m)
   verify(nativeExpirations == calls+1, "OFF retains native timer path")
  }}}
  enabled()
  let ordinary = message(ttl:nil,media:[TelegramMediaFile(voice:true)])
  let (transaction,postbox) = prepare([ordinary]);let calls=nativeExpirations
  performTimer(transaction:transaction,postbox:postbox,message:ordinary)
  verify(nativeExpirations == calls+1, "ordinary messages remain native")
  let attrs: [MessageAttribute] = [ConsumableContentMessageAttribute(consumed:true),AutoclearTimeoutMessageAttribute(timeout:90,countdownBeginTime:100),AutoremoveTimeoutMessageAttribute(timeout:120,countdownBeginTime:0)]
  let retained=nagramiXTemporaryAttributesWithoutCountdown(attrs)
  verify(retained.changed && (retained.attributes[1] as? AutoclearTimeoutMessageAttribute)?.timeout == 90 && (retained.attributes[2] as? AutoremoveTimeoutMessageAttribute)?.timeout == 120, "countdown reset preserves exact TTL provenance")
  verify((retained.attributes[0] as? ConsumableContentMessageAttribute) === (attrs[0] as? ConsumableContentMessageAttribute), "unrelated attributes retain identity")
  print("temporary-expiry consumption checks: \(count)")
 }
}
'''


READ_BOUNDARY = r'''
import Foundation
struct PeerId:Hashable { let value:Int64 }
struct MessageId:Equatable { let peerId:PeerId;let namespace:Int32;let id:Int32 }
struct MessageIndex:Comparable {
 let id:MessageId;let timestamp:Int32
 static func <(lhs:Self,rhs:Self)->Bool { lhs.timestamp != rhs.timestamp ? lhs.timestamp < rhs.timestamp : lhs.id.id < rhs.id.id }
}
struct MessageFlags:OptionSet { let rawValue:Int;static let Incoming=Self(rawValue:1) }
struct Message { let id:MessageId;let flags:MessageFlags;let timestamp:Int32;var index:MessageIndex { MessageIndex(id:id,timestamp:timestamp) } }
enum MessageHistoryViewReadState { case peer([PeerId:CombinedPeerReadState]) }
enum PeerReadState {
 case idBased(maxIncomingReadId:Int32,maxOutgoingReadId:Int32,maxKnownId:Int32,count:Int32,markedUnread:Bool)
 case indexBased(maxIncomingReadIndex:MessageIndex,maxOutgoingReadIndex:MessageIndex,count:Int32,markedUnread:Bool)
'''

READ_TESTS = r'''
@main struct RetainedReadTests {
 static func main() {
  var checks=0
  func check(_ value:Bool,_ why:String){checks+=1;if !value{FileHandle.standardError.write(Data(why.utf8));exit(96)}}
  let peer=PeerId(value:8),other=PeerId(value:9)
  for namespace:Int32 in [0,1,2] { for incoming in [false,true] { for value:Int32 in [5,10,15] {
   let id=MessageId(peerId:peer,namespace:namespace,id:value)
   let message=Message(id:id,flags:incoming ? [.Incoming]:[],timestamp:value)
   let limit=MessageIndex(id:MessageId(peerId:peer,namespace:namespace,id:10),timestamp:10)
   let states:[PeerReadState]=[.idBased(maxIncomingReadId:50,maxOutgoingReadId:10,maxKnownId:100,count:0,markedUnread:false),.indexBased(maxIncomingReadIndex:limit,maxOutgoingReadIndex:limit,count:0,markedUnread:false)]
   for state in states {
    let read=MessageHistoryViewReadState.peer([peer:CombinedPeerReadState(states:[(namespace,state)])])
    check(nagramiXRetainedTemporaryMessageIsRead(message,readStates:read) == (!incoming && value<=10),"retained read status follows real native read state")
    check(!nagramiXRetainedTemporaryMessageIsRead(message,readStates:.peer([other:CombinedPeerReadState(states:[(namespace,state)])])),"another peer cannot confirm reading")
    check(!nagramiXRetainedTemporaryMessageIsRead(message,readStates:.peer([peer:CombinedPeerReadState(states:[(namespace+20,state)])])),"another namespace cannot confirm reading")
   }
   check(!nagramiXRetainedTemporaryMessageIsRead(message,readStates:nil),"unknown read state does not fabricate two checks")
  }}}
  print("temporary-expiry native read checks: \(checks)")
 }
}
'''


def negatives(archive_text, receipt_text, read_text):
    cases = [
        ('expiry-is-delete', archive_text, 'record.mediaExpiredAt = expiredAt', 'record.deletedAt = expiredAt', 'expiry is not a deletion'),
        ('lost-expiry-row', archive_text, '(record.deletedAt != nil || (settings.saveTemporaryMessages && record.wasTemporary && record.mediaExpiredAt != nil))', 'record.deletedAt != nil', 'missing expired native row remains visible as ordinary retained media'),
        ('clear-revival', archive_text, '($0.value.deletedAt != nil || $0.value.mediaExpiredAt != nil)', '$0.value.deletedAt != nil', 'full clear tombstones expired retained rows'),
        ('expiry-removal-ownership', archive_text, 'var hasLocalRemovalOwnership: Bool { self.deletedAt != nil || self.mediaExpiredAt != nil }', 'var hasLocalRemovalOwnership: Bool { self.deletedAt != nil }', 'expiry-only copy removal never sends a missing original to server'),
        ('remote-countdown', receipt_text, 'if nagramiXPreserveTemporaryMedia { continue }', 'if false { continue }', 'retained remote playback never expires media'),
        ('queued-timer', receipt_text, 'if nagramiXPreserveTemporaryMediaBeforeExpiration(transaction: transaction, postbox: postbox, message: message) {', 'if false {', 'queued timer cannot erase approved media'),
        ('fake-unread', receipt_text, 'ConsumableContentMessageAttribute(consumed: true)', 'ConsumableContentMessageAttribute(consumed: false)', 'remote consumption truth is preserved'),
        ('fake-read', read_text, 'return state.isOutgoingMessageIndexRead(message.index)', 'return state.isOutgoingMessageIndexRead(message.index) || true', 'another namespace cannot confirm reading'),
    ]
    for name,text,before,after,diagnostic in cases:
        assert before in text,name
        yield name,text.replace(before,after),diagnostic
