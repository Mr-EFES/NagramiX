"""Исполнение production-границ архива, маршрута открытия и фильтров плеера."""
from validate_quick_format import block
from validate_temporary_interaction_archive import archive_fixture, clean, ARCHIVE, POLICY

UI = 'submodules/TelegramUI/'
ROUND = UI + 'Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift'
PLAYLIST = UI + 'Components/MediaManager/PeerMessagesMediaPlaylist/Sources/PeerMessagesMediaPlaylist.swift'


def archive(source):
    text = archive_fixture(source)
    # Reuse the explicit archive/storage adapters, but compile the real public
    # attribute (including its backward-compatible Postbox codec), not a fake
    # new member. The old suite executes separately at its inverse checkpoint.
    text = text[:text.index('@main struct TemporaryArchiveTests')]
    old = block(text, 'struct NagramiXArchivedMessageAttribute:')
    actual = clean(block((source / ARCHIVE).read_text(), 'public final class NagramiXArchivedMessageAttribute:'))
    text = text.replace(old, actual)
    text += '\n' + clean(block((source / ARCHIVE).read_text(), 'public extension Message {'))
    postbox = (source / 'submodules/Postbox/Sources/Message.swift').read_text()
    text += '\nextension Message {\n' + clean(block(postbox, '    public func withUpdatedStableId(')) + '\n}\n'
    policy = (source / POLICY).read_text()
    for marker in ['public func nagramiXCanUseTemporaryMediaActions(', 'public func nagramiXCanPlayTemporaryVoiceInline(']:
        text += '\n' + clean(block(policy, marker))
    text += '\nextension Archive {\n' + '\n'.join(clean(block((source/ARCHIVE).read_text(), marker)) for marker in ['    public func replayCopyForInteraction(', '    public func transcriptionMessage(']) + '\n}\n'
    text += CODEC + ARCHIVE_TESTS
    return text


def consumption(source):
    import validate_temporary_interaction_consumption as receipts
    paths=[POLICY,receipts.MARK,receipts.SECRET,receipts.APPLY,receipts.SYNC,
           receipts.CORE+'State/ManagedSynchronizeConsumeMessageContentsOperations.swift',
           receipts.CORE+'State/AccountViewTracker.swift',
           receipts.CORE+'State/ManagedSynchronizeMarkAllUnseenPersonalMessagesOperations.swift']
    fixture=receipts.fixture({p:(source/p).read_text() for p in paths},source)
    old='final class NagramiXArchivedMessageAttribute:MessageAttribute {let isTemporary:Bool;init(_ value:Bool){isTemporary=value}}'
    assert old in fixture
    fixture=fixture.replace(old,old.replace('let isTemporary:Bool;', 'let deletedAt:Int32=0;let isViewOnce=false;let isTemporary:Bool;'))
    fixture=fixture.replace('let(lt,lp)=prepare([text])','let(lt,_)=prepare([text])')
    notice=clean(block((source/ARCHIVE).read_text(),'    var nagramiXShowsArchiveNotice: Bool {'))
    start=fixture.index('for pair in [(false,false),(true,false),(false,true),(true,true)]')
    return fixture[:start]+'\nextension Message {\n'+notice+'\n}\n@main struct ConsumptionTests {static func main(){\n'+fixture[start:]+'\n}}\n'


CODEC = r'''
final class PostboxDecoder {
    let values:[String:Any];init(_ values:[String:Any]){self.values=values}
    func decodeInt32ForKey(_ key:String,orElse:Int32)->Int32{values[key] as? Int32 ?? orElse}
    func decodeBoolForKey(_ key:String,orElse:Bool)->Bool{values[key] as? Bool ?? orElse}
}
final class PostboxEncoder {
    var values:[String:Any]=[:]
    func encodeInt32(_ value:Int32,forKey:String){values[forKey]=value}
    func encodeBool(_ value:Bool,forKey:String){values[forKey]=value}
}
'''


