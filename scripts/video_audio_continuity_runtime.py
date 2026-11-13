"""Production audio ownership, activation and shared-clock fragments with explicit adapters."""
from validate_quick_format import block
from system_web_picture_in_picture_runtime import CONTENT

CHUNK = 'submodules/MediaPlayer/Sources/ChunkMediaPlayerV2.swift'
AUDIO = 'submodules/TelegramAudio/Sources/ManagedAudioSession.swift'


def fixture(source):
    web = (source / CONTENT).read_text()
    fields = web[web.index('    private var nagramiXPlaybackRequested'):web.index('    private var nagramiXBackgroundObserver')].replace('private ', '')
    policy = block(web, '    private func nagramiXUpdateManagedPlayback()').replace('private func', 'func', 1)
    methods = '\n'.join(block(web, marker) for marker in ['    func play()', '    func pause()', '    func togglePlayPause()'])
    start = web.index('            switch status.status {')
    end = web.index('            self.nagramiXUpdateManagedPlayback()', start)
    status = 'func status(_ status: Status) {\n' + web[start:end].replace('status.status', 'status') + 'self.nagramiXUpdateManagedPlayback()\n}'
    audio = (source / AUDIO).read_text()
    start = audio.index('        let nagramiXPlaybackNeedsConfiguration: Bool')
    end = audio.index('            self.currentTypeAndOutputMode = (type, outputMode)', start)
    route = audio[start:end] + 'self.configured += 1\n}\n'
    start = audio.index('                    let nagramiXConfigureAtomically: Bool')
    end = audio.index('                    if nagramiXConfigureAtomically {', start)
    atomic = audio[start:end] + 'return nagramiXConfigureAtomically\n'
    chunk = (source / CHUNK).read_text()
    start = chunk.index('        let isTooShortToPlay =')
    end = chunk.index('        if !isBuffering {', start)
    clock = chunk[start:end] + '\nreturn effectiveRate\n'
    activation = block(chunk, '                        control.setupAndActivate(synchronous: false,')
    # block() includes the closure's closing brace, not the call's closing parenthesis.
    activation += ')'
    media = (source / 'submodules/TelegramUI/Sources/MediaManager.swift').read_text()
    release = block(media, '    private var nagramiXMayReleaseIdleAudio: Bool').replace('private var', 'var', 1)
    trigger = block(media, '            if strongSelf.isCurrent && value')
    return BOUNDARY + '''
final class ReleaseManager {
 var currentPictureInPictureNode:Player?
 var isCurrent=true
 var nagramiXBackgroundVideoOwners=Set<UUID>()
 let nagramiXVideoNowPlayingRegistry=Registry()
 let audioSession=IdleAudio()
''' + release + '''
 func delayed(value:Bool){let strongSelf=self
''' + trigger + '''
 }
}
final class WebPolicy {
''' + fields + '''
 var nagramiXInForeground=true
 let playerNode=Player()
 let audioSessionManager=Manager()
 let audioSessionDisposable=MetaDisposable()
''' + methods + '\n' + status + '\n' + policy + '''\n}
final class RoutePolicy {
 var currentTypeAndOutputMode: (Session,Output)? = (.play(mixWithOthers:false), .system)
 var configured=0
 func setup(type:Session,outputMode:Output) {
''' + route + '''\n}
 func atomic(type:Session,nagramiXRestoringMixedPlayback:Bool)->Bool {
''' + atomic + '''\n}}
final class ChunkMediaPlayerV2 {
 static let endTolerance=0.1
 var isSoundEnabled=true,hasSound=true,hasAudioSession=false,isPlaying=true
 var baseRate=1.0,hasClockMovedSinceSeek=false
 var nagramiXAudioSessionGeneration:UInt64=1
 var updates=0
 func updateInternalState(){updates+=1}
 func activate(control:Control,generation:UInt64) {
 let request: (Control)->Void = { [weak self] control in
''' + activation + '''\n}
 request(control)
 }
 func rate(duration:Double,isBuffering:Bool)->Double {
''' + clock + '\n}}\n' + TESTS


