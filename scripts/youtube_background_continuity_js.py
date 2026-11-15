"""Run the production document-start script with explicit DOM/media boundaries."""
import json,subprocess
from video_audio_continuity_js import harness as previous_harness
from system_web_picture_in_picture_runtime import script


def harness():
    code=previous_harness().split("for (const nativeHidden",1)[0]
    code=code.replace("ownDescriptor=false}","ownDescriptor=false,seedYouTube=true,seedGuard=true}")
    code=code.replace("this.events=[];", "this.events=[];this.mediaListeners=new Map();")
    code=code.replace("pause(){this.paused=true;this.pauses=(this.pauses||0)+1}","pause(){this.paused=true;this.pauses=(this.pauses||0)+1;this.media('pause')}\n  media(name){for(const job of this.mediaListeners.get(name)||[])job({isTrusted:true})}")
    code=code.replace("if(type==='webkitpresentationmodechanged')this.events.push(listener)","if(type==='webkitpresentationmodechanged')this.events.push(listener);else{const list=this.mediaListeners.get(type)||[];list.push(listener);this.mediaListeners.set(type,list)}")
    code=code.replace("HTMLVideoElement:Video,", "HTMLVideoElement:Video,HTMLMediaElement:Video,")
    code=code.replace("vm.runInContext(source,context);", "const nativePause=Video.prototype.pause;\n vm.runInContext(source.replace('__YOUTUBE__',String(seedYouTube)).replace('__PAUSE_GUARD__',String(seedGuard)),context);\n const cachedPause=Video.prototype.pause;")
    code=code.replace("return {messages,jobs,video,", "return {nativePause,cachedPause,prototype:Video.prototype,messages,jobs,video,")
    return code+SCENARIOS


def check(source,folder):
    folder.mkdir(parents=True,exist_ok=True)
    value=script(source)
    path=folder/'youtube-background-dom.cjs'
    def run(body):
        path.write_text(harness().replace('__SOURCE_JSON__',json.dumps(body)))
        return subprocess.run(['node',str(path)],capture_output=True,text=True,timeout=30)
    result=run(value)
    assert result.returncode==0,result.stdout+result.stderr
    negatives=[]
    for name,old,new,why in [
      ('late-prototype-wrap','    refreshOverrides();\n    send({ kind:', '    void 0;\n    send({ kind:', 'document-start wrapper exists before page script caches pause'),
      ('background-depends-on-pip','backgroundProtection && background && playbackAllowed','backgroundProtection && override && background && playbackAllowed','early cached prototype pause is guarded independently of PiP'),
      ('ignore-user-pause','if (!event.isTrusted) return;','return;','trusted input keeps manual pause'),
      ('ignore-playback-off','playbackAllowed = data.enabled === true;','playbackAllowed = true;','native app pause disables guard'),
      ('ignore-application-inactive','nativeHidden || applicationInactive || active(video)','nativeHidden || active(video)','lock protection is armed before WebKit hidden lifecycle'),
      ('no-media-events',"video.addEventListener(name, () => {", "video.addEventListener('unused', () => {", 'actual native pause is reported without resume'),
    ]:
        assert value.count(old)==1,(name,value.count(old))
        test=run(value.replace(old,new,1))
        assert test.returncode and why in test.stderr,(name,test.stdout+test.stderr)
        negatives.append(name)
    return {'status':'passed','output':result.stdout.strip(),'semantic_negatives_rejected':negatives,
      'boundary':'Actual injected script in Node vm; explicit DOM/events/HTML media adapters, no live WebKit/YouTube/iPhone execution.'}