ARCHIVE_TESTS = r'''
@main struct PlaybackIdentityArchiveTests {
    static func main() throws {
        var checks=0
        func check(_ value:@autoclosure()->Bool,_ reason:String){if !value(){FileHandle.standardError.write(Data(("Temporary identity regression: "+reason+"\n").utf8));exit(91)};checks+=1}
        let directory=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)
        defer{try? FileManager.default.removeItem(at:directory);UserDefaults.standard.removeVolatileDomain(forName:UserDefaults.argumentDomain)}
        var ordinal:Int32=100
        for secret in [false,true] {for incoming in [false,true] {for once in [false,true] {
        for kind in ["voice","round","video","photo","text"] {for temporary in [false,true] {for deleted in [false,true] {
            ordinal+=1;configure(temporary,deleted)
            let archive=Archive(directory.appendingPathComponent("\(ordinal).json").path)
            let payload:[Media]=kind=="text" ? [] : kind=="photo" ? [TelegramMediaImage(kind)] : [TelegramMediaFile(kind)]
            let (store,peers)=sample(ordinal,secret:secret,incoming:incoming,ttl:once ? viewOnceTimeout:900,media:payload)
            let live=locallyRenderedMessage(message:store,peers:peers)!.withUpdatedStableId(stableId:197)
            archive.captureIncoming(store,peers:peers);archive.queue.drain()
            let before=archive.saved
            let shown=archive.temporaryInteractionMessage(id:live.id,liveMessage:live)!
            check(!shown.attributes.contains{$0 is NagramiXArchivedMessageAttribute},"valid live original is never replaced by a synthetic snapshot")
            check(nagramiXIsViewOnceMessage(shown)==once,"source once badge survives both switches and direction")
            check(shown.attributes.contains{$0 is AutoremoveTimeoutMessageAttribute},"original TTL is not stripped")
            check(shown.stableId==197 && shown.media.count==payload.count && shown.text==live.text,"original identity and content preserved")
            check(!shown.nagramiXShowsArchiveNotice,"playback is not deletion")
            check(archive.saved==before,"display lookup is readonly")
            check(nagramiXCanRetainTemporaryMessage(shown)==temporary,"consumption policy depends only on temporary switch")
            check(nagramiXCanUseTemporaryMediaActions(shown)==temporary,"deleted switch alone does not bypass live consumption")
            if temporary || deleted {
                check(archive.saved.records.count==1,"available temporary bytes captured independently for deletion")
                check(archive.saved.records.values.first?.originalViewOnce==once,"exact source provenance retained")
            } else {check(archive.saved.records.isEmpty,"both OFF capture nothing")}
            if temporary {
                let exported=archive.replayCopyForInteraction(id:live.id,liveMessage:live)!
                check(exported.attributes.contains{$0 is NagramiXArchivedMessageAttribute},"explicit copy exports retained snapshot rather than forwarding live source")
                check(!exported.nagramiXShowsArchiveNotice && nagramiXIsViewOnceMessage(exported)==once,"export resolution does not delete or lose source provenance")
            }
            archive.archiveMessagesBeforeDeletion([live],deletedAt:1000);archive.queue.drain()
            if deleted {
                check(archive.deletedMessage(id:live.id) != nil,"genuine deletion always remains available with deleted ON")
                let copy=archive.deletedMessage(id:live.id)!
                check(copy.nagramiXShowsArchiveNotice,"genuine deletion always has deleted notice")
                check(nagramiXIsViewOnceMessage(copy)==once,"deleted round/voice/photo/video retains exact once provenance")
                check(copy.stableId==197 && copy.media.count==payload.count,"deletion preserves row and entire payload")
                check(!copy.attributes.contains{$0 is AutoremoveTimeoutMessageAttribute || $0 is AutoclearTimeoutMessageAttribute},"local snapshot cannot restart TTL")
                check(nagramiXCanUseTemporaryMediaActions(copy),"deleted local snapshot supports actions even with temporary OFF")
                check(nagramiXCanTranscribeTemporaryMedia(copy)==(kind=="voice" || kind=="round"),"deleted voice and round remain transcribable")
                let rerender=archive.temporaryInteractionMessage(id:live.id,liveMessage:copy)!
                check(rerender.nagramiXShowsArchiveNotice,"resolver never resurrects a deleted snapshot")
                let reloaded=Archive(archive.path);reloaded.restore()
                check(reloaded.deletedMessage(id:live.id)?.nagramiXShowsArchiveNotice==true,"deletion persists across restart")
                check(reloaded.deletedMessage(id:live.id).map(nagramiXIsViewOnceMessage)==once,"once provenance persists across restart")
                archive.captureIncoming(store,peers:peers);archive.queue.drain()
                check(archive.deletedMessage(id:live.id)?.nagramiXShowsArchiveNotice==true,"late ingestion cannot erase deletion")
                configure(true,false)
                check(archive.deletedMessage(id:live.id)==nil,"temporary ON does not make deleted content fresh or visible with deleted OFF")
                check(archive.deletedMessages(peerId:live.id.peerId,threadId:nil,minIndex:nil,maxIndex:nil).isEmpty,"deleted visibility has one switch")
            } else {
                check(archive.deletedMessage(id:live.id)==nil,"deleted OFF hides actual deleted copy even if temporary ON")
            }
        }}}}}}
        configure(true,true)
        let race=Archive(directory.appendingPathComponent("race.json").path)
        let (store,peers)=sample(900,ttl:viewOnceTimeout,media:[TelegramMediaFile("round")])
        race.captureIncoming(store,peers:peers);race.queue.drain()
        let expired=race.snapshotForExpiredMessage(id:MessageId(peerId:PeerId(8),namespace:0,id:900))!
        check(expired.nagramiXShowsArchiveNotice,"first expired frame already has notice")
        check(race.saved.records.values.first?.deletedAt==nil,"test exercises pending archive persistence")
        let jobs=race.queue.jobs.count
        let resolved=race.temporaryInteractionMessage(id:expired.id,liveMessage:expired)!
        check(resolved.nagramiXShowsArchiveNotice,"pending persistence cannot remove deleted presentation")
        check(race.queue.jobs.count==jobs,"interaction adds no receipt, expiry or writer operation")
        let (placeholder,placeholderPeers)=sample(900,ttl:viewOnceTimeout,media:[TelegramMediaExpiredContent("expired")])
        let rawExpired=locallyRenderedMessage(message:placeholder,peers:placeholderPeers)!
        configure(true,false)
        check(race.transcriptionMessage(id:expired.id,liveMessage:rawExpired)==nil,"hidden expired ASR cannot resolve a fresh unmarked snapshot")
        configure(true,true)
        check(race.transcriptionMessage(id:expired.id,liveMessage:rawExpired)?.nagramiXShowsArchiveNotice==true,"expired ASR keeps deletion before queued persistence")
        race.queue.drain()
        check(race.deletedMessage(id:expired.id)?.nagramiXShowsArchiveNotice==true,"persisted deletion remains marked")
        var json=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:race.path))) as! [String:Any]
        var records=json["records"] as! [String:[String:Any]]
        for key in records.keys{records[key]?.removeValue(forKey:"originalViewOnce")}
        json["records"]=records
        try JSONSerialization.data(withJSONObject:json).write(to:URL(fileURLWithPath:race.path))
        let legacy=Archive(race.path);legacy.restore()
        check(legacy.deletedMessage(id:expired.id)?.nagramiXShowsArchiveNotice==true,"old JSON remains readable and deleted")
        check(legacy.deletedMessage(id:expired.id).map(nagramiXIsViewOnceMessage)==false,"unknown old origin never guessed from generic TTL")
        let live=locallyRenderedMessage(message:store,peers:peers)!.withUpdatedStableId(stableId:197)
        legacy.captureTemporaryBeforeViewing(message:live);legacy.queue.drain()
        check(legacy.deletedMessage(id:expired.id).map(nagramiXIsViewOnceMessage)==true,"known live source enriches old archive with exact once provenance")
        check(legacy.deletedMessage(id:expired.id)?.nagramiXShowsArchiveNotice==true,"enriching old provenance never resurrects deleted content")
        let attribute=NagramiXArchivedMessageAttribute(deletedAt:123,revisions:[],isTemporary:true,isViewOnceReplay:true,isViewOnce:true)
        let encoder=PostboxEncoder();attribute.encode(encoder)
        let decoded=NagramiXArchivedMessageAttribute(decoder:PostboxDecoder(encoder.values))
        check(decoded.isViewOnce && decoded.isTemporary && decoded.deletedAt==123,"real attribute codec retains independent flags")
        check(!NagramiXArchivedMessageAttribute(decoder:PostboxDecoder([:])).isViewOnce,"old Postbox codec defaults safely")
        print("PASS temporary archive identity checks: \(checks)")
    }
}
'''


