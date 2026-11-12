"""Выполнить новые production AVKit/WebKit мосты с явными adapter границами."""
from validate_quick_format import block
BASE='submodules/TelegramUniversalVideoContent/Sources/'
WEB=BASE+'WebEmbedPlayerNode.swift';AV=BASE+'SystemVideoContent.swift';CONTENT=BASE+'WebEmbedVideoContent.swift'
GALLERY='submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift'


def fixture(source):
    av=block((source/AV).read_text(),'final class NagramiXAVPlayerPictureInPicture:')
    web=block((source/WEB).read_text(),'private final class NagramiXWebSystemPictureInPicture:')
    policy=block((source/CONTENT).read_text(),'    private func nagramiXUpdateManagedPlayback()')
    media=block((source/'submodules/TelegramUI/Sources/MediaManager.swift').read_text(),'    private func nagramiXUpdateBackgroundVideoState()').replace('private func','func',1)
    prefix='final class RegistryBoundary {var pip=false;func preferred(backgroundEnabled:Bool)->Int?{pip ? 1:nil}}\nfinal class MediaPolicyBoundary {let nagramiXVideoNowPlayingRegistry=RegistryBoundary();var nagramiXBackgroundVideoOwners=Set<UUID>();let nagramiXBackgroundVideoPlaying=ValuePromise<Bool>(false,ignoreRepeated:true);'+media+'}\n'
    return BOUNDARY+prefix+av+'\n'+web+'''\nfinal class WebPolicyBoundary {
 var playerNode=WebPlayerBoundary()
 var nagramiXBackgroundOwners=Set<UUID>()
 var nagramiXPlaybackRequested=false
 var nagramiXInForeground=true
 var nagramiXHasManagedAudio=false
 let audioSessionManager=ManagedAudioBoundary()
 let audioSessionDisposable=MetaDisposable()
'''+policy.replace('private func','func',1)+'\n}\n'+TESTS


def script(source):
    text=(source/WEB).read_text();a=text.index('    private static let script = #"""\n')+len('    private static let script = #"""\n');b=text.index('\n"""#',a)
    return text[a:b]


def negatives(text):
    for name,old,new,why in [
        ('different-player','self.controller = AVPictureInPictureController(playerLayer: layer)','self.controller = AVPictureInPictureController(playerLayer: AVPlayerLayer(player: AVPlayer()))','AVKit uses the original player layer'),
        ('foreground-only-policy','self.isActive || !self.owners.isEmpty ? .continuesIfPossible : .automatic','self.isActive ? .continuesIfPossible : .automatic','background owner enables AVPlayer background policy'),
        ('lost-other-owner','self.owners.remove(id)','self.owners.removeAll()','one owner cannot revoke another background session'),
        ('accept-stale-web-state','request == self.request','!request.isEmpty','stale WebKit callbacks cannot start PiP'),
        ('global-pip-audio-drop','self.nagramiXBackgroundVideoPlaying.set(hasSystemPiP || (','self.nagramiXBackgroundVideoPlaying.set(hasSystemPiP && (','global manager keeps system PiP audio independently of background checkbox'),
        ('web-background-off','self.playerNode.setNagramiXBackgroundPlayback(permitted)','self.playerNode.setNagramiXBackgroundPlayback(false)','web background policy reaches the live frame bridge'),
    ]:
        assert text.count(old)==1,(name,text.count(old))
        yield name,text.replace(old,new,1),why

