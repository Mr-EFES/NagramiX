"""Exercise the injected production script, including repeated site pauses."""
import json
import subprocess
from youtube_playback_policy_js import HARNESS
from system_web_picture_in_picture_runtime import script


def harness():
    value = HARNESS.split('// SCENARIOS', 1)[0]
    value = value.replace('function emit(target,type){const event={type,', 'function emit(target,type,trusted=false){const event={type,isTrusted:trusted,')
    value = value.replace('  get disablePictureInPicture()', "  pause(){this.paused=true;this.pauses=(this.pauses||0)+1}\n  get disablePictureInPicture()")
    value = value.replace('  get hidden(){', '  hasFocus(){return !this.nativeHidden}\n  get hidden(){')
    return value + SCENARIOS


def check(source, folder, original=None):
    value = original if original is not None else script(source)
    target = folder / 'video-audio-dom.cjs'
    target.write_text(harness().replace('__SOURCE_JSON__', json.dumps(value)))
    result = subprocess.run(['node', str(target)], capture_output=True, text=True, timeout=30)
    if original is not None:
        assert result.returncode and 'periodic site pause cannot suspend owned playback' in result.stderr, result.stdout + result.stderr
        return {'original54': 'rejected at repeated site pause'}
    assert result.returncode == 0, result.stdout + result.stderr
    mutants = []
    for name, old, new, diagnostic in [
        ('no-pause-guard', 'override && background && playbackAllowed && !trustedInput', 'false && background && playbackAllowed && !trustedInput', 'periodic site pause cannot suspend owned playback'),
        ('ignore-app-pause', "playbackAllowed = data.enabled === true;", 'playbackAllowed = true;', 'explicit app pause remains effective'),
        ('ignore-user-input', 'if (!event.isTrusted) return;', 'return;', 'trusted site controls can pause'),
        ('no-window-capture', 'window.addEventListener(name, lifecycle, true);', 'void name;', 'window capture shields earlier lifecycle phase'),
    ]:
        assert value.count(old) == 1, name
        target.write_text(harness().replace('__SOURCE_JSON__', json.dumps(value.replace(old, new, 1))))
        run = subprocess.run(['node', str(target)], capture_output=True, text=True, timeout=30)
        assert run.returncode and diagnostic in run.stderr, (name, run.stdout + run.stderr)
        mutants.append(name)
    return {'output': result.stdout.strip(), 'semantic_mutations_rejected': mutants, 'boundary': 'Actual injected JavaScript in Node DOM/event adapters; real YouTube, WebKit and native PiP need device checks.'}


SCENARIOS = r'''
for (const nativeHidden of [false,true]) {
 const f=fixture({blocked:true});f.document.nativeHidden=nativeHidden;
 f.dispatch({command:'policy',youtube:true,enabled:true});
 f.dispatch({command:'background',enabled:true});
 f.dispatch({command:'probe',request:'owned'});f.dispatch({command:'enter',request:'owned',video:'0'});f.flush();
 for(let tick=0;tick<120;tick++) {
  f.video.pause();
  check(!f.video.paused,'periodic site pause cannot suspend owned playback');
 }
 check(f.video.currentTime===37 && f.video.plays===0,'no seeking, source replacement or resume polling');
 check(f.document.hasFocus(),'owned playing video retains focus visibility');
 f.dispatch({command:'playback',enabled:false});f.video.pause();
 check(f.video.paused,'explicit app pause remains effective');
 f.video.paused=false;f.dispatch({command:'playback',enabled:true});
 f.emit('window','click',true);f.video.pause();
 check(f.video.paused,'trusted site controls can pause');f.flush();
 f.video.paused=false;f.emit('window','click',false);f.video.pause();
 check(!f.video.paused,'synthetic site input cannot impersonate a user pause');
 // Native PiP / audio interruption changes the media state without JS pause().
 f.video.paused=true;f.flush();
 check(f.video.paused && f.video.plays===0,'native pause or interruption is never auto-resumed');
 f.dispatch({command:'policy',youtube:true,enabled:false});f.flush();
 check(Object.getOwnPropertyDescriptor(f.video,'pause')===undefined,'OFF restores native pause descriptor');
 f.video.paused=false;f.video.pause();check(f.video.paused,'OFF obeys ordinary page pause');
}
for(const youtube of [false,true]) for(const background of [false,true]) {
 const f=fixture();f.dispatch({command:'policy',youtube,enabled:true});f.dispatch({command:'background',enabled:background});f.flush();
 f.video.pause();check(f.video.paused === !(youtube && background),'pause policy is scoped to YouTube and authorized background');
}
{
 const f=fixture();f.dispatch({command:'policy',youtube:true,enabled:true});f.dispatch({command:'background',enabled:true});f.flush();
 let pauses=0;f.listen('window','visibilitychange',()=>{pauses++;f.video.pause()});
 check(f.emit('window','visibilitychange').stopped && pauses===0,'window capture shields earlier lifecycle phase');
 f.video.paused=true;check(!f.emit('window','visibilitychange').stopped,'already paused playback keeps native lifecycle');
 f.dispatch({command:'background',enabled:false});check(f.document.hasFocus()===false,'OFF restores focus query');
}
{
 const f=fixture();const own=function(){this.paused=true};Object.defineProperty(f.video,'pause',{configurable:true,writable:true,value:own});
 f.dispatch({command:'policy',youtube:true,enabled:true});f.dispatch({command:'background',enabled:true});f.flush();
 f.video.pause();check(!f.video.paused,'own pause implementation receives same scoped policy');
 f.dispatch({command:'policy',youtube:true,enabled:false});f.flush();check(f.video.pause===own,'original own pause implementation restored');
}
console.log('video audio continuity DOM checks: '+checks);
'''
