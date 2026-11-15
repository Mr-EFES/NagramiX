@main struct Tests {
 static func main(){
  var count=0
  func check(_ value:@autoclosure()->Bool,_ why:String){if !value(){FileHandle.standardError.write(Data(("YouTube background: "+why+"\n").utf8));exit(96)};count+=1}
  func receive(_ player:Player,_ values:[String:Any],token valid:Bool=true){
   player.nagramiXSystemPiP.setApplicationActive(false)
   let token=player.view.calls.last!.0["token"] as! String
   var body=values;body["token"]=valid ? token:"other-document"
   player.nagramiXSystemPiP.userContentController(player.controller,didReceive:WKScriptMessage(body:body,frameInfo:WKFrameInfo(1)))
  }
  func media(_ player:Player,playing:Bool,reason:String="playing",frame:String="source",area:Double=230400,ended:Bool=false,allowed:Bool=true){
   receive(player,["kind":"media","frameKey":frame,"playing":playing,"ended":ended,"area":area,"reason":reason,"allowed":allowed])
  }
  for pip in [false,true] {for bg in [false,true] {
   let player=Player(pip:pip,bg:bg),helper=player.nagramiXSystemPiP
   check(player.controller.scripts.count==1,"one script uses the existing WebKit player")
   let script=player.controller.scripts[0].source
   check(!script.contains("__YOUTUBE__") && !script.contains("__PAUSE_GUARD__"),"policy is seeded before document-start")
   helper.setBackground(bg);helper.setApplicationActive(false)
   receive(player,["kind":"ready","frameKey":"source"])
   let calls=player.view.calls.map{$0.0}
   let policy=calls.last{$0["command"] as? String == "policy"}!
   check(policy["backgroundEnabled"] as? Bool == bg,"background lease is independent of PiP preference")
   check(policy["enabled"] as? Bool == (pip && bg),"PiP hints keep their own switch")
   check(policy["pauseGuardEnabled"] as? Bool == (pip || bg),"early pause interception respects both preferences")
  }}
  do {
   let web=WebPolicy();web.play();let player=web.playerNode
   check(player.impl.plays==0 && web.nagramiXHasManagedAudio,"explicit play waits for real audio lease")
   NotificationCenter.default.post(name:UIApplication.willResignActiveNotification,object:nil)
   check(web.nagramiXInForeground,"inactive does not prematurely pause foreground player")
   NotificationCenter.default.post(name:UIApplication.didEnterBackgroundNotification,object:nil)
   check(web.nagramiXHasManagedAudio,"initial play survives background before gallery owner registration")
   web.audioSessionManager.acquire();check(player.impl.plays==1,"one play follows audio activation in background")
   media(player,playing:true);player.nagramiXPublishPlaybackStatus(sample(.playing))
   let id=UUID();web.setNagramiXBackgroundPlayback(id:id,active:true)
   for _ in 0..<120 {player.nagramiXPublishPlaybackStatus(sample(.paused))}
   check(web.nagramiXPlaybackRequested && web.nagramiXHasManagedAudio,"stale iframe pause cannot drop a truly playing background source")
   check(player.statusValue.value==sample(.playing),"metadata timestamps rate seek ID geometry and sound are preserved")
   player.nagramiXPublishPlaybackStatus(sample(.buffering(initial:false,whilePlaying:false,progress:0.4,display:true)))
   check(player.statusValue.value.status == .buffering(initial:false,whilePlaying:true,progress:0.4,display:true),"stale buffering preserves actual playing ownership")
   check(player.impl.plays==1 && web.audioSessionManager.pushes==1,"status reconciliation never replays or reacquires repeatedly")
   media(player,playing:false,reason:"pause")
   check(!web.nagramiXPlaybackRequested && !web.nagramiXAwaitingBackgroundOwner,"actual native pause cancels the handoff")
   player.nagramiXPublishPlaybackStatus(sample(.playing))
   check(player.statusValue.value.status == .paused,"stale iframe playing cannot undo a real pause")
   web.setNagramiXBackgroundPlayback(id:id,active:false)
   check(!web.nagramiXHasManagedAudio && player.impl.plays==1,"pause releases ownership without replay")
   NotificationCenter.default.post(name:UIApplication.didBecomeActiveNotification,object:nil)
   web.play();web.audioSessionManager.acquire(1);check(player.impl.plays==2,"next explicit user play recovers normally")
   media(player,playing:true);player.nagramiXPublishPlaybackStatus(sample(.playing));web.setNagramiXBackgroundPlayback(id:id,active:true)
   web.audioSessionManager.interrupt(1)
   check(web.nagramiXAudioSuspended && !web.nagramiXAwaitingBackgroundOwner,"audio interruption cancels startup and guard")
   for _ in 0..<120 {player.nagramiXPublishPlaybackStatus(sample(.playing))}
   check(player.impl.plays==2 && web.audioSessionManager.pushes==2,"late status cannot fight an audio interruption")
  }
  for keepOwner in [false,true] {
   let web=WebPolicy();web.play();web.audioSessionManager.acquire()
   let id=UUID();if keepOwner{web.setNagramiXBackgroundPlayback(id:id,active:true)}
   web.nagramiXInForeground=false;DispatchQueue.main.run()
   check(web.nagramiXHasManagedAudio == keepOwner,"startup handoff expires unless transferred to gallery owner")
  }
  do {
   let web=WebPolicy();web.play();web.pause();web.play()
   web.audioSessionManager.acquire(0);check(web.playerNode.impl.plays==0,"stale acquisition cannot start newer request")
   web.audioSessionManager.acquire(1);check(web.playerNode.impl.plays==1,"current acquisition starts exactly once")
   web.pause();DispatchQueue.main.run();check(!web.nagramiXAwaitingBackgroundOwner && web.playerNode.impl.plays==1,"cancelled deadline cannot resurrect playback")
  }
  do {
   let player=Player();let helper=player.nagramiXSystemPiP;helper.setBackground(true)
   media(player,playing:true);player.nagramiXPublishPlaybackStatus(sample(.paused))
   check(player.statusValue.value.status == .playing,"actual frame playing corrects background API pause")
   receive(player,["kind":"media","frameKey":"source","playing":false,"ended":false,"area":230400.0,"reason":"pause"],token:false)
   check(helper.actualMediaPlaying==true,"foreign token cannot change playback")
   media(player,playing:false,reason:"pause",frame:"secondary",area:1)
   check(helper.actualMediaPlaying==true,"secondary paused frame cannot stop selected source")
   media(player,playing:true,frame:"secondary",area:1)
   check(helper.actualMediaPlaying==true,"smaller secondary video cannot take playing ownership")
   helper.stop();check(helper.actualMediaPlaying==true,"PiP stop does not erase live background observation")
   helper.resetMediaObservation();check(helper.actualMediaPlaying==nil,"real navigation resets old document observation")
   media(player,playing:true,area:Double.nan);check(helper.actualMediaPlaying==nil,"invalid geometry is rejected")
   media(player,playing:false,reason:"ended",ended:true);check(!helper.playbackAllowed,"end does not trigger replay")
  }
  for youtube in [false,true] {
   NagramiXTabSettings.backgroundVideoPlaybackEnabled=false
   let web=WebPolicy(youtube:youtube);web.play();web.audioSessionManager.acquire()
   web.nagramiXInForeground=false;web.nagramiXUpdateManagedPlayback()
   check(!web.nagramiXHasManagedAudio && !web.nagramiXAwaitingBackgroundOwner,"saved background OFF stays effective")
   NagramiXTabSettings.backgroundVideoPlaybackEnabled=true
   let preload=WebPolicy(youtube:youtube);preload.status(sample(.paused))
   check(preload.audioSessionManager.pushes==0,"preload never owns an audio session")
   check(preload.nagramiXAwaitingBackgroundOwner==false,"handoff belongs only to explicit play")
   let ordinary=WebPolicy(youtube:youtube);ordinary.play();ordinary.audioSessionManager.acquire()
   check(ordinary.nagramiXAwaitingBackgroundOwner == youtube,"new startup handoff is scoped to YouTube")
  }
  print("YouTube background production checks: \(count)")
 }
}