def ui(source):
    iv=(source/ROUND).read_text()
    # Compile the actual predicates and activation prefix. Native rendering,
    # playlist storage and async scheduling are explicit, small adapters.
    flags=iv[iv.index('            let isViewOnceMessage ='):iv.index('            if isSecretMedia {')]
    flags=flags.replace('            let theme = item.presentationData.theme\n','')
    activate=block(iv,'    private func activateVideoPlayback()')
    activate=activate[:activate.index('        if self.infoBackgroundNode.alpha.isZero {')]+'        nativeFetchOnly += 1\n    }'
    progress=block(iv,'    private func progressPressed()')
    progress=progress[:progress.index('        if let status = self.status {')]+'        nativeFetchOnly += file.fileId\n    }'
    playback=(source/PLAYLIST).read_text()
    filters=[]
    for marker in ['private func aroundMessagesFromView(', 'private func navigatedMessageFromView(']:
        body=block(playback,marker)
        filters.append(block(body,'    let filteredEntries = view.entries.filter {')+'\nreturn filteredEntries.map{$0.message.id}\n')
    gate=block((source/(UI+'Sources/ChatController.swift')).read_text(),'                        if (file.isVoice || file.isInstantVideo) && message.minAutoremoveOrClearTimeout == viewOnceTimeout')
    return UI_BOUNDARY+'\nfunc flags(_ item:Item)->(Bool,Bool,Bool){\n'+flags+'\nreturn(isViewOnceMessage,requiresDisposableViewOnce,isSecretMedia)\n}\n'+'''
final class Node {
var item:Item?;var media:File?=File();var nativeFetchOnly=0;var allow=true;var status:Status?
let nagramiXArchivedPlaybackAction=NagramiXArchivedPlaybackAction()
func shouldOpen()->Bool{allow}
'''+block(iv,'    private var nagramiXIsArchivedInstantVideo: Bool {').replace('private ','')+'\n'+block(iv,'    private var nagramiXUsesRetainedPlayback: Bool {').replace('private ','')+'\n'+activate.replace('private ','')+'\n'+progress.replace('private ','')+'\n}\n'+''.join('func filter'+str(i)+'(_ view:View)->[Int]{\n'+f+'}\n' for i,f in enumerate(filters))+'''
final class Router {
var screenCaptureManager:Capture?=Capture();var disposableOpens=0
func openViewOnceMediaMessage(_ message:EngineMessage){disposableOpens+=1}
func open(_ message:Message,_ file:File)->Bool {
'''+gate+'\nreturn true\n}\n}\n'+UI_TESTS


