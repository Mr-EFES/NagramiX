"""Действующий WK bridge и реальные setting/observer hooks без дублирования алгоритмов."""
from validate_quick_format import block
from system_web_picture_in_picture_runtime import WEB,BOUNDARY as LEGACY_BOUNDARY
SETTINGS='submodules/NagramiXCore/Sources/NagramiXTabSettings.swift'


def bridge_fixture(source):
    bridge=block((source/WEB).read_text(),'private final class NagramiXWebSystemPictureInPicture:')
    old='struct WKUserScript {enum Time {case atDocumentEnd};let source:String;init(source:String,injectionTime:Time,forMainFrameOnly:Bool){self.source=source}}'
    new='struct WKUserScript {enum Time:Equatable {case atDocumentEnd,atDocumentStart};let source:String;let injectionTime:Time;let forMainFrameOnly:Bool;init(source:String,injectionTime:Time,forMainFrameOnly:Bool){self.source=source;self.injectionTime=injectionTime;self.forMainFrameOnly=forMainFrameOnly}}'
    assert LEGACY_BOUNDARY.count(old)==1
    return LEGACY_BOUNDARY.replace(old,new,1)+bridge+'\n'+BRIDGE_TESTS


def hook_fixture(source):
    text=(source/WEB).read_text();settings=(source/SETTINGS).read_text()
    call=next(x.strip() for x in text.splitlines() if 'self.nagramiXSystemPiP.setYouTubeOverride(self.impl' in x)
    observer=block(text,'        self.nagramiXPolicyObserver = NotificationCenter.default.addObserver(')
    cleanup=next(x.strip() for x in text.splitlines() if 'if let observer = self.nagramiXPolicyObserver' in x)
    getter=block(settings,'    public static var videoPiPSwipeEnabled:').replace('public ','')
    notification=next(x.strip().replace('public ','') for x in settings.splitlines() if 'changedNotification = Notification.Name("NagramiXSettingsChanged")' in x)
    key=next(x.strip() for x in settings.splitlines() if 'static let videoPiPSwipe =' in x)
    return '''import Foundation
struct NagramiXTabSettings {
 enum Key {'''+key+'''}
'''+notification+'\n'+getter+'''
}
final class YoutubeEmbedImplementation {}
final class OtherEmbed {}
final class BridgeBoundary {var calls:[(Bool,Bool)]=[];func setYouTubeOverride(_ youtube:Bool,enabled:Bool){calls.append((youtube,enabled))}}
final class ActualSettingsHook {
 let impl:Any
 let nagramiXSystemPiP:BridgeBoundary
 var nagramiXPolicyObserver:NSObjectProtocol?
 init(_ impl:Any,_ bridge:BridgeBoundary){self.impl=impl;self.nagramiXSystemPiP=bridge
'''+call+'\n'+observer+'''
 }
 deinit {'''+cleanup+'''}
}
'''+HOOK_TESTS


def bridge_negatives(code):
    variants=[('ignore-pip-setting','self.overrideYouTube && (self.background || self.keepsPlaybackActive)','self.youtube && (self.background || self.keepsPlaybackActive)','pending native request grants only enabled YouTube scope'),('wrong-site-scope','self.overrideYouTube = youtube && enabled','self.overrideYouTube = enabled','generic video does not receive YouTube override'),('late-script','injectionTime: .atDocumentStart','injectionTime: .atDocumentEnd','policy installed before site listeners'),('no-ready-policy','self.updatePolicy(frame: message.frameInfo)','_ = message.frameInfo','new frame receives policy before background'),('no-stop-release','self.active.set(false)\n        self.updatePolicy()','self.active.set(false)','stopping releases one-shot override')]
    for name,old,new,why in variants:
        assert code.count(old)==1,(name,code.count(old))
        yield name,code.replace(old,new,1),why


def hook_negatives(code):
    old='self.impl is YoutubeEmbedImplementation';assert code.count(old)==2
    yield 'other-site-enabled',code.replace(old,'true'),'non-YouTube node stays outside override scope'
    old='as? Bool ?? true';assert code.count(old)==1
    yield 'fresh-off',code.replace(old,'as? Bool ?? false',1),'fresh PiP default stays enabled'

