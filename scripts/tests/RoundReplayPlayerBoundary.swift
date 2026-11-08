// Native identities/filter/activation are inserted verbatim by the validator.
// These state containers replace account persistence, a player and its queue.
public typealias AccountRecordId=Int
public struct Account {public var id:Int;public init(_ id:Int){self.id=id}}
public struct PlaybackStatus:Equatable {
    public enum Kind:Equatable {case paused;case playing;case buffering}
    public var status:Kind;public var duration:Double;public var timestamp:Double
    public init(_ status:Kind,_ duration:Double,_ timestamp:Double){self.status=status;self.duration=duration;self.timestamp=timestamp}
}
public struct PlayerItem {public let id:SharedMediaPlaylistItemId;public init(_ id:SharedMediaPlaylistItemId){self.id=id}}
public struct SharedMediaPlayerItemPlaybackState:Equatable {
    public let playlistId:SharedMediaPlaylistId;public let item:PlayerItem;public let status:PlaybackStatus
    public init(_ playlistId:SharedMediaPlaylistId,_ itemId:SharedMediaPlaylistItemId,_ status:PlaybackStatus){self.playlistId=playlistId;self.item=PlayerItem(itemId);self.status=status}
    public static func ==(a:Self,b:Self)->Bool {a.playlistId.isEqual(to:b.playlistId) && a.item.id.isEqual(to:b.item.id) && a.status==b.status}
}
public enum SharedMediaPlayerItemPlaybackStateOrLoading {case loading;case state(SharedMediaPlayerItemPlaybackState)}
public enum Control {public enum Playback {case togglePlayPause};case playback(Playback)}
public final class Manager {
    public let channel=Channel<(Account,SharedMediaPlayerItemPlaybackStateOrLoading)?>(nil)
    public let musicChannel=Channel<(Account,SharedMediaPlayerItemPlaybackStateOrLoading,Bool)?>(nil)
    var voiceMediaPlayerState:Signal<(Account,SharedMediaPlayerItemPlaybackStateOrLoading)?,NoError>{channel.signal}
    var musicMediaPlayerState:Signal<(Account,SharedMediaPlayerItemPlaybackStateOrLoading,Bool)?,NoError>{musicChannel.signal}
    public private(set) var toggles=0
    public init(){}
    public func playlistControl(_ action:Control,type:MediaManagerPlayerType){toggles+=1}
    // INSERT_NATIVE_FILTER
}
public final class SharedContext {public let mediaManager=Manager();public init(){}}
public final class AccountContext {public var account=Account(1);public let sharedContext=SharedContext();public init(){}}