UI_BOUNDARY=r'''
import Foundation
protocol MessageAttribute {}
struct NagramiXArchivedMessageAttribute:MessageAttribute {}
struct Message {
 var id=1;var timeout:Int32? = viewOnceTimeout;var retained=true;var archived=false
 var containsSecretMedia=true
 var attributes:[MessageAttribute]{archived ? [NagramiXArchivedMessageAttribute()]:[]}
 var minAutoremoveOrClearTimeout:Int32?{timeout}
}
let viewOnceTimeout:Int32 = .max
// Exact provenance is executed separately with real production policy/codec.
func nagramiXIsViewOnceMessage(_ m:Message)->Bool{m.timeout==viewOnceTimeout}
func nagramiXCanUseTemporaryMediaActions(_ m:Message)->Bool{m.retained}
struct File {var fileId=10;var isVoice=false;var isInstantVideo=true}
struct Account{var id=1}
enum MediaStatus{case playbackStatus;case fetchStatus}
struct Status{var mediaStatus:MediaStatus}
enum Control{case playback(Playback);enum Playback{case togglePlayPause}}
enum PlayerType{case voice}
final class Manager{var toggles=0;func playlistControl(_ control:Control,type:PlayerType){toggles+=1}}
final class SharedContext{let mediaManager=Manager()}
final class Context{var account=Account();let sharedContext=SharedContext()}
struct OpenMessageParams{enum Mode{case `default`};let mode:Mode}
struct EngineMessage{let value:Message;init(_ value:Message){self.value=value}}
final class Capture{var isRecordingActive=false}
final class Interaction {
 var opens=0
 @discardableResult func openMessage(_ message:Message,_ params:OpenMessageParams)->Bool{opens+=1;return true}
}
struct Item{var message:Message;let context=Context();let controllerInteraction=Interaction()}
final class NagramiXArchivedPlaybackAction {
 var pending:[()->Void]=[]
 func activate(context:Context,message:Message,isCurrent:@escaping()->Bool,open:@escaping()->Void){pending.append{if isCurrent(){open()}}}
 func drain(){let work=pending;pending=[];work.forEach{$0()}}
}
struct Entry{let message:Message}
struct View{let entries:[Entry]}
'''


