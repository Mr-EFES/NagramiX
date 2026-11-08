#!/usr/bin/env python3
"""Проверить сохранение временных сообщений и readonly-взаимодействия."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from validate_quick_format import block
from validate_copy_delivery import model_boundary

ROOT = Path(__file__).resolve().parents[1]
CORE = 'submodules/TelegramCore/Sources/'
ARCHIVE = CORE + 'Utils/NagramiXMessageArchive.swift'
POLICY = CORE + 'Utils/NagramiXCaptureProtectionPolicy.swift'
HISTORY = 'submodules/TelegramUI/Sources/ChatHistoryEntriesForView.swift'
SECRET = CORE + 'State/ProcessSecretChatIncomingDecryptedOperations.swift'
REPLAY = CORE + 'State/Sync/StateReplay+Messages.swift'
WRITER = CORE + 'Utils/NagramiXArchivePersistence.swift'
OLD = ROOT / 'ios/extended_poll_integrity/After3.inc'


def clean(text):
    return '\n'.join(line for line in text.splitlines() if not line.startswith('import ') and not line.startswith('internal import ')).replace('public ', '')


def body(text, marker):
    result = block(text, marker)
    if text[:text.index(marker)].endswith('    @discardableResult\n'):
        result = '    @discardableResult\n' + result
    return result


def verify(source):
    text = (source / ARCHIVE).read_text()
    readonly = body(text, '    public func temporaryInteractionMessage(')
    for forbidden in ['captureTemporary', 'markTemporaryExpired', 'persist(', 'snapshotForExpired', 'archiveTemporaryExpiration', '.queue.', '.engine.', '.network.']:
        assert forbidden not in readonly, forbidden
    assert 'requireCompleteMedia: false' in readonly
    assert 'guard nagramiXTemporaryMessagesEnabled() else { return liveMessage }' in readonly
    assert 'var globallyUniqueId: Int64? = nil' in text
    assert 'var contentAttributes: [Data]? = nil' in text
    render = body(text, '    private func renderDeletedRecord(')
    assert '!media.isEmpty' not in render
    assert 'decodedMedia.count == record.content.media.count' in render
    assert 'decodedContentAttributes.count == encodedContentAttributes.count' in render
    assert 'AutoremoveTimeoutMessageAttribute(' not in render and 'AutoclearTimeoutMessageAttribute(' not in render
    assert 'retainedPeers' in render and 'globallyUniqueId: record.globallyUniqueId' in render
    assert 'nagramiXCanRetainTemporaryMessage(message)' in body(text, '    public func captureIncoming(')
    assert 'nagramiXCanRetainTemporaryMessage(message)' in body(text, '    public func captureTemporaryBeforeViewing(')
    history = (source / HISTORY).read_text()
    assert 'if nagramiXCanRetainTemporaryMessage(entry.message)' in history
    assert 'view.namespaces.contains(Namespaces.Message.SecretIncoming)' in history
    secret = (source / SECRET).read_text()
    function = body(secret, 'func processSecretChatIncomingDecryptedOperations(')
    assert function.index('case .terminated:') < function.index('transaction.addMessages([message]') < function.index('archive.captureIncoming(message, peers: peers)')
    assert 'attribute.associatedPeerIds' in (source / REPLAY).read_text()
    # Existing durable writer remains authoritative; no best-effort clear/unlink.
    assert 'try? JSONEncoder' not in text
    return {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in [ARCHIVE, HISTORY, SECRET, REPLAY]}


def archive_fixture(source, mode='current'):
    a = (source / ARCHIVE).read_text()
    old = OLD.read_text()
    boundary = (ROOT / 'scripts/tests/NagramiXArchivePostsBoundary.swift').read_text()
    boundary = boundary.replace('    var namespace: Int32 { value < 0 ? 99 : 0 }', '    var namespace: Int32 { value < 0 ? 99 : 0 }\n    var isVerificationCodes: Bool { value == 777000 }')
    boundary = boundary.replace('enum Namespaces { enum Message { static let Cloud:Int32=0 };enum Peer { static let SecretChat:Int32=99 } }', 'enum Namespaces { enum Message { static let Cloud:Int32=0; static let Local:Int32=1; static let SecretIncoming:Int32=2 };enum Peer { static let SecretChat:Int32=99; static let CloudUser:Int32=0; static let CloudGroup:Int32=1; static let CloudChannel:Int32=2 } }')
    boundary = boundary.replace('protocol MessageAttribute {}', 'protocol MessageAttribute { var associatedPeerIds: [PeerId] { get } }\nextension MessageAttribute { var associatedPeerIds:[PeerId] { [] } }')
    boundary = boundary.replace('struct AudioTranscriptionMessageAttribute: MessageAttribute {}', 'struct AudioTranscriptionMessageAttribute: MessageAttribute { var text:String = "" }')
    boundary = boundary.replace('static let Incoming=Flags(rawValue:1)', 'static let Incoming=Flags(rawValue:1); static let CopyProtected=Flags(rawValue:2); static let Unsent=Flags(rawValue:4); static let Sending=Flags(rawValue:8); static let Failed=Flags(rawValue:16); var isSending:Bool { !intersection([.Unsent,.Sending]).isEmpty }')
    boundary = boundary.replace('class Peer { let id:PeerId;init(_ id:PeerId){self.id=id} }', 'class Peer { let id:PeerId; var isCopyProtectionEnabled=false; init(_ id:PeerId){self.id=id} }')
    boundary = boundary.replace('final class TelegramMediaFile:Media {var resource:Any=LocalFileReferenceMediaResource()}', 'final class TelegramMediaFile:Media { var resource:Any=LocalFileReferenceMediaResource(); var isVoice:Bool { name == "voice" }; var isInstantVideo:Bool { name == "round" }; var isVideo:Bool { name == "video" }; var isMusic:Bool { name == "music" }; var isAnimated:Bool { name == "gif" } }')
    boundary = boundary.replace('enum StoreMessageId {case Id(MessageId);case Partial}', 'enum StoreMessageId {case Id(MessageId);case Partial;var peerId:PeerId {if case let .Id(id)=self{return id.peerId};return PeerId(0)}}')
    settings = body(boundary, 'struct NagramiXMessageArchiveSettings {')
    boundary = boundary.replace(settings, '')
    boundary = boundary.replace('func modify(_ f:(T)->T)->T{value=f(value);return value}', 'var afterModify:(()->Void)?;func modify(_ f:(T)->T)->T{value=f(value);if let hook=afterModify{afterModify=nil;hook()};return value}')
    boundary = boundary.replace('    var sequence:Int64=0\n', '    var sequence:Int64=0\n    var afterReservation:(()->Void)?\n')
    boundary=boundary.replace('    var sequence:Int64=0\n', '    var sequence:Int64=0\n    var beforeRestoredReservation:(()->Void)?\n    func reserveRestored(key:String,requests:[NagramiXArchiveMediaRequest])->Int64? {if let hook=beforeRestoredReservation{beforeRestoredReservation=nil;hook()};guard reservations[key]==nil else{return nil};return reserve(key:key,requests:requests)}\n')
    boundary = boundary.replace(r'reservations[key]=(t,requests.map(\.name));return t', r'reservations[key]=(t,requests.map(\.name));if let hook=afterReservation {afterReservation=nil;hook()};return t')
    boundary = boundary.replace('    var messages:[MessageId:Message]=[:]\n', '    var messages:[MessageId:Message]=[:]\n    var peers:[PeerId:Peer]=[:]\n    func getPeer(_ id:PeerId)->Peer?{peers[id]}\n    func withAllMessages(peerId:PeerId,namespace:Int32,_ f:(Message)->Bool){for m in messages.values where m.id.peerId==peerId && m.id.namespace==namespace {if !f(m){break}}}\n')
    boundary += '''
typealias PostboxCoding = Any
let viewOnceTimeout:Int32 = .max
final class AutoremoveTimeoutMessageAttribute:MessageAttribute { let timeout:Int32;init(_ value:Int32){timeout=value} }
final class AutoclearTimeoutMessageAttribute:MessageAttribute { let timeout:Int32;init(_ value:Int32){timeout=value} }
final class EphemeralMessageAttribute:MessageAttribute {}
final class EphemeralOutgoingMessageAttribute:MessageAttribute {}
final class EditedMessageAttribute:MessageAttribute { let date:Int32;init(_ date:Int32){self.date=date} }
final class MediaSpoilerMessageAttribute:MessageAttribute {}
final class WebpagePreviewMessageAttribute:MessageAttribute {}
final class InvertMediaMessageAttribute:MessageAttribute {}
final class ReplyMessageAttribute:MessageAttribute {}
final class OutgoingContentInfoMessageAttribute:MessageAttribute {}
final class InstantPage {let text:String;init(_ text:String){self.text=text}}
final class RichTextMessageAttribute:MessageAttribute {let instantPage:InstantPage;let fullInstantPage:InstantPage?;init(instantPage:InstantPage,fullInstantPage:InstantPage?){self.instantPage=instantPage;self.fullInstantPage=fullInstantPage}}
final class TelegramMediaExpiredContent:Media {}
final class TelegramMediaPaidContent:Media {}
final class TelegramMediaAction:Media {}
final class TelegramMediaPoll:Media {}
final class TelegramMediaContact:Media {}
final class TelegramMediaMap:Media {}
final class TelegramMediaWebpage:Media {}
final class TelegramMediaTodo:Media {}
final class Codec {static var values:[Data:Any]=[:];static func encode(_ object:Any)->Data {let key=Data(UUID().uuidString.utf8);values[key]=object;return key}}
final class BoundaryTimer {init(timeout:Double,repeat:Bool,completion:@escaping()->Void,queue:Queue){};func start(){};func invalidate(){}}
final class ValuePromise<T> {var value:T;init(_ value:T,ignoreRepeated:Bool=false){self.value=value};func set(_ value:T){self.value=value};func get()->Signal<T,NoError>{Signal{$0.putNext(self.value);$0.putCompletion();return EmptyDisposable}}}
struct MessageIdNamespaces {let values:Set<Int32>?;static let all=Self(values:nil);func contains(_ namespace:Int32)->Bool{values?.contains(namespace) ?? true}}
'''
    boundary += '\nextension StoreMessageForwardInfo {\n' + clean(body((source/'submodules/Postbox/Sources/Message.swift').read_text(), '    public init(_ info: MessageForwardInfo)')) + '\n}\n'
    policy = (source / POLICY).read_text()
    policy = policy[policy.index('/// The two persisted switches'):policy.index('/// Visual routing stays voice-specific.')]
    policy += body((source / POLICY).read_text(), 'public func nagramiXCanTranscribeTemporaryMedia(')
    models = a[a.index('public struct NagramiXMessageRevision:'):a.index('/// Marks a synthetic')]
    models += a[a.index('private struct NagramiXArchivePostKey:'):a.index('private final class NagramiXWeakMessageArchive')]
    props = a[a.index('    private let storageStatusValue ='):a.index('    private lazy var mediaStore =')].replace('SwiftSignalKit.Timer', 'BoundaryTimer')
    methods = ['private func restoreMediaOwnership()', 'private func loadPersistedState()', 'private func persist(', 'private func didPersist(', 'private static func key(',
               'private static func retainedContentAttributes(', 'private static func isRegularArchiveIdentifier(',
               'private static func makeRecord(message: StoreMessage,', 'private static func makeRecord(message: Message,',
               'public func captureSent(', 'public func captureIncoming(', 'public func captureTemporaryBeforeViewing(',
               'public func archiveTemporaryExpiration(', 'public func markTemporaryExpired(', 'public func recordIncomingEdit(',
               'public func archiveMessagesBeforeDeletion(', 'public func archiveHistoryBeforeDeletion(', 'public func archiveMessageRangeBeforeDeletion(',
               'private func archiveHistoryDeletion(', 'public func archiveServerDeletion(messageIds:',
               'private func rejectPurgedCapture(', 'public func clearAll()', 'public func postMessageIds(',
               'public func localPostDeletionCandidates(', 'public func postDeletionPlan(', 'public func deleteArchivedPosts(',
               'public func isLocallyDeletedMessage(', 'public func containsArchivedMessage(',
               'public func temporaryInteractionMessage(', 'public func shouldSuppressTemporaryContentReceipt(id:',
               'public func shouldSuppressTemporaryContentReceipt(peerId:', 'public func deletedMessage(',
               'public func deletedMessages(', 'public func snapshotForExpiredMessage(',
               'public func updateTranscriptionAttributes(', 'private func renderDeletedRecord(']
    parts = [boundary, clean(policy), clean(models), clean((source / WRITER).read_text()), clean(body(a, 'private struct NagramiXMessageArchiveSettings'))]
    parts.append('''
private final class Archive {
    let path:String
    let accountPeerId=PeerId(1)
    let queue=Queue()
    let mediaStore=MediaStore()
    let state=Atomic<NagramiXMessageArchiveState>(value:NagramiXMessageArchiveState())
    let renderVersion=Atomic<UInt32>(value:0)
    let replayCapturePending=Atomic<Set<MessageId>>(value:[])
    var revisions=0
    init(_ path:String){self.path=path}
    func publishUpdate(){revisions+=1}
    static func encodedRootObject(_ object:Any)->Data {Codec.encode(object)}
    static func decodedRootObject(_ data:Data)->Any? {Codec.values[data]}
    func mediaRequests(_ record:NagramiXArchivedRecord)->[NagramiXArchiveMediaRequest] {record.content.media.compactMap{Codec.values[$0] as? Media}.map{NagramiXArchiveMediaRequest(name:$0.name)}}
    func localMedia(_ media:Media)->Media {media}
    func localRichPage(_ page:InstantPage)->InstantPage {page}
    func hasCompleteRetainedMedia(_ media:Media)->Bool {if let file=media as? TelegramMediaFile{return file.resource is LocalFileReferenceMediaResource};return true}
    func injectAfterClearBarrier(_ block:@escaping()->Void){captureClearBarrier.afterModify=block}
    var saved:NagramiXMessageArchiveState {state.with{$0}}
    func restore(){_ = loadPersistedState()}
    func restoreOwners(){restoreMediaOwnership()}
    func retry(){_ = persistence.retry()}
    func render(_ id:MessageId,complete:Bool=true)->Message? {guard let r=saved.records[Self.key(id)]else{return nil};return renderDeletedRecord(r,requireCompleteMedia:complete)}
''')
    parts.append(props)
    for marker in methods:
        origin = a
        if mode == 'old-capture' and marker == 'public func captureIncoming(': origin = old
        if mode == 'old-serialize' and marker == 'private static func makeRecord(message: StoreMessage,': origin = old
        if mode == 'old-render' and marker == 'private func renderDeletedRecord(': origin = old
        if mode == 'old-clear' and marker == 'private func rejectPurgedCapture(': origin = old
        if mode == 'old-plan' and marker == 'public func postDeletionPlan(': origin = old
        extracted = body(origin, '    ' + marker)
        if mode == 'old-receipt' and marker.startswith('public func shouldSuppressTemporaryContentReceipt('):
            extracted = extracted[:extracted.index('{') + 1] + ' return false }'
        if mode == 'corrupt-media' and marker == 'private func renderDeletedRecord(':
            extracted=extracted.replace('        guard decodedMedia.count == record.content.media.count else { return nil }\n','')
        if mode == 'corrupt-attributes' and marker == 'private func renderDeletedRecord(':
            extracted=extracted.replace('        guard decodedContentAttributes.count == encodedContentAttributes.count else { return nil }\n','')
        if mode == 'clear-inverse' and marker == 'public func clearAll()':
            extracted=extracted.replace('            empty.records = old.records.filter { (self.captureTickets[$0.key] ?? 0) > ticket }\n','')
        if mode == 'expired-plan' and marker == 'public func postDeletionPlan(':
            extracted=extracted.replace('(live[id] == nil || live[id]?.media.contains(where: { $0 is TelegramMediaExpiredContent }) == true)','live[id] == nil')
        if mode == 'expired-archive-plan' and marker == 'public func postDeletionPlan(':
            extracted=extracted.replace('guard live[id] == nil || isExpiredRetainedPlaceholder(id),','guard live[id] == nil,')
        if mode == 'restored-capture' and marker == 'private func restoreMediaOwnership()':
            extracted=extracted.replace('''                if self.captureClearBarrier.with({ $0 > 0 }) {
                    self.removalTickets[key] = max(self.removalTickets[key] ?? ticket, ticket)
                }
''','')
        if mode == 'restored-clear' and marker == 'private func didPersist(':
            extracted=extracted.replace('self.removalTickets = self.removalTickets.filter { updated.records[$0.key] != nil }','self.removalTickets.removeAll()')
        if mode == 'attribute-edit' and marker == 'public func recordIncomingEdit(':
            extracted=extracted.replace('current.content != replacement.content || current.contentAttributes != replacement.contentAttributes','current.content != replacement.content')
        if mode == 'attribute-removal' and marker == 'public func captureIncoming(':
            extracted=extracted.replace('record.contentAttributes == nil','record.contentAttributes?.isEmpty != false')
        parts.append(clean(extracted))
    parts.append('}\n')
    parts.append(body((source / (CORE + 'Utils/MessageUtils.swift')).read_text(), 'func locallyRenderedMessage(message: StoreMessage, peers: [PeerId: Peer]'))
    parts.append(ARCHIVE_TESTS)
    return '\n'.join(parts)


ARCHIVE_TESTS = r'''
func configure(_ temporary:Bool,_ deleted:Bool=false,_ legacy:Bool=false) {
    UserDefaults.standard.setVolatileDomain(["nagramix.messages.saveTemporaryMessages":temporary,"nagramix.messages.replayViewOnce":legacy,"nagramix.messages.showDeletedMessages":deleted,"nagramix.messages.editHistory":false],forName:UserDefaults.argumentDomain)
}
func sample(_ value:Int32=10,secret:Bool=false,incoming:Bool=true,ttl:Int32?=900,text:String="Текст 😀",media:[Media]=[],attributes:[MessageAttribute]=[],global:Int64?=123)->(StoreMessage,[PeerId:Peer]) {
    let peer=Peer(PeerId(secret ? -8 : 8)),author=Peer(PeerId(9))
    var a=attributes
    if let ttl {a.append(AutoremoveTimeoutMessageAttribute(ttl))}
    let namespace=secret ? (incoming ? Namespaces.Message.SecretIncoming:Namespaces.Message.Local):Namespaces.Message.Cloud
    let m=StoreMessage(id:.Id(MessageId(peerId:peer.id,namespace:namespace,id:value)),customStableId:nil,globallyUniqueId:global,groupingKey:nil,threadId:nil,timestamp:value,flags:incoming ? [.Incoming]:[],tags:0,globalTags:0,localTags:[],forwardInfo:nil,authorId:author.id,text:text,attributes:a,media:media)
    return (m,[peer.id:peer,author.id:author])
}
@main struct TemporaryArchiveTests {
    static func main() throws {
        var checks=0
        func check(_ value:@autoclosure()->Bool,_ label:String){if !value(){FileHandle.standardError.write(Data(("Temporary archive regression: "+label+"\n").utf8));exit(91)};checks+=1}
        let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true)
        defer{try? FileManager.default.removeItem(at:root);UserDefaults.standard.removeVolatileDomain(forName:UserDefaults.argumentDomain)}
        func make(_ name:String)->Archive {Archive(root.appendingPathComponent(name+".json").path)}
        configure(true)
        let archive=make("all")
        var captured:[MessageId]=[]
        let kinds:[Media?]=[nil,TelegramMediaFile("voice"),TelegramMediaFile("round"),TelegramMediaFile("video"),TelegramMediaFile("document"),TelegramMediaImage("photo"),TelegramMediaContact("phone"),TelegramMediaMap("venue"),TelegramMediaWebpage("URL"),TelegramMediaPoll("poll"),TelegramMediaTodo("checklist")]
        for secret in [false,true] {for incoming in [false,true] {for (index,media) in kinds.enumerated(){
            let (store,peers)=sample(Int32(10+captured.count),secret:secret,incoming:incoming,ttl:index%2 == 0 ? 900:viewOnceTimeout,media:media.map{[$0]} ?? [],attributes:[TextEntitiesMessageAttribute(entities:[MessageTextEntity(text:"bold/link")]),MediaSpoilerMessageAttribute(),RichTextMessageAttribute(instantPage:InstantPage("preview"),fullInstantPage:InstantPage("full body"))],global:Int64(captured.count+1000))
            guard case let .Id(id)=store.id else {fatalError()}
            archive.captureIncoming(store,peers:peers);archive.queue.drain();captured.append(id)
            check(archive.saved.records.count==captured.count,"all temporary directions and kinds captured without deleted feature")
            let resolved=archive.temporaryInteractionMessage(id:id,liveMessage:nil)
            check(resolved?.id==id && resolved?.text==store.text && resolved?.author?.id==store.authorId,"readonly resolution keeps identity author text")
            check(resolved?.globallyUniqueId==store.globallyUniqueId,"secret/global identity preserved")
            check(resolved?.media.count==store.media.count && resolved?.media.first?.name==store.media.first?.name,"entire native media metadata retained")
            check(resolved?.attributes.contains{$0 is AutoremoveTimeoutMessageAttribute || $0 is AutoclearTimeoutMessageAttribute} == false,"retained copy has no timer")
            check((resolved?.attributes.compactMap{$0 as? TextEntitiesMessageAttribute}.first?.entities)==[MessageTextEntity(text:"bold/link")],"entities survive")
            check(resolved?.attributes.contains{$0 is MediaSpoilerMessageAttribute} == true,"spoiler attribute survives")
            check(resolved?.attributes.compactMap{$0 as? RichTextMessageAttribute}.first?.fullInstantPage?.text=="full body","rich body survives")
        }}}
        let first=captured[0]
        let before=archive.saved;let revisions=archive.revisions
        _=archive.temporaryInteractionMessage(id:first,liveMessage:nil)
        check(archive.saved==before && archive.revisions==revisions && archive.queue.jobs.isEmpty,"readonly resolver never captures marks expiry or writes")
        check(archive.shouldSuppressTemporaryContentReceipt(id:captured[11]),"missing Postbox row proven incoming temporary suppresses content receipt")
        check(!archive.shouldSuppressTemporaryContentReceipt(id:first),"outgoing retained record does not suppress incoming receipt")
        let secretIncoming=captured[33]
        check(archive.shouldSuppressTemporaryContentReceipt(peerId:secretIncoming.peerId,globallyUniqueId:1033),"secret global receipt resolves stored provenance")
        check(!archive.shouldSuppressTemporaryContentReceipt(peerId:secretIncoming.peerId,globallyUniqueId:99999),"unknown global id remains native")
        check(!archive.shouldSuppressTemporaryContentReceipt(id:MessageId(peerId:PeerId(8),namespace:0,id:99999)),"unknown id remains native")
        let (liveStore,livePeers)=sample(100)
        let live=locallyRenderedMessage(message:liveStore,peers:livePeers)!
        configure(false)
        check(archive.temporaryInteractionMessage(id:live.id,liveMessage:live)?.id==live.id,"OFF returns native live identity")
        check(archive.temporaryInteractionMessage(id:first,liveMessage:nil)==nil && !archive.shouldSuppressTemporaryContentReceipt(id:captured[11]),"OFF hides retained rows and restores receipts")
        check(archive.deletedMessages(peerId:PeerId(8),threadId:nil,minIndex:nil,maxIndex:nil).isEmpty,"OFF retains native history visibility")
        configure(false,false,true)
        check(archive.temporaryInteractionMessage(id:first,liveMessage:nil) != nil,"legacy alias preserves retained visibility")
        configure(true)
        archive.archiveServerDeletion(messageIds:captured,deletedAt:200);archive.queue.drain()
        check(archive.deletedMessages(peerId:PeerId(8),threadId:nil,minIndex:nil,maxIndex:nil,limit:Int.max).count==22,"deleted cloud rows including text remain visible")
        check(archive.deletedMessages(peerId:PeerId(-8),threadId:nil,minIndex:nil,maxIndex:nil,limit:Int.max).count==22,"deleted secret rows including text remain visible")
        let restored=Archive(archive.path);restored.restore()
        check(restored.saved.records.count==44 && restored.temporaryInteractionMessage(id:secretIncoming,liveMessage:nil)?.globallyUniqueId==1033,"JSON restart keeps metadata and global receipt identity")
        var legacyJSON=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:archive.path))) as! [String:Any]
        var records=legacyJSON["records"] as! [String:Any]
        for key in records.keys {var value=records[key] as! [String:Any];value.removeValue(forKey:"globallyUniqueId");value.removeValue(forKey:"contentAttributes");records[key]=value}
        legacyJSON["records"]=records;let legacyPath=root.appendingPathComponent("legacy.json");try JSONSerialization.data(withJSONObject:legacyJSON).write(to:legacyPath)
        let legacy=Archive(legacyPath.path);legacy.restore()
        check(legacy.saved.records.count==44 && !legacy.shouldSuppressTemporaryContentReceipt(peerId:secretIncoming.peerId,globallyUniqueId:1033),"old JSON decodes optional fields without inventing global identity")

        let race=make("race")
        let (raceStore,racePeers)=sample(200)
        race.captureIncoming(raceStore,peers:racePeers);race.queue.drain()
        race.mediaStore.afterReservation={race.clearAll()}
        race.captureIncoming(raceStore,peers:racePeers)
        race.queue.drain()
        check(race.saved.records.isEmpty,"clear barrier rejects preempted formerly live capture after clear")
        let (fresh,freshPeers)=sample(201)
        race.captureIncoming(fresh,peers:freshPeers);race.queue.drain()
        check(race.saved.records.count==1,"fresh capture after clear barrier still allowed")

        let planner=make("plan");let tx=Transaction()
        let (temp,tempPeers)=sample(300);let tempMessage=locallyRenderedMessage(message:temp,peers:tempPeers)!
        tx.messages[tempMessage.id]=tempMessage
        let tempPlan=planner.postDeletionPlan(transaction:tx,messageIds:[tempMessage.id],localCandidates:[])
        check(tempPlan.nativeMessageIds==[tempMessage.id] && tempPlan.localMessageIds==[tempMessage.id],"TEMP-only explicit live deletion freezes native and purge ownership")
        _=planner.deleteArchivedPosts(messageIds:tempPlan.localMessageIds,allowingLiveTemporaryMessageIds:tempPlan.localMessageIds).startStandalone()
        planner.captureIncoming(temp,peers:tempPeers);planner.queue.drain()
        check(planner.saved.records.isEmpty,"explicit intent tombstone blocks native deletion capture even before first snapshot")
        let (ordinary,ordinaryPeers)=sample(301,ttl:nil);let ordinaryMessage=locallyRenderedMessage(message:ordinary,peers:ordinaryPeers)!
        tx.messages[ordinaryMessage.id]=ordinaryMessage
        let ordinaryPlan=planner.postDeletionPlan(transaction:tx,messageIds:[ordinaryMessage.id],localCandidates:[])
        check(ordinaryPlan.localMessageIds.isEmpty && ordinaryPlan.nativeMessageIds==[ordinaryMessage.id],"ordinary deletion stays native when only TEMP enabled")
        configure(true,true)
        let two=make("two");two.captureIncoming(temp,peers:tempPeers);two.queue.drain()
        let firstPlan=two.postDeletionPlan(transaction:tx,messageIds:[tempMessage.id],localCandidates:[])
        check(firstPlan.localMessageIds.isEmpty && firstPlan.nativeMessageIds==[tempMessage.id],"deleted feature preserves first phase")
        two.archiveMessagesBeforeDeletion([tempMessage],deletedAt:300);two.queue.drain();tx.messages.removeValue(forKey:tempMessage.id)
        let secondPlan=two.postDeletionPlan(transaction:tx,messageIds:[tempMessage.id],localCandidates:[tempMessage.id])
        check(secondPlan.localMessageIds==[tempMessage.id] && secondPlan.nativeMessageIds.isEmpty,"deleted feature preserves second local phase")
        _=two.deleteArchivedPosts(messageIds:secondPlan.localMessageIds).startStandalone();two.queue.drain()
        check(two.saved.records.isEmpty,"second phase purges entire retained post")
        configure(false,false)
        let offPlan=two.postDeletionPlan(transaction:tx,messageIds:[ordinaryMessage.id],localCandidates:[])
        check(offPlan.localMessageIds.isEmpty,"both flags OFF keeps native deletion")

        configure(true)
        let inverse=make("inverse-clear");let (oldStore,oldPeers)=sample(500);let (newStore,newPeers)=sample(501)
        inverse.captureIncoming(oldStore,peers:oldPeers);inverse.queue.drain()
        inverse.injectAfterClearBarrier { inverse.captureIncoming(newStore,peers:newPeers);inverse.queue.drain() }
        inverse.clearAll();inverse.queue.drain()
        let newID=MessageId(peerId:PeerId(8),namespace:0,id:501)
        check(inverse.saved.records.count==1 && inverse.temporaryInteractionMessage(id:newID,liveMessage:nil) != nil,"capture newer than barrier committed before clear enqueue survives clear")
        let onDisk=try JSONDecoder().decode(NagramiXMessageArchiveState.self,from:Data(contentsOf:URL(fileURLWithPath:inverse.path)))
        check(onDisk.records==inverse.saved.records,"inverse interleaving fresh snapshot remains durable")

        let failedClear=make("failed-clear");failedClear.captureIncoming(oldStore,peers:oldPeers);failedClear.queue.drain()
        let backup=failedClear.path+".backup"
        try FileManager.default.moveItem(atPath:failedClear.path,toPath:backup)
        try FileManager.default.createDirectory(atPath:failedClear.path,withIntermediateDirectories:false)
        failedClear.clearAll();failedClear.queue.drain()
        check(failedClear.saved.records.count==1,"failed durable clear keeps previous published snapshot and media ownership")
        failedClear.captureIncoming(newStore,peers:newPeers);failedClear.queue.drain()
        try FileManager.default.removeItem(atPath:failedClear.path)
        try FileManager.default.moveItem(atPath:backup,toPath:failedClear.path)
        failedClear.retry()
        check(failedClear.saved.records.count==1 && failedClear.temporaryInteractionMessage(id:newID,liveMessage:nil) != nil,"durable retry applies clear and preserves later accepted capture")


        let (restoredOld,restoredOldPeers)=sample(590,media:[TelegramMediaFile("old-audio")]);let (restoredNew,restoredNewPeers)=sample(591,media:[TelegramMediaFile("new-audio")])
        let restoredSource=make("restored-source");restoredSource.captureIncoming(restoredOld,peers:restoredOldPeers);restoredSource.queue.drain()
        let restoring=Archive(restoredSource.path);restoring.restore()
        restoring.mediaStore.beforeRestoredReservation={
            restoring.injectAfterClearBarrier {restoring.captureIncoming(restoredNew,peers:restoredNewPeers)}
            restoring.clearAll()
        }
        restoring.restoreOwners();restoring.queue.drain()
        check(restoring.saved.records.count==1 && restoring.saved.records.values.first?.id==591,"restoration racing clear preserves only post-barrier fresh record")
        check(restoring.mediaStore.files==["new-audio"],"clear removes newer reservation made by old initialization after barrier; later capture commit cannot forget cleanup")
        check(!restoring.mediaStore.reservations.values.contains{$0.1.contains("old-audio")},"old restored reservation cannot pin removed archive bytes")


        let originalRestore=make("original-restore");originalRestore.captureIncoming(restoredOld,peers:restoredOldPeers);originalRestore.queue.drain()
        let restoringFailurePath=root.appendingPathComponent("restoring-failure.json").path
        try Data(contentsOf:URL(fileURLWithPath:originalRestore.path)).write(to:URL(fileURLWithPath:restoringFailurePath))
        let restoringFailure=Archive(restoringFailurePath);restoringFailure.restore()
        restoringFailure.mediaStore.beforeRestoredReservation={restoringFailure.clearAll()}
        restoringFailure.restoreOwners()
        let restoringBackup=restoringFailurePath+".backup"
        try FileManager.default.moveItem(atPath:restoringFailurePath,toPath:restoringBackup)
        try FileManager.default.createDirectory(atPath:restoringFailurePath,withIntermediateDirectories:false)
        restoringFailure.queue.drain()
        check(restoringFailure.saved.records.count==1 && restoringFailure.mediaStore.files==["old-audio"],"failed clear keeps bytes of late old restoration until durable retry")
        try FileManager.default.removeItem(atPath:restoringFailurePath)
        try FileManager.default.moveItem(atPath:restoringBackup,toPath:restoringFailurePath);restoringFailure.retry()
        check(restoringFailure.saved.records.isEmpty && restoringFailure.mediaStore.files.isEmpty,"durable clear retry finally removes old restored bytes")

        let invalid=make("invalid");let (multi,multiPeers)=sample(600,media:[TelegramMediaImage("one"),TelegramMediaFile("two")],attributes:[MediaSpoilerMessageAttribute(),RichTextMessageAttribute(instantPage:InstantPage("body"),fullInstantPage:nil)])
        invalid.captureIncoming(multi,peers:multiPeers);invalid.queue.drain()
        let pristine=invalid.saved;let recordKey=pristine.records.keys.first!;let initialRecord=pristine.records[recordKey]!
        let invalidID=initialRecord.messageId
        for blobs in [[initialRecord.content.media[0],Data("unknown-blob".utf8)],[initialRecord.content.media[0],Codec.encode("wrong-type")],[Data("bad-one".utf8),Data("bad-two".utf8)]] {
            var corrupt=pristine;var record=initialRecord
            record.content=NagramiXArchivedContent(text:record.content.text,entities:record.content.entities,media:blobs);corrupt.records[recordKey]=record;_ = invalid.state.swap(corrupt)
            check(invalid.temporaryInteractionMessage(id:invalidID,liveMessage:nil)==nil,"unknown or invalid media rejects entire post instead of dropping attachments")
        }
        for blobs in [[initialRecord.contentAttributes![0],Data("unknown-attr".utf8)],[Codec.encode("wrong-attr-type")], [Data("all-attrs-bad".utf8)]] {
            var corrupt=pristine;var record=initialRecord;record.contentAttributes=blobs;corrupt.records[recordKey]=record;_ = invalid.state.swap(corrupt)
            check(invalid.temporaryInteractionMessage(id:invalidID,liveMessage:nil)==nil,"unknown or invalid required content attribute rejects entire post")
        }
        _ = invalid.state.swap(pristine)
        check(invalid.temporaryInteractionMessage(id:invalidID,liveMessage:nil)?.media.count==2,"valid multi-attachment row stays atomic")
        let plaintext=make("plain");let (plain,plainPeers)=sample(601);plaintext.captureIncoming(plain,peers:plainPeers);plaintext.queue.drain()
        check(plaintext.saved.records.count==1 && plaintext.render(MessageId(peerId:PeerId(8),namespace:0,id:601))?.media.isEmpty==true,"original empty-media temporary text is valid")

        let expired=make("expired-plan");expired.captureIncoming(temp,peers:tempPeers);expired.queue.drain()
        let (placeholder,placeholderPeers)=sample(300,ttl:nil,media:[TelegramMediaExpiredContent("expired")])
        tx.messages[tempMessage.id]=locallyRenderedMessage(message:placeholder,peers:placeholderPeers)!
        let expiredPlan=expired.postDeletionPlan(transaction:tx,messageIds:[tempMessage.id],localCandidates:[tempMessage.id])
        check(expiredPlan.nativeMessageIds==[tempMessage.id] && expiredPlan.localMessageIds==[tempMessage.id],"explicit expired placeholder deletes native stub and retained copy together")
        let beforeUndo=expired.saved;check(expired.saved==beforeUndo && expired.queue.jobs.isEmpty,"planning or Undo before commit does not mutate archive")
        _=expired.deleteArchivedPosts(messageIds:expiredPlan.localMessageIds,allowingLiveTemporaryMessageIds:expiredPlan.localMessageIds).startStandalone();expired.queue.drain()
        check(expired.saved.records.isEmpty,"explicit placeholder deletion cannot resurrect retained row")

        let edit=make("edit");let (editOriginal,editPeers)=sample(700,attributes:[MediaSpoilerMessageAttribute()])
        edit.captureIncoming(editOriginal,peers:editPeers);edit.queue.drain()
        let editID=MessageId(peerId:PeerId(8),namespace:0,id:700);let editMessage=locallyRenderedMessage(message:editOriginal,peers:editPeers)!
        let (editReplacement,_)=sample(700,attributes:[InvertMediaMessageAttribute(),RichTextMessageAttribute(instantPage:InstantPage("new rich body"),fullInstantPage:nil)])
        edit.recordIncomingEdit(previousMessage:editMessage,replacementMessage:editReplacement,peers:editPeers,receivedAt:701);edit.queue.drain()
        let edited=edit.temporaryInteractionMessage(id:editID,liveMessage:nil)!
        check(edited.attributes.contains{$0 is InvertMediaMessageAttribute} && !edited.attributes.contains{$0 is MediaSpoilerMessageAttribute},"display-only attribute edits replace retained metadata without requiring text edit")
        check(edited.attributes.compactMap{$0 as? RichTextMessageAttribute}.first?.instantPage.text=="new rich body","rich-only edit retained")
        check(edit.saved.records.values.first?.revisions.isEmpty==true,"display-only edit creates no invented text revision")
        let (removed,_)=sample(700)
        edit.captureIncoming(removed,peers:editPeers);edit.queue.drain()
        check(edit.temporaryInteractionMessage(id:editID,liveMessage:nil)?.attributes.contains{$0 is InvertMediaMessageAttribute || $0 is RichTextMessageAttribute}==false,"known empty attribute list removes old spoiler/rich attributes on refresh")

        let delayed=make("late-ASR");let (voice,voicePeers)=sample(800,media:[TelegramMediaFile("voice")])
        delayed.captureIncoming(voice,peers:voicePeers);delayed.queue.drain();let voiceID=MessageId(peerId:PeerId(8),namespace:0,id:800)
        var result=false
        _=delayed.updateTranscriptionAttributes(id:voiceID,transform:{_ in [AudioTranscriptionMessageAttribute(text:"Текст")]}).startStandalone(next:{result=$0});delayed.queue.drain()
        check(result && delayed.temporaryInteractionMessage(id:voiceID,liveMessage:nil)?.attributes.compactMap{$0 as? AudioTranscriptionMessageAttribute}.first?.text=="Текст","ASR text stored only on retained voice")
        delayed.clearAll()
        _=delayed.updateTranscriptionAttributes(id:voiceID,transform:{_ in [AudioTranscriptionMessageAttribute(text:"late")]}).startStandalone(next:{result=$0});delayed.queue.drain()
        check(!result && delayed.saved.records.isEmpty,"late ASR after clear cannot recreate archive")
        let nativeBefore=make("before-delete");nativeBefore.archiveMessagesBeforeDeletion([tempMessage],deletedAt:900);nativeBefore.queue.drain()
        check(nativeBefore.saved.records.values.first?.wasTemporary==true && nativeBefore.saved.records.values.first?.deletedAt==900,"TEMP-only before native deletion captures existing uncached message")
        configure(true,true)
        let provenance=make("provenance");provenance.captureIncoming(temp,peers:tempPeers);provenance.queue.drain()
        let (untimed,untimedPeers)=sample(300,ttl:nil);let untimedMessage=locallyRenderedMessage(message:untimed,peers:untimedPeers)!
        provenance.archiveMessagesBeforeDeletion([untimedMessage],deletedAt:1000);provenance.queue.drain()
        check(provenance.saved.records.values.first?.wasTemporary==true,"before-delete metadata refresh cannot erase proven temporary provenance")
        configure(true)
        let pendingBytes=make("pending-bytes");let cloudVoice=TelegramMediaFile("voice");cloudVoice.resource="cloud"
        let (pendingStore,pendingPeers)=sample(850,media:[cloudVoice]);pendingBytes.captureIncoming(pendingStore,peers:pendingPeers);pendingBytes.queue.drain()
        let pendingID=MessageId(peerId:PeerId(8),namespace:0,id:850)
        check(pendingBytes.render(pendingID)==nil && pendingBytes.temporaryInteractionMessage(id:pendingID,liveMessage:nil)?.media.count==1,"pending primary bytes cannot hide retained metadata row or claim strict completeness")
        for temporary in [false,true] {for deleted in [false,true] {
            configure(temporary,deleted)
            let matrix=make("matrix-\(temporary)-\(deleted)");matrix.captureIncoming(temp,peers:tempPeers);matrix.queue.drain();tx.messages[tempMessage.id]=tempMessage
            let planned=matrix.postDeletionPlan(transaction:tx,messageIds:[tempMessage.id],localCandidates:[])
            check(planned.nativeMessageIds==[tempMessage.id],"all flag combinations keep live native delete")
            check(planned.localMessageIds==(temporary && !deleted ? [tempMessage.id]:[]),"local explicit purge only TEMP-only mode; deleted feature preserves two phases")
            if temporary || deleted {
                _=matrix.deleteArchivedPosts(messageIds:[tempMessage.id]).startStandalone();matrix.queue.drain()
                check(matrix.saved.records.count==(temporary ? 1:0),"default purge API cannot erase unexpired live record without frozen intent")
            }
        }}

        for temporary in [false,true] {for deleted in [false,true] {for expiredAt in [false,true] {for nativeKind in ["nil","expired","live"] {
            configure(true,true)
            let item=make("full-matrix-\(temporary)-\(deleted)-\(expiredAt)-\(nativeKind)")
            item.captureIncoming(temp,peers:tempPeers);item.queue.drain()
            if expiredAt {item.archiveServerDeletion(messageIds:[tempMessage.id],deletedAt:1200);item.queue.drain()}
            let transaction=Transaction()
            if nativeKind=="expired" {transaction.messages[tempMessage.id]=locallyRenderedMessage(message:placeholder,peers:placeholderPeers)!}
            if nativeKind=="live" {transaction.messages[tempMessage.id]=tempMessage}
            configure(temporary,deleted)
            let plan=item.postDeletionPlan(transaction:transaction,messageIds:[tempMessage.id],localCandidates:expiredAt ? [tempMessage.id]:[])
            let expectLocal:Bool
            if deleted {expectLocal=expiredAt && nativeKind != "live"}
            else {expectLocal=temporary}
            let expectNative = !expectLocal || nativeKind != "nil"
            check(plan.localMessageIds==(expectLocal ? [tempMessage.id]:[]),"full flag/placeholder/live/deletionphase matrix keeps exact local ownership")
            check(plan.nativeMessageIds==(expectNative ? [tempMessage.id]:[]),"full deletion matrix cleans expired native stub and preserves native live path")
        }}}}
        print("Temporary archive actual-method checks: \(checks)")
    }
}
'''


def resource_fixture(source, mode='current'):
    a = (source / ARCHIVE).read_text()
    old = OLD.read_text()
    base = model_boundary(source)
    base = base.replace(clean(body((source / POLICY).read_text(), 'public func nagramiXCanUseTemporaryMediaActions(')), '')
    info_start = base.index('func nagramiXCopyShouldReupload(')
    base = base[:info_start]
    base = base.replace('struct MediaResourceId {', 'struct MediaResourceId: Hashable {')
    base = base.replace('var alternativeRepresentations: [Int] = []', 'var alternativeRepresentations: [TelegramMediaFile] = []')
    image = body(base, 'final class TelegramMediaImage: Media {')
    image = image.replace('[Int]', '[VideoRepresentation]')
    video = native_prefix(source, 'SyncCore_TelegramMediaImage.swift', '    public final class VideoRepresentation:', '        public init(decoder:').replace(': Equatable, PostboxCoding', '')
    image = image.replace('final class TelegramMediaImage: Media {', 'final class TelegramMediaImage: Media {\n' + video)
    base = base.replace(body(base, 'final class TelegramMediaImage: Media {'), image)
    representation = native_prefix(source, 'SyncCore_TelegramMediaImage.swift', 'public final class TelegramMediaImageRepresentation:', '    public init(decoder:').replace(': PostboxCoding, Equatable, CustomStringConvertible', '')
    base = base.replace(body(base, 'struct TelegramMediaImageRepresentation {'), representation)
    base = base.replace('struct TelegramMediaWebpage: Media {}', '')
    base = base.replace('struct TelegramMediaGame: Media {}', '')
    base = base.replace(body(base, 'final class RichTextMessageAttribute: MessageAttribute {'), '')
    base += '''
typealias PixelDimensions = Dimensions
typealias TelegramMediaFileAttribute = String
extension Namespaces.Media { static let CloudGame:Int32=7 }
extension PeerId { init(_ value:Int64){self.init(value:Int(value))} }
class Peer {let id:PeerId;init(_ id:PeerId){self.id=id}}
class TelegramMediaStory:Media {}

extension InstantPage {
    struct Accessor {let value:InstantPage;init(_ value:InstantPage){self.value=value};func _parse()->InstantPage{value}}
}
enum TelegramMediaWebpageContent {case Pending(Int32,String?);case Loaded(TelegramMediaWebpageLoadedContent)}
struct EmptyMediaResource:MediaResource {let id=MediaResourceId(stringRepresentation:"empty")}
extension MessageReference {
    init(peer:Peer,author:Peer?,id:MessageId,timestamp:Int32,incoming:Bool,secret:Bool,threadId:Int64?){self.init(Message(id:id))}
}
struct NagramiXArchiveMediaRequest {let reference:MediaResourceReference;let temporary:Bool;let primary:Bool;let replay:Bool}
struct NagramiXArchivedContent {let media:[Data]}
struct NagramiXArchivedRecord {
    let peerData:[String:Data];let messageId:MessageId;let authorId:Int64?;let timestamp:Int32;let incoming:Bool;let wasTemporary:Bool;let threadId:Int64?;let content:NagramiXArchivedContent;let contentAttributes:[Data]?
}
final class ResourceCodec {static var values:[Data:Any]=[:];static func encode(_ object:Any)->Data{let key=Data(UUID().uuidString.utf8);values[key]=object;return key}}
final class RetainedStore {
    var resources:[String:LocalFileReferenceMediaResource]=[:]
    func localResource(for resource:MediaResource)->MediaResource {resources[resource.id.stringRepresentation] ?? resource}
}
'''
    websource=(source/(CORE+'SyncCore/SyncCore_TelegramMediaWebpage.swift')).read_text()
    base+='\ntypealias TelegramThemeSettings=String\ntypealias CurrencyAmount=String\ntypealias PeerCollectibleColor=String\n'
    base+='enum TelegramMediaWebpageAttribute {\n'+'\n'.join(line for line in websource[websource.index('public enum TelegramMediaWebpageAttribute:'):websource.index('    public init(decoder:',websource.index('public enum TelegramMediaWebpageAttribute:'))].splitlines() if line.startswith('    case '))+'\n}\n'
    for name,first in [('TelegraMediaWebpageThemeAttribute','files'),('TelegramMediaWebpageStickerPackAttribute','flags'),('TelegramMediaWebpageGiftCollectionAttribute','files'),('TelegramMediaWebpageStarGiftAttribute','gift'),('TelegramMediaWebpageGiftAuctionAttribute','gift'),('TelegramMediaWebpageAITextStyleAttribute','emojiFileId')]:
        original=body(websource,'public final class '+name+':')
        fields=original[original.index('    public let '+first+':'):original.index('    public init(decoder:')]
        flags=body(original,'    public struct Flags:') if name=='TelegramMediaWebpageStickerPackAttribute' else ''
        base+='final class '+name+' {\n'+flags+'\n'+fields+'}\n'
    gifts=(source/(CORE+'TelegramEngine/Payments/StarGifts.swift')).read_text()
    gift=body(gifts,'    public struct Gift:');unique=body(gifts,'    public struct UniqueGift:')
    start=gift.index('\n        public let id: Int64\n');simple=gift[start:gift.index('        public init(from decoder:',start)]
    start=unique.index('\n        public let id: Int64\n');extended=unique[start:unique.index('        public init(from decoder:',start)]
    attribute=body(unique,'        public enum Attribute:')
    cases='\n'.join(line for line in attribute.splitlines() if line.startswith('            case model(') or line.startswith('            case pattern(') or line.startswith('            case backdrop(') or line.startswith('            case originalInfo('))
    base+='enum StarGift {case generic(Gift);case unique(UniqueGift)\nstruct Gift {typealias Availability=String;typealias SoldOut=String;typealias Flags=Int;typealias PerUserLimit=String;typealias Background=String;\n'+simple+'}\nstruct UniqueGift {typealias Owner=String;typealias Availability=String;typealias Flags=Int;enum Attribute {typealias Rarity=Int;\n'+cases+'\n}\n'+extended+'}\n}\n'
    base += native_prefix(source, 'SyncCore_TelegramMediaGame.swift', 'public final class TelegramMediaGame:', '    public init(decoder:').replace(': Media, Equatable', ': Media')
    base += native_prefix(source, 'SyncCore_TelegramMediaWebpage.swift', 'public final class TelegramMediaWebpageLoadedContent:', '    public init(decoder:').replace(': PostboxCoding, Equatable', '')
    web = (source / (CORE + 'SyncCore/SyncCore_TelegramMediaWebpage.swift')).read_text()
    web = web[web.index('    public let webpageId:'):web.index('    public init(decoder:', web.index('    public let webpageId:'))]
    base += 'final class TelegramMediaWebpage:Media {\n' + web + '\n}\n'
    base += native_prefix(source, 'SyncCore_TelegramMediaWebFile.swift', 'public class TelegramMediaWebFile:', '    public required init(decoder:').replace(': Media, Codable, Equatable', ': Media')
    invoice = (source / (CORE + 'SyncCore/SyncCore_TelegramMediaInvoice.swift')).read_text()
    base += body(invoice, 'public struct TelegramMediaInvoiceFlags:')
    enum_cases = '\n'.join(line for line in invoice.splitlines() if line.startswith('    case preview(') or line.startswith('    case full('))
    base += '\nenum TelegramExtendedMedia {\n' + enum_cases + '\n}\n'
    base += native_prefix(source, 'SyncCore_TelegramMediaInvoice.swift', 'public final class TelegramMediaInvoice:', '    public init(decoder:').replace(': Media, Equatable', ': Media')
    rich = (source / (CORE + 'SyncCore/SyncCore_RichTextMessageAttribute.swift')).read_text()
    base += '\nfinal class RichTextMessageAttribute:MessageAttribute {\n' + rich[rich.index('    public let instantPage:'):rich.index('    /// The users')] + body(rich, '    public init(instantPage:') + '\n}\n'
    c = (source / (CORE + 'Utils/NagramiXContentCopy.swift')).read_text()
    base += body(c, 'public func nagramiXMapPollMedia(') + '\n' + body(c, 'public func nagramiXPollMediaAttachments(')
    helpers = ['    private func retainedGiftFiles(', '    private func localGift(', '    private func retainedWebpageFiles(', '    private func localWebpageAttribute(', '    private func localRepresentation(', '    private func localImage(', '    private func localFile(', '    private func localRichPage(', '    private func hasCompleteRetainedMedia(']
    local = body(old if mode == 'old-local' else a, '    private func localMedia(_ media: Media) -> Media')
    if mode != 'old-local': local += '\n' + body(a, '    private func localMedia(_ media: Media, depth: Int)')
    requests = body(old if mode == 'old-requests' else a, '    private func mediaRequests(')
    if mode == 'attribute-resources':
        a=a.replace(body(a,'    private func retainedWebpageFiles('),'    private func retainedWebpageFiles(_ attributes: [TelegramMediaWebpageAttribute]) -> [TelegramMediaFile] {return []}')
    if mode == 'invoice-primary':
        a=a.replace('return photoComplete && self.hasCompleteRetainedMedia(media, depth: depth + 1)','return self.hasCompleteRetainedMedia(media, depth: depth + 1)').replace('return photoComplete\n','return true\n')
        a=a.replace('            let photoComplete = invoice.photo.map { self.hasCompleteRetainedMedia($0, depth: depth + 1) } ?? true\n','')
    base += '''
final class ResourceArchive {
    let mediaStore=RetainedStore()
    static func decodedRootObject(_ data:Data)->Any? {ResourceCodec.values[data]}
    func mapped(_ media:Media)->Media {self.localMedia(media)}
    func page(_ page:InstantPage)->InstantPage {self.localRichPage(page)}
    func complete(_ media:Media)->Bool {self.hasCompleteRetainedMedia(media)}
    func requests(_ record:NagramiXArchivedRecord)->[NagramiXArchiveMediaRequest] {self.mediaRequests(record)}
''' + '\n'.join(body(a, marker) for marker in helpers) + '\n' + local + '\n' + requests + '\n}\n'
    return 'import Foundation\n' + clean(base) + RESOURCE_TESTS


def native_prefix(source, filename, start, end):
    text = (source / (CORE + 'SyncCore/' + filename)).read_text()
    value = text[text.index(start):]
    return value[:value.index(end)] + '}\n'


RESOURCE_TESTS = r'''
@main struct TemporaryResourceTests {
    static func main() {
        var checks=0
        func check(_ value:@autoclosure()->Bool,_ label:String){if !value(){FileHandle.standardError.write(Data(("Temporary resource regression: "+label+"\n").utf8));exit(92)};checks+=1}
        let archive=ResourceArchive()
        func rep(_ name:String)->TelegramMediaImageRepresentation {TelegramMediaImageRepresentation(dimensions:Dimensions(width:50,height:90),resource:CloudResource(name),progressiveSizes:[],immediateThumbnailData:nil)}
        let image=TelegramMediaImage(representations:[rep("photo")])
        let file=TelegramMediaFile(resource:CloudResource("file"),size:4,attributes:["video"])
        let webFile=TelegramMediaWebFile(resource:CloudResource("webfile"),mimeType:"image/png",size:4,attributes:["photo"])
        let game=TelegramMediaGame(gameId:10,accessHash:20,name:"game",title:"Title",description:"Description",image:image,file:file)
        let page=InstantPage(blocks:["title","photo","video"],rawMedia:[MediaId(namespace:0,id:1):image,MediaId(namespace:0,id:2):file],isComplete:true,rtl:true,url:"https://example.org",views:50)
        let content=TelegramMediaWebpageLoadedContent(url:"https://example.org",displayUrl:"example.org",hash:11,type:"video",websiteName:"Site",title:"Title",text:"Text",embedUrl:"embed",embedType:"video",embedSize:Dimensions(width:20,height:30),duration:12,author:"Author",isMediaLargeByDefault:true,imageIsVideoCover:true,image:image,file:file,story:nil,attributes:[],instantPage:page)
        let webpage=TelegramMediaWebpage(webpageId:MediaId(namespace:0,id:3),content:.Loaded(content))
        let invoice=TelegramMediaInvoice(title:"Invoice",description:"Description",photo:webFile,receiptMessageId:nil,currency:"USD",totalAmount:123,startParam:"start",extendedMedia:.full(media:file),subscriptionPeriod:30,flags:[],version:1)
        let rich=RichTextMessageAttribute(instantPage:page,fullInstantPage:page)
        let medias:[Media]=[image,file,webFile,game,webpage,invoice]
        for value in medias {check(!archive.complete(value),"cloud primary bytes are incomplete before retention")}
        for name in ["photo","file","webfile"] {archive.mediaStore.resources[name]=LocalFileReferenceMediaResource(localFilePath:"/retained/"+name,randomId:Int64(name.count),isUniquelyReferencedTemporaryFile:false,size:4)}
        let mapped=medias.map{archive.mapped($0)}
        for value in mapped {check(archive.complete(value),"all known nested primary bytes map to retained resources")}
        let localGame=mapped[3] as! TelegramMediaGame
        check(localGame.gameId==10 && localGame.accessHash==20 && localGame.name=="game" && localGame.title=="Title" && localGame.description=="Description","game metadata preserved")
        check(localGame.image!.representations[0].resource is LocalFileReferenceMediaResource && localGame.file!.resource is LocalFileReferenceMediaResource,"game nested files retained")
        guard case let .Loaded(localPage)=(mapped[4] as! TelegramMediaWebpage).content else {fatalError()}
        check(localPage.url==content.url && localPage.displayUrl==content.displayUrl && localPage.hash==11 && localPage.type=="video","webpage identity metadata")
        check(localPage.websiteName=="Site" && localPage.title=="Title" && localPage.text=="Text" && localPage.author=="Author","webpage text fields")
        check(localPage.embedUrl=="embed" && localPage.embedType=="video" && localPage.embedSize?.width==20 && localPage.duration==12,"webpage embed fields")
        check(localPage.isMediaLargeByDefault==true && localPage.imageIsVideoCover && localPage.attributes.isEmpty,"webpage flags and attributes")
        check(localPage.image!.representations[0].resource is LocalFileReferenceMediaResource && localPage.file!.resource is LocalFileReferenceMediaResource,"webpage nested files retained")
        let localInstant=localPage.instantPage!._parse()
        check(localInstant.blocks==page.blocks && localInstant.isComplete && localInstant.rtl && localInstant.url==page.url && localInstant.views==50,"instant page layout metadata")
        check((localInstant.rawMedia[MediaId(namespace:0,id:1)] as! TelegramMediaImage).representations[0].resource is LocalFileReferenceMediaResource,"instant page nested image retained")
        let localInvoice=mapped[5] as! TelegramMediaInvoice
        check(localInvoice.title=="Invoice" && localInvoice.currency=="USD" && localInvoice.totalAmount==123 && localInvoice.startParam=="start" && localInvoice.subscriptionPeriod==30 && localInvoice.version==1,"invoice metadata preserved")
        check(localInvoice.photo!.resource is LocalFileReferenceMediaResource,"invoice photo retained")
        guard case let .full(invoiceMedia)=localInvoice.extendedMedia! else {fatalError()}
        check((invoiceMedia as! TelegramMediaFile).resource is LocalFileReferenceMediaResource,"available invoice full media retained without unlocking preview")
        let localRich=archive.page(page)
        check(localRich.blocks==page.blocks && localRich.rawMedia.count==2 && localRich.views==50,"rich page full metadata")
        check((localRich.rawMedia[MediaId(namespace:0,id:2)] as! TelegramMediaFile).resource is LocalFileReferenceMediaResource,"rich page file retained")
        let peer=Peer(PeerId())
        let record=NagramiXArchivedRecord(peerData:["peer":ResourceCodec.encode(peer)],messageId:MessageId(),authorId:nil,timestamp:1,incoming:true,wasTemporary:true,threadId:nil,content:NagramiXArchivedContent(media:medias.map{ResourceCodec.encode($0)}),contentAttributes:[ResourceCodec.encode(rich)])
        let requests=archive.requests(record)
        check(Set(requests.map{$0.reference.resource.id.stringRepresentation})==Set(["photo","file","webfile"]),"all metadata and rich nested resources reserved exactly once")
        check(requests.count==3 && requests.allSatisfy{$0.temporary && $0.replay},"retained-only mode owns every resource independent of deleted setting")

        let generic=StarGift.Gift(id:1,title:"Gift",file:file,price:3,convertStars:4,availability:"available",soldOut:"no",flags:7,upgradeStars:8,releasedBy:nil,perUserLimit:"limit",lockedUntilDate:10,auctionSlug:"auction",auctionGiftsPerRound:11,auctionStartDate:12,upgradeVariantsCount:13,background:"background")
        let unique=StarGift.UniqueGift(id:2,giftId:3,title:"Unique",number:4,slug:"slug",owner:"owner",attributes:[.model(name:"model",file:file,rarity:5,crafted:true),.pattern(name:"pattern",file:file,rarity:6),.backdrop(name:"backdrop",id:7,innerColor:8,outerColor:9,patternColor:10,textColor:11,rarity:12)],availability:"available",giftAddress:"address",resellAmounts:["3USD"],resellForTonOnly:true,releasedBy:nil,valueAmount:14,valueCurrency:"USD",valueUsdAmount:15,flags:16,themePeerId:nil,peerColor:"color",hostPeerId:nil,minOfferStars:17,craftChancePermille:18)
        let attributeList:[TelegramMediaWebpageAttribute]=[.theme(TelegraMediaWebpageThemeAttribute(files:[file],settings:"theme")),.stickerPack(TelegramMediaWebpageStickerPackAttribute(flags:[.isEmoji,.isTemplate],files:[file])),.giftCollection(TelegramMediaWebpageGiftCollectionAttribute(files:[file])),.starGift(TelegramMediaWebpageStarGiftAttribute(gift:.generic(generic))),.giftAuction(TelegramMediaWebpageGiftAuctionAttribute(gift:.unique(unique),endDate:500)),.aiTextStyle(TelegramMediaWebpageAITextStyleAttribute(emojiFileId:900))]
        let attributeContent=TelegramMediaWebpageLoadedContent(url:"https://example.org/gift",displayUrl:"gift",hash:3,type:nil,websiteName:nil,title:nil,text:nil,embedUrl:nil,embedType:nil,embedSize:nil,duration:nil,author:nil,isMediaLargeByDefault:nil,imageIsVideoCover:false,image:nil,file:nil,story:nil,attributes:attributeList,instantPage:nil)
        let attributeWebpage=TelegramMediaWebpage(webpageId:MediaId(namespace:0,id:7),content:.Loaded(attributeContent))
        let other=ResourceArchive()
        check(!other.complete(attributeWebpage),"file-bearing webpage attributes cannot claim complete before retention")
        let attributeRecord=NagramiXArchivedRecord(peerData:["peer":ResourceCodec.encode(peer)],messageId:MessageId(),authorId:nil,timestamp:1,incoming:true,wasTemporary:true,threadId:nil,content:NagramiXArchivedContent(media:[ResourceCodec.encode(attributeWebpage)]),contentAttributes:nil)
        check(other.requests(attributeRecord).count==1 && other.requests(attributeRecord)[0].reference.resource.id.stringRepresentation=="file","theme sticker and gift resources reserved with exact resource identity")
        other.mediaStore.resources["file"]=LocalFileReferenceMediaResource(localFilePath:"/retained/file",randomId:3,isUniquelyReferencedTemporaryFile:false,size:4)
        let attributeMapped=other.mapped(attributeWebpage)
        check(other.complete(attributeMapped),"attribute-only webpage completes after local resource mapping")
        guard case let .Loaded(mappedAttributes)=(attributeMapped as! TelegramMediaWebpage).content else {fatalError()}
        check(mappedAttributes.attributes.count==6,"all webpage attributes preserved including unresolved AI ID metadata")
        guard case let .theme(theme)=mappedAttributes.attributes[0],case let .stickerPack(stickers)=mappedAttributes.attributes[1],case let .giftCollection(collection)=mappedAttributes.attributes[2],case let .starGift(star)=mappedAttributes.attributes[3],case let .giftAuction(auction)=mappedAttributes.attributes[4],case let .aiTextStyle(ai)=mappedAttributes.attributes[5] else {fatalError()}
        check(theme.settings=="theme" && theme.files[0].resource is LocalFileReferenceMediaResource && stickers.flags.contains(.isTemplate) && stickers.files[0].resource is LocalFileReferenceMediaResource && collection.files[0].resource is LocalFileReferenceMediaResource,"native attribute constructors preserve metadata and replace file resources")
        guard case let .generic(localGeneric)=star.gift,case let .unique(localUnique)=auction.gift else {fatalError()}
        check(localGeneric.file.resource is LocalFileReferenceMediaResource && localGeneric.id==1 && localGeneric.title=="Gift" && localGeneric.price==3 && localGeneric.convertStars==4 && localGeneric.availability=="available" && localGeneric.soldOut=="no" && localGeneric.flags==7 && localGeneric.upgradeStars==8 && localGeneric.perUserLimit=="limit" && localGeneric.lockedUntilDate==10 && localGeneric.auctionSlug=="auction" && localGeneric.auctionGiftsPerRound==11 && localGeneric.auctionStartDate==12 && localGeneric.upgradeVariantsCount==13 && localGeneric.background=="background","generic gift native metadata intact")
        check(localUnique.id==2 && localUnique.giftId==3 && localUnique.title=="Unique" && localUnique.number==4 && localUnique.slug=="slug" && localUnique.owner=="owner" && localUnique.availability=="available" && localUnique.giftAddress=="address" && localUnique.resellAmounts==["3USD"] && localUnique.resellForTonOnly && localUnique.valueAmount==14 && localUnique.valueCurrency=="USD" && localUnique.valueUsdAmount==15 && localUnique.flags==16 && localUnique.peerColor=="color" && localUnique.minOfferStars==17 && localUnique.craftChancePermille==18,"unique gift native metadata intact")
        guard case let .model(modelName,modelFile,modelRarity,crafted)=localUnique.attributes[0],case let .pattern(patternName,patternFile,patternRarity)=localUnique.attributes[1] else {fatalError()}
        check(modelName=="model" && modelRarity==5 && crafted && patternName=="pattern" && patternRarity==6 && modelFile.resource is LocalFileReferenceMediaResource && patternFile.resource is LocalFileReferenceMediaResource && auction.endDate==500 && ai.emojiFileId==900,"unique gift media files and all attribute metadata retained")
        let photoInvoice=TelegramMediaInvoice(title:"Photo",description:"Description",photo:webFile,receiptMessageId:nil,currency:"USD",totalAmount:123,startParam:"",extendedMedia:nil,subscriptionPeriod:nil,flags:[],version:1)
        check(!ResourceArchive().complete(photoInvoice),"invoice photo alone is a real primary resource")
        check(archive.complete(archive.mapped(photoInvoice)),"invoice photo maps independently of extended media")
        let videoImage=TelegramMediaImage(representations:[TelegramMediaImageRepresentation(dimensions:Dimensions(width:1,height:1),resource:archive.mediaStore.resources["photo"]!,progressiveSizes:[],immediateThumbnailData:nil)],videoRepresentations:[TelegramMediaImage.VideoRepresentation(dimensions:Dimensions(width:1,height:1),resource:CloudResource("animation"),startTimestamp:0)],video:file)
        check(!archive.complete(videoImage),"animated image requires primary video resource as well as thumbnail")
        print("Temporary native constructor/resource checks: \(checks)")
    }
}
'''


def run(source, swiftc, temp):
    executions = []
    for mode in ['current', 'old-capture', 'old-serialize', 'old-render', 'old-clear', 'old-plan', 'old-receipt', 'corrupt-media', 'corrupt-attributes', 'clear-inverse', 'expired-plan', 'attribute-edit', 'attribute-removal', 'expired-archive-plan', 'restored-capture', 'restored-clear']:
        path = temp / (mode + '.swift')
        path.write_text(archive_fixture(source, mode))
        for optimized in [False, True]:
            binary = temp / (mode + ('-O' if optimized else '-debug'))
            command = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache')]
            if optimized: command.append('-O')
            subprocess.run([*command, str(path), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if mode == 'current': assert result.returncode == 0, result.stdout + result.stderr
            else: assert result.returncode == 91 and 'Temporary archive regression:' in result.stderr, result.stdout + result.stderr
            executions.append(binary.name + ': ' + (result.stdout.strip() if result.returncode == 0 else result.stderr.strip()))
            print(executions[-1], flush=True)
    for mode in ['resource-current', 'resource-old-requests', 'resource-old-local', 'resource-attribute-resources', 'resource-invoice-primary']:
        implementation = mode.removeprefix('resource-')
        path=temp/(mode+'.swift');path.write_text(resource_fixture(source,implementation))
        for optimized in [False,True]:
            binary=temp/(mode+('-O' if optimized else '-debug'))
            command=[str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'resource-cache')]
            if optimized:command.append('-O')
            subprocess.run([*command,str(path),'-o',str(binary)],check=True)
            result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=60,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
            if implementation=='current':assert result.returncode==0,result.stdout+result.stderr
            else:assert result.returncode==92 and 'Temporary resource regression:' in result.stderr,result.stdout+result.stderr
            executions.append(binary.name+': '+(result.stdout.strip() if result.returncode==0 else result.stderr.strip()));print(executions[-1],flush=True)
    return executions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    outputs = verify(args.source)
    with tempfile.TemporaryDirectory(prefix='temporary-interaction-archive-') as directory:
        executions = run(args.source, args.swiftc, Path(directory)) if args.swiftc else []
        if args.swiftc:
            for n in outputs: subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / n)], check=True)
    report = {'outputs': outputs, 'executions': executions, 'swift_parse': len(outputs) if args.swiftc else 0,
              'boundaries': 'Actual capture/edit/delete, record metadata, phase planning, both clear/capture interleavings, purge and late ASR, readonly resolver, receipt proofs, render and unchanged durable writer; real Foundation atomic JSON/failure/retry. Nested resource collectors/remappers compile against extracted native constructors and native field declarations. Postbox codec, Signal delivery, media store, theme/gift leaf metadata and UIKit are explicit adapters; no native crypto/network/SDK/device/build claim.', 'native_compile': 'pending', 'physical_device': 'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True);args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Temporary interaction archive checks passed')


if __name__ == '__main__': main()
