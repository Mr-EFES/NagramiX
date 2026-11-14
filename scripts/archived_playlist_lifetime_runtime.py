"""Фактический playlist updateState и native цепочка его отмены; движок — граница."""
from validate_quick_format import block
from doh_empty_action_runtime import library

PLAYLIST = 'submodules/TelegramUI/Components/MediaManager/PeerMessagesMediaPlaylist/Sources/PeerMessagesMediaPlaylist.swift'
SHARED = 'submodules/TelegramUI/Sources/SharedMediaPlayer.swift'
MANAGER = 'submodules/TelegramUI/Sources/MediaManager.swift'
STATE = 'submodules/AccountContext/Sources/SharedMediaPlayer.swift'


def fixture(source):
    playlist = (source / PLAYLIST).read_text()
    code = library(source)
    code += '\n' + block((source / 'submodules/SSignalKit/SwiftSignalKit/Source/Promise.swift').read_text(), 'public final class Promise<T> {')
    code += '\n' + block((source / 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Mapping.swift').read_text(), 'public func filter<T, E>(')
    code += '\n' + BOUNDARY
    # Exact native state declaration and initializer, with only the item graph
    # and its equality edge adapted; rendering/decoding is outside this probe.
    code += '\n' + block((source / STATE).read_text(), 'public final class SharedMediaPlaylistState: Equatable {')
    code += '\nfinal class PlaylistProbe {\n' + PLAYLIST_STORAGE
    code += '\n' + block(playlist, '    private func updateState() {')
    code += '\n' + PLAYLIST_METHODS + '\n}\n'
    code += 'final class PlayerProbe {\nvar cancelled:(()->Void)?;var stops=0\nfunc stop(){stops+=1}\ninit(_ playlist:PlaylistProbe){\n'
    code += block((source / SHARED).read_text(), '        playlist.currentItemDisappeared = { [weak self] in')
    code += '\n}\n}\n'
    code += 'final class ManagerProbe {\nvar voiceMediaPlayer:PlayerProbe?\nfunc install(_ voiceMediaPlayer:PlayerProbe){\nself.voiceMediaPlayer=voiceMediaPlayer\nlet installHandler = { [weak self] in\n'
    code += block((source / MANAGER).read_text(), '                                voiceMediaPlayer.cancelled = { [weak voiceMediaPlayer] in')
    code += '\n};installHandler()\n}\n}\n'
    return code + '\n' + TESTS


BOUNDARY = r'''
private var checks=0
private func check(_ value:@autoclosure()->Bool,_ message:String){
 if !value(){print("FAIL: "+message);exit(96)};checks+=1
}
protocol MessageAttribute {}
final class NagramiXArchivedMessageAttribute:MessageAttribute {}
public final class Message {
 public let id:Int;public let index:Int;let attributes:[MessageAttribute];let kind:String
 init(_ id:Int,archived:Bool=false,kind:String="round"){self.id=id;index=id;attributes=archived ? [NagramiXArchivedMessageAttribute()]:[];self.kind=kind}
}
public final class MessageMediaPlaylistItem {
 public let message:Message;let isSavedMusic:Bool
 init(message:Message,isSavedMusic:Bool){self.message=message;self.isSavedMusic=isSavedMusic}
}
public typealias SharedMediaPlaylistItem = MessageMediaPlaylistItem
public enum MusicPlaybackSettingsOrder {case regular,reversed,random}
public enum MusicPlaybackSettingsLooping {case none,item,all}
// The production state equality helper's item graph is not used to decide
// whether the original Postbox message must be observed.
func arePlaylistItemsEqual(_ a:SharedMediaPlaylistItem?,_ b:SharedMediaPlaylistItem?)->Bool{a?.message.id==b?.message.id}
enum TelegramEngine {enum EngineData {enum Item {enum Messages {struct Message {let id:Int}}}}}
final class EngineDataProbe {
 let updates=ValuePromise<Bool>(ignoreRepeated:false);var subscriptions=0;var active=0
 func subscribe(_ item:TelegramEngine.EngineData.Item.Messages.Message)->Signal<Message?,NoError>{
  subscriptions+=1
  return Signal{[self] subscriber in
   active+=1
   let d=updates.get().start(next:{exists in subscriber.putNext(exists ? Message(item.id):nil)})
   return ActionDisposable{[self] in active-=1;d.dispose()}
  }
 }
}
struct EngineProbe {let data=EngineDataProbe()}
struct ContextProbe {let engine=EngineProbe()}
enum LocationProbe {
 case messages,singleMessage,custom,recentActions(Message),savedMusic
 func effectiveLocation(context:ContextProbe)->LocationProbe{self}
}
'''

PLAYLIST_STORAGE = r'''
 let context=ContextProbe();let messagesLocation:LocationProbe
 var currentItem:(current:Message,around:[Message])?
 var currentlyObservedMessageId:Int?
 let currentlyObservedMessageDisposable=MetaDisposable()
 var currentItemDisappeared:(()->Void)?
 var loadingItem=false;var playedToEnd=false
 var order=MusicPlaybackSettingsOrder.regular;var looping=MusicPlaybackSettingsLooping.none
 let stateValue=Promise<SharedMediaPlaylistState>()
 init(_ location:LocationProbe,message:Message){messagesLocation=location;currentItem=(message,[]);updateState()}
 deinit{currentlyObservedMessageDisposable.dispose()}
'''
PLAYLIST_METHODS = r'''
 func refresh(){updateState()}
 func setCurrent(_ message:Message?,around:[Message]=[]){currentItem=message.map{($0,around)};updateState()}
 func state()->SharedMediaPlaylistState{
  var value:SharedMediaPlaylistState?
  let d=stateValue.get().start(next:{value=$0});d.dispose();return value!
 }
 func seedOldObserver(){
  currentlyObservedMessageId=currentItem?.current.id
  currentlyObservedMessageDisposable.set(context.engine.data.subscribe(.init(id:currentItem!.current.id)).start(next:{[weak self] message in if message==nil{self?.currentItemDisappeared?()}}))
 }
'''

TESTS = r'''
@main struct PlaylistLifetimeTests {static func main(){
 for kind in ["round","voice","music"] {for loop in [MusicPlaybackSettingsLooping.none,.item,.all] {
  let message=Message(7,archived:true,kind:kind)
  let playlist=PlaylistProbe(.recentActions(message),message:message)
  let player=PlayerProbe(playlist);let manager=ManagerProbe();manager.install(player)
  playlist.looping=loop;playlist.refresh()
  // Engine's missing-original reply arrives after SharedMediaPlayer installs
  // its cancellation callback, as with the asynchronous production lookup.
  playlist.context.engine.data.updates.set(false)
  check(manager.voiceMediaPlayer === player && player.stops==0,"retained missing original never cancels native player")
  check(playlist.context.engine.data.subscriptions==0 && playlist.currentlyObservedMessageId==nil,"retained snapshot never subscribes to original ID")
  for _ in 0..<8 {playlist.refresh();playlist.context.engine.data.updates.set(false)}
  check(manager.voiceMediaPlayer === player && player.stops==0,"repeated state refresh keeps same native owner")
  let state=playlist.state()
  check(state.item?.message === message && !state.loading && state.looping==loop,"native item data and looping remain intact")
  playlist.context.engine.data.updates.set(true)
  playlist.seedOldObserver();check(playlist.context.engine.data.active==1,"test seeds an old observation")
  playlist.refresh();playlist.context.engine.data.updates.set(false)
  check(playlist.context.engine.data.active==0 && player.stops==0,"retained branch disposes old original watcher")
  playlist.setCurrent(nil)
  check(playlist.state().item==nil,"explicit native end still clears item")
 }}
 for kind in ["round","voice","view-once"] {
  let message=Message(9,kind:kind)
  for location in [LocationProbe.messages,.singleMessage,.recentActions(message),.savedMusic] {
   let playlist=PlaylistProbe(location,message:message)
   let player=PlayerProbe(playlist);let manager=ManagerProbe();manager.install(player)
   playlist.context.engine.data.updates.set(true)
   check(playlist.context.engine.data.subscriptions==1 && manager.voiceMediaPlayer === player,"ordinary source still observes existing message")
   playlist.refresh()
   check(playlist.context.engine.data.subscriptions==1,"unchanged native ID does not duplicate observers")
   playlist.context.engine.data.updates.set(false)
   check(manager.voiceMediaPlayer==nil && player.stops==1,"ordinary original deletion still cancels native player")
   playlist.context.engine.data.updates.set(false)
   check(player.stops==1,"native disappearance callback remains take one")
  }
 }
 let message=Message(3,archived:true)
 for location in [LocationProbe.messages,.singleMessage] {
  let playlist=PlaylistProbe(location,message:message)
  check(playlist.context.engine.data.subscriptions==1,"archive attribute alone never bypasses native message location")
 }
 let custom=PlaylistProbe(.custom,message:Message(1))
 check(custom.context.engine.data.subscriptions==0,"custom-source policy unchanged")
 let ordering=PlaylistProbe(.messages,message:Message(5))
 ordering.setCurrent(Message(5),around:[Message(3),Message(7)])
 check(ordering.state().previousItem?.message.id==3 && ordering.state().nextItem?.message.id==7,"native neighbor ordering unchanged")
 let oldData:EngineDataProbe
 do {let p=PlaylistProbe(.messages,message:Message(8));oldData=p.context.engine.data;check(oldData.active==1,"ordinary watcher active before deinit")}
 check(oldData.active==0,"native observer lifetime releases on deinit")
 print("PASS archived playlist production checks: \(checks)")
}}
'''