BOUNDARY=r'''
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
final class ValuePromise<T> {
 var value:T
 init(_ value:T,ignoreRepeated:Bool){self.value=value}
 func set(_ value:T){self.value=value}
}
protocol AVPictureInPictureControllerDelegate:AnyObject {}
final class AVPlayer {
 enum Policy {case automatic,continuesIfPossible}
 var audiovisualBackgroundPlaybackPolicy=Policy.automatic
 var pauses=0
 func pause(){pauses+=1}
}
final class AVPlayerLayer {let player:AVPlayer;init(player:AVPlayer){self.player=player}}
final class AVPictureInPictureController {
 static var last:AVPictureInPictureController?
 static var supported=true
 let layer:AVPlayerLayer
 weak var delegate:AVPictureInPictureControllerDelegate?
 var isPictureInPictureActive=false,isPictureInPicturePossible=true
 var canStartPictureInPictureAutomaticallyFromInline=false
 var starts=0,stops=0
 init?(playerLayer:AVPlayerLayer){self.layer=playerLayer;Self.last=self}
 static func isPictureInPictureSupported()->Bool{supported}
 func startPictureInPicture(){starts+=1}
 func stopPictureInPicture(){stops+=1}
}
final class UIApplication {
 enum State {case active,inactive,background}
 static let shared=UIApplication()
 static let willEnterForegroundNotification=Notification.Name("fixture-foreground")
 static let didEnterBackgroundNotification=Notification.Name("fixture-background")
 var applicationState=State.active
}
final class Scheduler {
 var jobs:[()->Void]=[]
 func asyncAfter(deadline:DispatchTime,execute:@escaping()->Void){jobs.append(execute)}
 func run(){let pending=jobs;jobs=[];for job in pending{job()}}
}
enum DispatchQueue {static let main=Scheduler()}
protocol WKScriptMessageHandler:AnyObject {func userContentController(_ userContentController:WKUserContentController,didReceive message:WKScriptMessage)}
struct WKUserScript {enum Time {case atDocumentEnd};let source:String;init(source:String,injectionTime:Time,forMainFrameOnly:Bool){self.source=source}}
final class WKUserContentController {var scripts:[WKUserScript]=[];func add(_ handler:WKScriptMessageHandler,name:String){};func addUserScript(_ script:WKUserScript){scripts.append(script)}}
final class WKFrameInfo {let id:Int;init(_ id:Int){self.id=id}}
struct WKScriptMessage {var name="nagramiXSystemPiP";let body:Any;let frameInfo:WKFrameInfo}
enum WKContentWorld {case page}
final class WKWebView {
 var calls:[([String:Any],WKFrameInfo?)]=[]
 func evaluateJavaScript(_ text:String,in frame:WKFrameInfo?,in world:WKContentWorld,completionHandler:Any?) {
  let marker="window.nagramiXNativePiPDispatch("
  let start=text.range(of:marker)!.upperBound
  let json=String(text[start..<text.index(before:text.endIndex)])
  calls.append((try! JSONSerialization.jsonObject(with:Data(json.utf8)) as! [String:Any],frame))
 }
}
enum NoError{}
struct Signal {static func complete()->Signal{Signal()}}
final class MetaDisposable {var value:Int?;func set(_ value:Int?){self.value=value}}
final class ManagedAudioBoundary {
 enum Session {case play(mixWithOthers:Bool)}
 var pushes=0
 func push(audioSessionType:Session,activate:(Int)->Void,deactivate:@escaping(Int)->Signal)->Int {pushes+=1;activate(0);return pushes}
}
enum NagramiXTabSettings {static var backgroundVideoPlaybackEnabled=true}
final class WebPlayerBoundary {
 var nagramiXIsSystemPiPActive=false
 var background=false,pauses=0
 func setNagramiXBackgroundPlayback(_ value:Bool){background=value}
 func pause(){pauses+=1}
}
'''
TESTS=r'''
@main struct SystemWebPiPTests {
 static func main(){
  var checks=0
  func check(_ condition:@autoclosure()->Bool,_ why:String){if !condition(){FileHandle.standardError.write(Data(("System web PiP regression: "+why+"\n").utf8));exit(91)};checks+=1}
  let player=AVPlayer(),layer=AVPlayerLayer(player:AVPlayer())
  let helper=NagramiXAVPlayerPictureInPicture(player:player,layer:layer)
  let system=AVPictureInPictureController.last!
  check(system.layer === layer,"AVKit uses the original player layer")
  let owner=UUID(),other=UUID()
  helper.setBackground(id:owner,active:true)
  check(player.audiovisualBackgroundPlaybackPolicy == .continuesIfPossible,"background owner enables AVPlayer background policy")
  helper.setBackground(id:other,active:true);helper.setBackground(id:owner,active:false)
  check(player.audiovisualBackgroundPlaybackPolicy == .continuesIfPossible,"one owner cannot revoke another background session")
  helper.setBackground(id:other,active:false)
  check(player.audiovisualBackgroundPlaybackPolicy == .automatic,"last background owner releases policy")
  system.isPictureInPicturePossible=false;check(!helper.begin(),"not-ready AVKit does not start")
  system.isPictureInPicturePossible=true;check(helper.begin(),"AVKit starts")
  check(!helper.begin() && system.starts==1,"repeated AVKit tap creates one request")
  system.isPictureInPictureActive=true;helper.pictureInPictureControllerDidStartPictureInPicture(system)
  check(helper.active.value,"actual AVKit callback publishes active")
  var restored=false
  helper.restore={callback in restored=true;callback(true)}
  var acknowledged=false
  helper.pictureInPictureController(system,restoreUserInterfaceForPictureInPictureStopWithCompletionHandler:{acknowledged=$0})
  check(restored && acknowledged,"AVKit restores through original owner")
  system.isPictureInPictureActive=false;helper.pictureInPictureControllerDidStopPictureInPicture(system)
  check(!helper.active.value,"AVKit actual stop releases state")
  check(helper.begin(),"AVKit retry after stop")
  helper.stop();system.isPictureInPictureActive=true;helper.pictureInPictureControllerDidStartPictureInPicture(system)
  check(system.stops>0 && !helper.active.value,"late AVKit start is stopped after cancellation")
  system.isPictureInPictureActive=false
  let controller=WKUserContentController(),view=WKWebView()
  let web=NagramiXWebSystemPictureInPicture(controller:controller);web.webView=view
  check(controller.scripts.count==1,"one script for the existing web view")
  check(web.begin() && !web.begin(),"one pending WebKit request")
  let payload=view.calls.last!.0,request=payload["request"] as! String,token=payload["token"] as! String
  let small=WKFrameInfo(1),large=WKFrameInfo(2)
  func message(_ kind:String,_ id:String,_ frame:WKFrameInfo,_ playing:Bool=false,_ area:Double=1,_ active:Bool=false,_ req:String?=nil) {
   web.userContentController(controller,didReceive:WKScriptMessage(body:["token":token,"kind":kind,"frameKey":id,"request":req ?? request,"video":"0","playing":playing,"area":area,"active":active],frameInfo:frame))
  }
  message("candidate","small",small,false,10000)
  message("candidate","large",large,true,100)
  DispatchQueue.main.run()
  check(view.calls.last!.1 === large && view.calls.last!.0["command"] as? String == "enter","exactly one playing frame selected")
  message("state","large",large,false,1,true,"stale")
  check(!web.active.value,"stale WebKit callbacks cannot start PiP")
  message("state","small",small,false,1,true)
  check(!web.active.value,"unselected frame cannot start PiP")
  message("state","large",large,false,1,true)
  check(web.active.value && web.isActive,"actual HTML PiP event publishes active")
  web.stop()
  check(!web.active.value && view.calls.last!.0["command"] as? String == "stop","stop targets the active source")
  check(web.begin(),"web retry after cancellation")
  web.stop();DispatchQueue.main.run()
  check(view.calls.last!.0["command"] as? String == "probe","cancelled frame probe cannot create PiP")
  for enabled in [false,true] {for foreground in [false,true] {for playing in [false,true] {for pip in [false,true] {
   NagramiXTabSettings.backgroundVideoPlaybackEnabled=enabled
   UIApplication.shared.applicationState=foreground ? .active:.background
   let policy=WebPolicyBoundary();policy.nagramiXInForeground=foreground;policy.nagramiXPlaybackRequested=playing;policy.playerNode.nagramiXIsSystemPiPActive=pip
   if playing{policy.nagramiXBackgroundOwners.insert(UUID())}
   policy.nagramiXUpdateManagedPlayback()
   let background=pip || (enabled && playing)
   check(policy.playerNode.background==background,"web background policy reaches the live frame bridge")
   check(policy.nagramiXHasManagedAudio == (background || (foreground && playing)),"managed audio follows settings, PiP and playback")
   check(policy.playerNode.pauses == ((!foreground && !background) ? 1:0),"background OFF pauses ordinary web playback")
   policy.nagramiXUpdateManagedPlayback()
   check(policy.audioSessionManager.pushes<=1,"repeated status updates do not duplicate audio ownership")
  }}}}
  for background in [false,true] {for pip in [false,true] {for owner in [false,true] {
   NagramiXTabSettings.backgroundVideoPlaybackEnabled=background
   let media=MediaPolicyBoundary();media.nagramiXVideoNowPlayingRegistry.pip=pip
   if owner{media.nagramiXBackgroundVideoOwners.insert(UUID())}
   media.nagramiXUpdateBackgroundVideoState()
   check(media.nagramiXBackgroundVideoPlaying.value == (pip || (background && owner)),"global manager keeps system PiP audio independently of background checkbox")
  }}}
  UIApplication.shared.applicationState = .active
  print("system web PiP production checks: \(checks)")
 }
}
'''