BRIDGE_TESTS=r'''
@main struct YouTubeBridgeTests {
 static func main(){
  var checks=0
  func check(_ v:@autoclosure()->Bool,_ why:String){if !v(){FileHandle.standardError.write(Data(("YouTube bridge regression: "+why+"\n").utf8));exit(96)};checks+=1}
  for youtube in [false,true] {for enabled in [false,true] {for background in [false,true] {
   let controller=WKUserContentController(),view=WKWebView()
   let bridge=NagramiXWebSystemPictureInPicture(controller:controller);bridge.webView=view
   check(controller.scripts.count==1 && controller.scripts[0].injectionTime == .atDocumentStart && !controller.scripts[0].forMainFrameOnly,"policy installed before site listeners")
   bridge.setYouTubeOverride(youtube,enabled:enabled);bridge.setBackground(background)
   func policy()->[String:Any]? {view.calls.last(where:{$0.0["command"] as? String == "policy"})?.0}
   if !enabled {check((policy()?["enabled"] as? Bool ?? false)==false,"saved OFF does not grant override")}
   if !youtube {check((policy()?["enabled"] as? Bool ?? false)==false,"generic video does not receive YouTube override")}
   if youtube && enabled {check(policy()?["enabled"] as? Bool == background,"idle policy requires a playback owner")}
   let count=view.calls.count;bridge.setYouTubeOverride(youtube,enabled:enabled);bridge.setBackground(background)
   check(count==view.calls.count,"unchanged preferences do not poll JS")
   check(bridge.begin() && !bridge.begin(),"one native probe per request")
   let probe=view.calls.last!.0;let request=probe["request"] as! String;let token=probe["token"] as! String
   check(policy()?["enabled"] as? Bool == (youtube && enabled),"pending native request grants only enabled YouTube scope")
   let frame=WKFrameInfo(1)
   func message(_ kind:String,request value:String=request,key:String="one",active:Bool=false) {
    bridge.userContentController(controller,didReceive:WKScriptMessage(body:["kind":kind,"token":token,"request":value,"frameKey":key,"video":"0","playing":true,"area":Double(100),"active":active],frameInfo:frame))
   }
   let beforeReady=view.calls.count;message("ready")
   check(view.calls.count==beforeReady+2 && view.calls[beforeReady].0["command"] as? String == "policy" && view.calls[beforeReady].1 === frame && view.calls[beforeReady+1].0["command"] as? String == "background","new frame receives policy before background")
   message("candidate");DispatchQueue.main.run()
   check(view.calls.last!.0["command"] as? String == "enter" && view.calls.last!.1 === frame,"same selected frame owns system entry")
   message("state",request:"stale",active:true);check(!bridge.isActive,"stale presentation state rejected")
   message("state",active:true);check(bridge.isActive,"actual native state required for active")
   bridge.setYouTubeOverride(youtube,enabled:false)
   check(policy()?["enabled"] as? Bool == false,"live OFF revokes override during PiP")
   bridge.stop();check(!bridge.keepsPlaybackActive,"stop releases original native ownership")
   check(view.calls.contains(where:{$0.0["command"] as? String == "stop" && $0.1 === frame}),"stop is sent to selected frame")
   bridge.setYouTubeOverride(youtube,enabled:enabled);bridge.setBackground(false)
   _ = bridge.begin();let second=view.calls.last!.0["request"] as! String
   bridge.stop()
   check(policy()?["enabled"] as? Bool == false,"stopping releases one-shot override")
   DispatchQueue.main.run();check(!view.calls.contains(where:{$0.0["command"] as? String == "enter" && $0.0["request"] as? String == second}),"cancelled probe cannot enter later")
   _ = bridge.begin();DispatchQueue.main.run()
   check(!bridge.keepsPlaybackActive && view.calls.last!.0["enabled"] as? Bool == false,"empty probe releases its temporary policy")
   bridge.setYouTubeOverride(true,enabled:true);bridge.setBackground(true)
   bridge.setYouTubeOverride(false,enabled:true)
   check(policy()?["enabled"] as? Bool == false,"generic video does not receive YouTube override")
   bridge.setBackground(false)
  }}}
  print("YouTube bridge production checks: \(checks)")
 }
}
'''
HOOK_TESTS=r'''
@main struct YouTubeSettingTests {
 static func main(){
  var checks=0
  func check(_ v:@autoclosure()->Bool,_ why:String){if !v(){FileHandle.standardError.write(Data(("YouTube setting regression: "+why+"\n").utf8));exit(96)};checks+=1}
  let key=NagramiXTabSettings.Key.videoPiPSwipe;let defaults=UserDefaults.standard;let old=defaults.object(forKey:key)
  defer {defaults.set(old,forKey:key)}
  defaults.removeObject(forKey:key)
  let bridge=BridgeBoundary()
  var node:ActualSettingsHook?=ActualSettingsHook(YoutubeEmbedImplementation(),bridge)
  let weakBox=WeakBox(node)
  check(bridge.calls.last?.0==true && bridge.calls.last?.1==true,"fresh PiP default stays enabled")
  for enabled in [false,true,false,true] {
   defaults.set(enabled,forKey:key);NotificationCenter.default.post(name:NagramiXTabSettings.changedNotification,object:nil)
   check(bridge.calls.last?.0==true && bridge.calls.last?.1==enabled,"open player observes saved PiP setting")
   let other=BridgeBoundary();let otherNode=ActualSettingsHook(OtherEmbed(),other)
   check(other.calls.last?.0==false,"non-YouTube node stays outside override scope")
   _ = otherNode
  }
  node=nil;check(weakBox.value==nil,"settings observer does not retain player")
  let count=bridge.calls.count;NotificationCenter.default.post(name:NagramiXTabSettings.changedNotification,object:nil)
  check(bridge.calls.count==count,"released player receives no more settings callbacks")
  print("YouTube actual setting checks: \(checks)")
 }
}
final class WeakBox {weak var value:ActualSettingsHook?;init(_ value:ActualSettingsHook?){self.value=value}}
'''
