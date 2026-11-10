import Foundation
#if canImport(QuartzCore)
import QuartzCore
// Apple prechecks compile the real framework declaration, even though time in the test is virtual.
private func nativeMediaTimeImportProbe()->Double {CACurrentMediaTime()}
#endif

// Only the clock/queue and Telegram IO are adapters. SignalKit operators, native playback models
// and identities, and the complete action implementation are appended from pinned source files.
enum Clock {
    static var now=0.0
    static var tasks:[(Double,Int,()->Void)]=[]
    static var sequence=0
    static func enqueue(_ delay:Double,_ action:@escaping()->Void) {
        sequence += 1;tasks.append((now+delay,sequence,action))
    }
    static func advance(_ seconds:Double=0) {
        let end=now+seconds
        var count=0
        while let i=tasks.indices.filter({tasks[$0].0<=end}).min(by:{tasks[$0].0==tasks[$1].0 ? tasks[$0].1<tasks[$1].1 : tasks[$0].0<tasks[$1].0}) {
            let task=tasks.remove(at:i);now=task.0;task.2();count += 1;precondition(count<10000)
        }
        now=end
    }
}
public final class Queue {
    public static func mainQueue()->Queue { Queue() }
    public func async(_ action:@escaping()->Void) { Clock.enqueue(0,action) }
}
public final class Timer {
    private let interval:Double
    private let completion:()->Void
    private var active=false
    public init(timeout:Double,repeat:Bool,completion:@escaping()->Void,queue:Queue) { interval=timeout;self.completion=completion }
    public func start() { active=true;Clock.enqueue(interval) { [weak self] in guard let self,self.active else{return};self.active=false;self.completion() } }
    public func invalidate(){active=false}
}
public enum EnginePeer { public typealias Id=Int64 }
public struct MessageId:Equatable,Hashable { public var peerId:Int64;public var id:Int32 }
public struct MessageIndex:Equatable { public var id:MessageId;public var timestamp:Int32 }
public protocol MessageAttribute {}
public final class NagramiXArchivedMessageAttribute:MessageAttribute {}
public protocol Media {}
public struct Resource { public var id:Int64 }
public final class TelegramMediaFile:Media {
    public var fileId:Int64
    public var resource:Resource
    public var isInstantVideo=true
    public init(_ file:Int64=7,_ resource:Int64=101){fileId=file;self.resource=Resource(id:resource)}
    public func isEqual(to other:TelegramMediaFile)->Bool {fileId==other.fileId && resource.id==other.resource.id}
}
public struct FileMediaReference { public var media:TelegramMediaFile }
public final class EngineRawMessage {
    public var id=MessageId(peerId:44,id:12)
    public var attributes:[MessageAttribute]=[NagramiXArchivedMessageAttribute()]
    public var media:[Media]
    public var index:MessageIndex {MessageIndex(id:id,timestamp:91)}
    public init(_ file:TelegramMediaFile=TelegramMediaFile()){media=[file]}
}
public struct EngineMessage {
    public typealias Id=MessageId
    public typealias Index=MessageIndex
    public let raw:EngineRawMessage
    public init(_ raw:EngineRawMessage){self.raw=raw}
    public var id:MessageId {raw.id}
    public var index:MessageIndex {raw.index}
    public var attributes:[MessageAttribute] {raw.attributes}
}
public protocol InstantPagePlaylistItemIndexProviding {var instantPageMediaIndex:Int{get}}
public struct SharedMediaPlaybackDisplayData:Equatable {}
public enum MusicPlaybackSettingsOrder {case regular}
public enum MusicPlaybackSettingsLooping {case none,item}
public struct AudioPlaybackRate {}
public struct MediaPlayerStatus:Equatable {
    public enum Status:Equatable {case playing,paused,buffering}
    public var status:Status
    public var timestamp:Double
    public var duration:Double
    public var generationTimestamp:Double=0
    public var baseRate:Double=1
}
func testMediaTime()->Double {Clock.now}
public struct TestLocation:SharedMediaPlaylistLocation {public func isEqual(to:SharedMediaPlaylistLocation)->Bool {to is TestLocation}}
public struct TestItem:SharedMediaPlaylistItem {
    public var id:SharedMediaPlaylistItemId
    public var playbackData:SharedMediaPlaybackData?
    public var displayData:SharedMediaPlaybackDisplayData? {nil}
    public var stableId:AnyHashable {12}
}
public final class Account {public var id:Int64;public init(_ id:Int64=1){self.id=id}}
public final class AccountContext {
    public let account:Account
    public let sharedContext:SharedContext
    public init(_ manager:TestMediaManager){account=Account();sharedContext=SharedContext(mediaManager:manager)}
}
public struct SharedContext {public var mediaManager:TestMediaManager}
public final class TestMediaManager {
    public typealias Value=(Account,SharedMediaPlayerItemPlaybackStateOrLoading,MediaManagerPlayerType)?
    public var value:Value=nil
    private var subscribers:[Int:Subscriber<Value,NoError>]=[:]
    private var sequence=0
    public var commands:[String]=[]
    public var nativePlayerIndex=17
    public var nativeSurfaceIndex=19
    public var baseRate=1.5
    public var filteredCalls=0
    public var observerCount:Int{subscribers.count}
    public var globalMediaPlayerState:Signal<Value,NoError> {
        Signal { [weak self] subscriber in
            guard let self else{return EmptyDisposable}
            self.sequence += 1;let id=self.sequence;self.subscribers[id]=subscriber;subscriber.putNext(self.value)
            return ActionDisposable { [weak self] in self?.subscribers.removeValue(forKey:id) }
        }
    }
    public func emit(_ value:Value){self.value=value;for subscriber in Array(subscribers.values){subscriber.putNext(value)}}
    public func filteredPlaylistState(accountId:Int64,playlistId:SharedMediaPlaylistId,itemId:SharedMediaPlaylistItemId,type:MediaManagerPlayerType)->Signal<SharedMediaPlayerItemPlaybackState?,NoError>{
        filteredCalls += 1
        if let (account,state,_)=value,account.id==accountId,case let .state(state)=state,state.playlistId.isEqual(to:playlistId),state.item.id.isEqual(to:itemId){return .single(state)}
        return .single(nil)
    }
    public func playlistControl(_ control:SharedMediaPlayerControlAction,type:MediaManagerPlayerType?){
        switch control {
        case let .seek(timestamp):commands.append("seek:\(timestamp)")
        case let .playback(action):switch action{case .play:commands.append("play");case .pause:commands.append("pause");case .togglePlayPause:commands.append("toggle")}
        default:commands.append("unexpected")
        }
    }
}
enum OpenMessageMode:Equatable {case `default`,timecode(Double)}
struct OpenMessageParams {var mode:OpenMessageMode}
final class TestInteraction {
    var opens:[OpenMessageMode]=[]
    func openMessage(_ message:EngineRawMessage,_ params:OpenMessageParams)->Bool{opens.append(params.mode);return true}
}
struct TestRowItem {let context:AccountContext;let message:EngineRawMessage;let controllerInteraction:TestInteraction}
final class TestRoundRow {
    var item:TestRowItem?
    var media:TelegramMediaFile?
    var nativeActivations=0
    let nagramiXArchivedPlaybackAction=NagramiXArchivedPlaybackAction()
    var nagramiXUsesRetainedPlayback:Bool {item?.message.attributes.contains(where:{$0 is NagramiXArchivedMessageAttribute})==true}
    func shouldOpen()->Bool{true}
    func tap(){activateVideoPlayback()}
}
func nagramiXCanUseTemporaryMediaActions(_ message:EngineRawMessage)->Bool {false}
enum NagramiXTabSettings {static var voiceAutoplayEnabled=false}
enum PeerMessagesPlaylistLocation:SharedMediaPlaylistLocation {
    case recentActions(EngineRawMessage)
    func isEqual(to other:SharedMediaPlaylistLocation)->Bool {other is PeerMessagesPlaylistLocation}
}
final class NativePlaylistProbe {
    var location:SharedMediaPlaylistLocation
    var looping:MusicPlaybackSettingsLooping = .none
    init(_ message:EngineRawMessage){location=PeerMessagesPlaylistLocation.recentActions(message)}
}
final class NativeDecoderProbe {
    var completion:(()->Void)?
    var seeks:[Double]=[]
    var pauses=0
    var plays=0
    func setActionAtEnd(_ action:@escaping()->Void){completion=action}
    func seek(_ time:Double){seeks.append(time)}
    func pause(){pauses += 1}
    func play(){plays += 1}
}
enum NativePlaybackItemProbe {
    case instantVideo(NativeDecoderProbe),audio(NativeDecoderProbe)
    var value:NativeDecoderProbe {switch self{case let .instantVideo(v),let .audio(v):return v}}
    func setActionAtEnd(_ action:@escaping()->Void){value.setActionAtEnd(action)}
    func seek(_ time:Double){value.seek(time)}
    func pause(){value.pause()}
    func play(){value.play()}
}
final class NativeReplayProbe {
    var playbackItem:NativePlaybackItemProbe?
    let playlist:NativePlaylistProbe
    let type=MediaManagerPlayerType.voice
    var nagramiXPlaybackGeneration:UInt64=1
    var currentPlayedToEnd=false
    var scheduledPlaybackAction:SharedMediaPlayerPlaybackControlAction?
    var scheduledStartTime:Double?
    var ended=0
    var next=0
    var playedToEnd:(()->Void)?
    let decoder=NativeDecoderProbe()
    init(_ message:EngineRawMessage){playlist=NativePlaylistProbe(message);playbackItem = .instantVideo(decoder);playedToEnd={ [weak self] in self?.ended += 1 };nagramiXInstallPlaybackCompletion()}
    func control(_ action:SharedMediaPlayerControlAction){if case .next=action{next += 1}}
}