UI_TESTS=r'''
@main struct TemporaryPlayerRoutingTests {
 static func main(){
 var checks=0
 func check(_ v:@autoclosure()->Bool,_ why:String){if !v(){FileHandle.standardError.write(Data(("Temporary player regression: "+why+"\n").utf8));exit(91)};checks+=1}
 for once in [false,true] {for retained in [false,true] {for archived in [false,true] {
  let message=Message(timeout:once ? viewOnceTimeout:900,retained:retained,archived:archived)
  let item=Item(message:message);let f=flags(item)
  check(f.0==once,"once badge independent of retention")
  check(f.1==(once && !retained),"disposable presentation independent of badge")
  check(f.2==(!retained),"retention uses normal visible player")
  let node=Node();node.item=item;node.progressPressed()
  if archived {check(item.controllerInteraction.opens==0,"archive waits for its identity lease");node.nagramiXArchivedPlaybackAction.drain();check(item.controllerInteraction.opens==1,"archive one tap opens after resolution")}
  else if retained {
   check(item.controllerInteraction.opens==1 && node.nagramiXArchivedPlaybackAction.pending.isEmpty,"live retained first tap uses normal open and native identity")
   node.status=Status(mediaStatus:.playbackStatus);node.progressPressed();node.progressPressed()
   check(item.context.sharedContext.mediaManager.toggles==2 && item.controllerInteraction.opens==1,"playing and paused retained circle uses native pause/resume without replacing playlist")
  }
  else {check(node.nativeFetchOnly==10,"OFF native fetch route preserved")}
  let router=Router()
  check(router.open(message,File()) == (!once || retained),"retained circle uses full native navigation and transition callbacks")
  router.screenCaptureManager?.isRecordingActive=true
  check(router.open(message,File()) == !once,"one-time screen recording safeguard retained")
 }} }
 let node=Node();let first=Item(message:Message(archived:true));node.item=first;node.progressPressed();node.item=Item(message:Message(id:2,archived:true));node.nagramiXArchivedPlaybackAction.drain();check(first.controllerInteraction.opens==0,"stale archive tap cannot start another row")
 let entries=[Message(id:1,timeout:nil,retained:false),Message(id:2,retained:false),Message(id:3,retained:true),Message(id:4,timeout:900,retained:false)].map{Entry(message:$0)}
 let view=View(entries:entries)
 check(filter0(view)==[1,3,4],"around playlist includes selected retained view-once original")
 check(filter1(view)==[1,3,4],"navigated playlist includes retained view-once and keeps native OFF exclusion")
 print("PASS temporary native routing checks: \(checks)")
 }
}
'''


def negatives(archive_text, ui_text):
    result=[]
    def add(name,text,old,new,diagnostic):
        assert old in text,name
        result.append((name,text.replace(old,new),diagnostic))
    add('live-shadow',archive_text,'} else if record.deletedAt == nil {','} else if false {','valid live original')
    add('deletion-race',archive_text,'return settings.showDeletedMessages ? liveMessage : nil','return self.renderDeletedRecord(self.state.with { $0.records[Self.key(id)]! }, requireCompleteMedia: false)','pending persistence')
    add('origin-lost',archive_text,'isViewOnce: record.originalViewOnce == true','isViewOnce: false','exact once provenance')
    add('origin-guessed',archive_text,'isViewOnce: record.originalViewOnce == true','isViewOnce: record.wasTemporary','exact once provenance')
    add('deleted-hidden-by-temp',archive_text,'guard deleted ? settings.showDeletedMessages :','guard deleted ? (settings.showDeletedMessages && settings.saveTemporaryMessages) :','genuine deletion')
    add('local-actions-off',archive_text,'return UserDefaults.standard.bool(forKey: "nagramix.messages.showDeletedMessages")','return false && UserDefaults.standard.bool(forKey: "nagramix.messages.showDeletedMessages")','deleted local snapshot supports actions')
    add('hidden-expired-asr',archive_text,'guard NagramiXMessageArchiveSettings.current.showDeletedMessages else { return nil }','guard NagramiXMessageArchiveSettings.current.showDeletedMessages || NagramiXMessageArchiveSettings.current.saveTemporaryMessages else { return nil }','hidden expired ASR')
    add('badge-hidden',ui_text,'let isViewOnceMessage = nagramiXIsViewOnceMessage(item.message)','let isViewOnceMessage = nagramiXIsViewOnceMessage(item.message) && !nagramiXCanUseTemporaryMediaActions(item.message)','once badge independent')
    add('live-archive-player',ui_text,'return self.nagramiXIsArchivedInstantVideo','return self.nagramiXIsArchivedInstantVideo || self.item?.message.retained == true','live retained first tap')
    add('pause-resets-player',ui_text,'if let status = self.status, case .playbackStatus = status.mediaStatus','if let status = self.status, case .fetchStatus = status.mediaStatus','native pause/resume')
    add('playlist-exclusion',ui_text,'entry.message.minAutoremoveOrClearTimeout == viewOnceTimeout && !nagramiXCanUseTemporaryMediaActions(entry.message)','entry.message.minAutoremoveOrClearTimeout == viewOnceTimeout','around playlist')
    add('disposable-retained',ui_text,'&& (!nagramiXCanUseTemporaryMediaActions(message) || self.screenCaptureManager?.isRecordingActive == true)','&& true','retained circle uses full native navigation')
    return result