BOUNDARY = r'''
import Foundation
enum NoError: Error {}
final class Queue {
 static let shared=Queue();static func mainQueue()->Queue{shared}
 var jobs:[()->Void]=[]
 var isCurrent:()->Bool = {true}
 func async(_ job:@escaping()->Void){jobs.append(job)}
 func drain(){var count=0;while !jobs.isEmpty {count+=1;precondition(count<100);jobs.removeFirst()()}}
}
final class Subscriber {var completed=false;func putCompletion(){completed=true}}
struct EmptyDisposition {}
let EmptyDisposable=EmptyDisposition()
struct Signal {let action:(Subscriber)->EmptyDisposition;init(_ action:@escaping(Subscriber)->EmptyDisposition){self.action=action}}
precedencegroup SignalPrecedence {associativity:left}
infix operator |> : SignalPrecedence
func |> (signal:Signal,transform:(Signal)->Signal)->Signal{transform(signal)}
func runOn(_ queue:Queue)->(Signal)->Signal{{signal in signal}}
extension Queue {static func mainQueue()->Queue{shared}}
final class MetaDisposable {var value:Int?;func set(_ value:Int?){self.value=value}}
enum Session:Equatable {case play(mixWithOthers:Bool);case record(Bool,Bool,Bool)}
enum Output:Equatable {case system}
struct State {}
final class Manager {
 var activations:[()->Void]=[],deactivations:[()->Signal]=[]
 var pushes=0
 func push(audioSessionType:Session,once:Bool,activate:@escaping(State)->Void,deactivate:@escaping(Bool)->Signal)->Int {
  precondition(audioSessionType == .play(mixWithOthers:false) && once)
  pushes+=1;activations.append({activate(State())});deactivations.append({deactivate(false)});return pushes
 }
 func acquire(_ i:Int=0){activations[i]();Queue.shared.drain()}
 func interrupt(_ i:Int=0){let signal=deactivations[i]();let subscriber=Subscriber();_ = signal.action(subscriber);precondition(subscriber.completed)}
}
final class Player {
 var nagramiXIsSystemPiPActive=false,background=false
 var plays=0,pauses=0
 func play(){plays+=1}
 func pause(){pauses+=1}
 func setNagramiXBackgroundPlayback(_ value:Bool){background=value}
}
final class IdleAudio {var drops=0;func dropAll(){drops+=1}}
final class Registry {var pip=false,background=false;func preferred(backgroundEnabled:Bool)->Int?{pip || (backgroundEnabled && background) ? 1:nil}}
enum Status {case playing,paused,buffering(Bool,Bool,Double,Bool)}
enum NagramiXTabSettings {static var backgroundVideoPlaybackEnabled=true}
struct AVAudioSession {
 enum Category {case playback,playAndRecord,ambient}
 enum Mode {case `default`,voiceChat}
 struct CategoryOptions:OptionSet {let rawValue:Int;static let mixWithOthers=CategoryOptions(rawValue:1)}
 static var session=AVAudioSession()
 static func sharedInstance()->AVAudioSession{session}
 var category=Category.playback,mode=Mode.default,categoryOptions=CategoryOptions([])
}
final class Control {
 var callbacks:[(State)->Void]=[]
 func setupAndActivate(synchronous:Bool,_ completion:@escaping(State)->Void){callbacks.append(completion)}
 func complete(){callbacks[0](State());Queue.shared.drain()}
}
'''.replace('extension Queue {static func mainQueue()->Queue{shared}}', '')