SCENARIOS=r"""
const policy=(f,{pip=false,bg=true,guard=true,youtube=true}={})=>{f.dispatch({command:'policy',youtube,enabled:pip,backgroundEnabled:bg,pauseGuardEnabled:guard});f.dispatch({command:'background',enabled:bg});f.flush()};
for(const pip of [false,true]) {
 const f=fixture();policy(f,{pip});
 check(f.cachedPause!==f.nativePause,'document-start wrapper exists before page script caches pause');
 for(let i=0;i<120;i++){f.cachedPause.call(f.video);check(!f.video.paused,'early cached prototype pause is guarded independently of PiP')}
 check(f.video.currentTime===37 && f.video.plays===0 && f.video.seeks===0,'no restart seek extraction or replay polling');
 check(f.document.hasFocus() && !f.document.hidden,'background keeps visibility for existing playing source');
 if(!pip)check(f.video.disablePictureInPicture && f.frame.getAttribute('allow').includes("'none'"),'background alone does not alter PiP settings');
 f.dispatch({command:'playback',enabled:false});f.cachedPause.call(f.video);
 check(f.video.paused,'native app pause disables guard');
 f.video.paused=false;f.dispatch({command:'playback',enabled:true});f.emit('window','click',true);f.cachedPause.call(f.video);
 check(f.video.paused,'trusted input keeps manual pause');f.flush();
 f.video.paused=false;f.dispatch({command:'playback',enabled:true});f.emit('window','click',false);f.cachedPause.call(f.video);
 check(!f.video.paused,'synthetic input cannot impersonate explicit pause');
 f.nativePause.call(f.video);f.flush();
 check(f.messages.some(m=>m.kind==='media' && m.reason==='pause' && !m.playing && !m.allowed),'actual native pause is reported without resume');
 check(f.video.paused && f.video.plays===0,'native pause and interruption never auto-resume');
 f.video.paused=false;f.video.media('playing');f.cachedPause.call(f.video);
 check(f.video.paused,'site playing event cannot re-enable cancelled background protection');
}
{
 const f=fixture();f.document.nativeHidden=false;policy(f);
 f.cachedPause.call(f.video);check(f.video.paused,'foreground inline site pause remains native');
 f.video.paused=false;f.dispatch({command:'playback',enabled:true});f.dispatch({command:'application',active:false});
 f.cachedPause.call(f.video);check(!f.video.paused,'lock protection is armed before WebKit hidden lifecycle');
 f.dispatch({command:'application',active:true});f.cachedPause.call(f.video);check(f.video.paused,'return foreground restores normal inline pause');
}
{
 const f=fixture();policy(f);const second=f.appendVideo();f.flush();
 f.cachedPause.call(second);check(second.paused,'unselected media is never protected');
 check(!f.messages.some(m=>m.reason==='pause'),'secondary source pause cannot stop selected playback');
 f.removeVideo(f.video);second.paused=false;second.media('playing');f.flush();
 f.cachedPause.call(second);check(!second.paused,'DOM replacement source inherits authorized lease');
 f.dispatch({command:'policy',youtube:true,enabled:false,backgroundEnabled:false,pauseGuardEnabled:false});f.dispatch({command:'background',enabled:false});f.flush();
 check(f.prototype.pause===f.nativePause,'OFF restores original prototype descriptor');
 f.cachedPause.call(second);check(second.paused,'cached wrapper forwards native pause after OFF');
}
for(const youtube of [false,true])for(const bg of [false,true]) {
 const f=fixture({seedYouTube:youtube,seedGuard:bg});policy(f,{youtube,bg,guard:bg});
 f.video.pause();check(f.video.paused===!(youtube&&bg),'only enabled YouTube background owns pause policy');
}
{
 const f=fixture();policy(f);let stopped=0;f.listen('window','visibilitychange',()=>{stopped++;f.video.pause()});
 check(f.emit('window','visibilitychange').stopped && stopped===0,'lifecycle handler cannot suspend owned playing source');
 f.nativePause.call(f.video);check(!f.emit('window','visibilitychange').stopped,'paused source preserves native lifecycle');
}
{
 const f=fixture();policy(f);f.removeVideo(f.video);f.flush();
 check(f.messages.some(m=>m.kind==='media' && m.ended && !m.playing && m.reason==='detached'),'removed source releases stale playing ownership');
 check(f.video.plays===0,'removed source is never restarted');
}
console.log('YouTube background DOM checks: '+checks);
"""