TESTS = r'''
@main struct Tests {
 static func main(){
  var count=0
  func check(_ value:@autoclosure()->Bool,_ why:String){if !value(){FileHandle.standardError.write(Data((why+"\n").utf8));exit(96)};count+=1}
  do {
   let web=WebPolicy();web.status(.buffering(true,true,0,true))
   check(web.audioSessionManager.pushes==0,"initial preload buffering cannot steal another video's audio")
  }
  do {
   let web=WebPolicy();web.play()
   check(web.playerNode.plays==0,"web waits for audio before play")
   web.status(.paused);web.status(.buffering(true,false,0,false))
   check(web.nagramiXPendingPlay && web.nagramiXPlaybackRequested,"initial status cannot cancel pending user play")
   web.audioSessionManager.acquire();check(web.playerNode.plays==1,"one play follows activation")
   web.status(.paused);web.status(.buffering(true,false,0,false))
   check(web.nagramiXHasManagedAudio && web.playerNode.plays==1,"stale paused report cannot release a dispatched play before acknowledgement")
   for _ in 0..<120{web.status(.playing)}
   check(web.playerNode.plays==1 && web.audioSessionManager.pushes==1,"status ticks cannot recreate session or replay")
   web.pause();web.audioSessionManager.acquire()
   check(web.playerNode.plays==1,"stale activation cannot undo user pause")
   web.play();web.audioSessionManager.acquire(1);check(web.playerNode.plays==2,"next explicit play recovers without app restart")
  }
  do {
   let web=WebPolicy();web.play();web.pause();web.play()
   web.audioSessionManager.acquire(0);check(web.playerNode.plays==0,"old lease callback cannot start a new request")
   web.audioSessionManager.acquire(1);check(web.playerNode.plays==1,"current lease alone starts playback")
   web.playerNode.nagramiXIsSystemPiPActive=true;web.audioSessionManager.interrupt(1)
   check(!web.playerNode.background && web.nagramiXAudioSuspended,"interruption suspends PiP background guard before pause")
   for _ in 0..<120{web.status(.playing)}
   check(web.audioSessionManager.pushes==2 && web.playerNode.plays==1,"stale playing polls cannot fight audio interruption")
   web.status(.paused);web.status(.playing)
   check(web.audioSessionManager.pushes==3,"PiP resume after confirmed pause can reacquire audio")
  }
  for enabled in [false,true] {for pip in [false,true] {
   NagramiXTabSettings.backgroundVideoPlaybackEnabled=enabled
   let web=WebPolicy();web.play();web.audioSessionManager.acquire();web.nagramiXBackgroundOwners.insert(UUID());web.playerNode.nagramiXIsSystemPiPActive=pip
   web.nagramiXInForeground=false;web.nagramiXUpdateManagedPlayback()
   check(web.playerNode.background == (enabled || pip),"background and PiP retain their existing settings precedence")
   check(web.nagramiXHasManagedAudio == (enabled || pip),"background OFF releases ordinary audio only")
  }}
  for enabled in [false,true] {for pending in [false,true] {for pipEntry in [false,true] {for owner in [false,true] {
   NagramiXTabSettings.backgroundVideoPlaybackEnabled=enabled
   let media=ReleaseManager();if pending{media.currentPictureInPictureNode=Player()};media.nagramiXVideoNowPlayingRegistry.pip=pipEntry
   if owner{media.nagramiXBackgroundVideoOwners.insert(UUID())}
   media.delayed(value:true)
   check(media.audioSession.drops == ((!pending && !pipEntry && !(enabled && owner)) ? 1:0),"delayed idle release rechecks current PiP and background ownership")
  }}}}
  do {
   NagramiXTabSettings.backgroundVideoPlaybackEnabled=true
   let media=ReleaseManager();media.nagramiXVideoNowPlayingRegistry.background=true
   media.delayed(value:true)
   check(media.audioSession.drops==1,"paused ordinary Now Playing entry cannot retain an idle session")
  }
  for category in [AVAudioSession.Category.playback,.playAndRecord,.ambient] {for mode in [AVAudioSession.Mode.default,.voiceChat] {for mixed in [false,true] {
   AVAudioSession.session.category=category;AVAudioSession.session.mode=mode;AVAudioSession.session.categoryOptions=mixed ? [.mixWithOthers]:[]
   let route=RoutePolicy();route.setup(type:.play(mixWithOthers:false),outputMode:.system)
   check(route.configured == ((category != .playback || mode != .default || mixed) ? 1:0),"actual session drift must repair cached playback mode")
  }}}
  for mixed in [false,true] {
   check(RoutePolicy().atomic(type:.play(mixWithOthers:mixed),nagramiXRestoringMixedPlayback:false),"playback restores incompatible category and mode atomically")
  }
  for sound in [false,true] {for hasSound in [false,true] {for acquired in [false,true] {for playing in [false,true] {for buffering in [false,true] {
   let chunk=ChunkMediaPlayerV2();chunk.isSoundEnabled=sound;chunk.hasSound=hasSound;chunk.hasAudioSession=acquired;chunk.isPlaying=playing
   let rate=chunk.rate(duration:60,isBuffering:buffering)
   check(rate == ((playing && !buffering && (!sound || !hasSound || acquired)) ? 1:0),"shared video clock waits for enabled audio")
  }}}}}
  for stale in [false,true] {for sound in [false,true] {for hasSound in [false,true] {
   let chunk=ChunkMediaPlayerV2(),control=Control();chunk.isSoundEnabled=sound;chunk.hasSound=hasSound
   chunk.activate(control:control,generation:1);if stale{chunk.nagramiXAudioSessionGeneration=2};control.complete()
   check(chunk.hasAudioSession == (!stale && sound && hasSound),"stale audio acquisition cannot resurrect old renderer")
  }}}
  print("video audio continuity production checks: \(count)")
 }
}
'''
