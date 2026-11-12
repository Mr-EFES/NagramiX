"""Реальный WK script: повторные запреты, iframe, lifecycle и штатный PiP без replay loops."""
import json,subprocess
from system_web_picture_in_picture_runtime import script


def check(source,folder,original_script=None):
    value=original_script if original_script is not None else script(source)
    harness=HARNESS if original_script is None else HARNESS.split('// SCENARIOS',1)[0]+ORIGINAL_REGRESSION
    code=harness.replace('__SOURCE_JSON__',json.dumps(value))
    path=folder/'youtube-policy-dom.cjs';path.write_text(code)
    result=subprocess.run(['node',str(path)],capture_output=True,text=True,timeout=30)
    if original_script is not None:
        assert result.returncode!=0 and 'site can restore restriction during system PiP' in result.stderr,result.stdout+result.stderr
        return {'original_implementation':'rejected','diagnostic':'site can restore restriction during system PiP'}
    assert result.returncode==0,result.stdout+result.stderr
    mutations=[]
    for name,old,new,label in [
        ('no-observer',"if (typeof MutationObserver !== 'undefined')",'if (false)','site cannot reapply video hint while enabled'),
        ('no-lifecycle-guard',"event.stopImmediatePropagation();",'void event;','hidden lifecycle cannot pause permitted playback'),
        ('wrong-native-method',"override && typeof nativeSetMode === 'function' ? nativeSetMode : video.webkitSetPresentationMode",'video.webkitSetPresentationMode','original HTML video uses native WebKit mode'),
        ('ignore-off','override = nextOverride;','override = youtube;','OFF restores original video restriction'),
    ]:
        assert value.count(old)==1,(name,value.count(old))
        path.write_text(HARNESS.replace('__SOURCE_JSON__',json.dumps(value.replace(old,new,1))))
        r=subprocess.run(['node',str(path)],capture_output=True,text=True,timeout=30)
        assert r.returncode!=0 and label in r.stderr,(name,r.stdout+r.stderr)
        mutations.append({'name':name,'rejected':True,'diagnostic':label})
    return {'status':'passed','output':result.stdout.strip(),'semantic_mutations':mutations,'boundary':'Actual injected script in Node vm with explicit event/DOM/MutationObserver/native-video adapters. No real WebKit, YouTube network, DRM or iPhone audio scheduling tested.'}

HARNESS=r'''
const vm = require('node:vm');
const source = __SOURCE_JSON__;
let checks=0;
function check(value,why){if(!value)throw new Error(why);checks++;}
function fixture({blocked=true,hasFrame=true,siteMethod=false,ownDescriptor=false}={}) {
 const messages=[],jobs=[],relays=[],records=[],listeners=new Map();
 let observer=null;
 function emit(target,type){const event={type,stopped:false,stopImmediatePropagation(){this.stopped=true}};for(const entry of listeners.get(target+type)||[]){entry(event);if(event.stopped)break}return event;}
 function listen(target,type,handler){const key=target+type;listeners.set(key,[...(listeners.get(key)||[]),handler]);}
 function mutate(record){records.push(record);}
 class Element {
  constructor(tag){this.tag=tag;this.nodeType=1;this.isConnected=true;this.attrs=new Map();}
  hasAttribute(name){return this.attrs.has(name)}
  getAttribute(name){return this.attrs.has(name) ? this.attrs.get(name) : null}
  setAttribute(name,value){const oldValue=this.getAttribute(name);this.attrs.set(name,String(value));if(oldValue!==String(value))mutate({type:'attributes',target:this,attributeName:name,oldValue});}
  removeAttribute(name){if(!this.attrs.has(name))return;const oldValue=this.attrs.get(name);this.attrs.delete(name);mutate({type:'attributes',target:this,attributeName:name,oldValue});}
  matches(selector){return selector.split(',').includes(this.tag)}
  querySelector(){return null}
 }
 class Video extends Element {
  constructor(){super('video');this.readyState=4;this.paused=false;this.ended=false;this.events=[];this.webkitPresentationMode='inline';this.calls=[];this.fails=false;this.currentTime=37;this.plays=0;this.seeks=0;}
  get disablePictureInPicture(){return this.hasAttribute('disablepictureinpicture')}
  set disablePictureInPicture(value){if(value)this.setAttribute('disablepictureinpicture','');else this.removeAttribute('disablepictureinpicture')}
  getBoundingClientRect(){return {width:640,height:360}}
  addEventListener(type,listener){if(type==='webkitpresentationmodechanged')this.events.push(listener)}
  webkitSetPresentationMode(mode){
   if(mode==='picture-in-picture' && (this.fails || this.hasAttribute('disablepictureinpicture') || (hasFrame && !frame.getAttribute('allow').includes('picture-in-picture *'))))throw Error('native mode unavailable');
   this.webkitPresentationMode=mode;this.calls.push(mode);for(const e of this.events)e();
  }
 }
 class Frame extends Element {constructor(){super('iframe');this.attrs.set('allow',"autoplay; encrypted-media; picture-in-picture 'none'")}}
 const video=new Video(),frame=new Frame();
 if(blocked)video.attrs.set('disablepictureinpicture','site restriction');
 if(ownDescriptor)Object.defineProperty(video,'disablePictureInPicture',{configurable:true,writable:true,value:blocked});
 if(siteMethod)video.webkitSetPresentationMode=function(mode){if(mode==='picture-in-picture')throw Error('site restriction');return Video.prototype.webkitSetPresentationMode.call(this,mode)};
 const videos=[video],frames=hasFrame?[frame]:[];
 class Document {
  get hidden(){return this.nativeHidden}
  get visibilityState(){return this.nativeHidden ? 'hidden':'visible'}
  querySelectorAll(selector){return (selector==='video' ? videos:frames).filter(node=>node.isConnected)}
  addEventListener(type,handler){listen('document',type,handler)}
 }
 class MutationObserver {constructor(callback){this.callback=callback}observe(){observer=this}}
 const document=new Document();document.nativeHidden=true;
 const window={frames:[{postMessage:data=>relays.push(data)}],addEventListener(type,handler){listen('window',type,handler)},webkit:{messageHandlers:{nagramiXSystemPiP:{postMessage:data=>messages.push(data)}}}};
 const context=vm.createContext({window,document,Document,HTMLVideoElement:Video,MutationObserver,Date,Math,setTimeout:job=>jobs.push(job)});
 vm.runInContext(source,context);
 const frameKey=messages[0].frameKey;
 const dispatch=data=>window.nagramiXNativePiPDispatch(Object.assign({token:'__TOKEN__',frameKey},data));
 const flush=()=>{let n=0;while(records.length || jobs.length){if(++n>200)throw Error('policy must not create observer/replay loop');if(records.length){const batch=records.splice(0);if(observer)observer.callback(batch);}if(jobs.length)jobs.shift()();}};
 const appendVideo=()=>{const v=new Video();v.attrs.set('disablepictureinpicture','replacement restriction');videos.push(v);mutate({type:'childList',addedNodes:[v],removedNodes:[]});return v};
 const removeVideo=v=>{v.isConnected=false;mutate({type:'childList',addedNodes:[],removedNodes:[v]});};
 return {messages,jobs,video,frame,document,window,dispatch,flush,relays,frameKey,appendVideo,removeVideo,listen,emit};
}
// SCENARIOS
{
 const f=fixture();f.dispatch({command:'policy',youtube:true,enabled:true});f.flush();
 check(!f.video.disablePictureInPicture && !f.video.hasAttribute('disablepictureinpicture'),'YouTube hint is ignored throughout allowed playback');
 check(f.frame.getAttribute('allow').includes('picture-in-picture *') && f.frame.getAttribute('allow').includes('encrypted-media'),'iframe delegates PiP without losing other permissions');
 for(let i=0;i<30;i++) {
  f.video.disablePictureInPicture=true;f.video.setAttribute('disablepictureinpicture','site restriction');f.flush();
  check(!f.video.disablePictureInPicture && !f.video.hasAttribute('disablepictureinpicture'),'site cannot reapply video hint while enabled');
 }
 const replacement=f.appendVideo();f.flush();
 check(!replacement.disablePictureInPicture,'replacement video inherits playback policy');
 f.removeVideo(replacement);f.flush();check(replacement.disablePictureInPicture,'detached source restores its own policy');
 f.dispatch({command:'policy',youtube:true,enabled:false});f.flush();
 check(f.video.disablePictureInPicture && f.video.getAttribute('disablepictureinpicture')==='site restriction','OFF restores original video restriction');
 check(f.frame.getAttribute('allow')==="autoplay; encrypted-media; picture-in-picture 'none'",'OFF restores iframe policy exactly');
 check(Object.getOwnPropertyDescriptor(f.video,'disablePictureInPicture')===undefined,'OFF removes the temporary own descriptor');
 f.dispatch({command:'probe',request:'off'});
 check(!f.dispatch({command:'enter',request:'off',video:'0'}),'OFF does not bypass site video restriction');
 check(f.video.currentTime===37 && f.video.plays===0 && f.video.seeks===0,'policy never starts or seeks another playback');
}
for(const ownDescriptor of [false,true]) {
 const f=fixture({ownDescriptor});f.dispatch({command:'policy',youtube:true,enabled:true});f.flush();
 f.video.setAttribute('disablepictureinpicture','unflushed');f.video.disablePictureInPicture=false;
 f.dispatch({command:'policy',youtube:true,enabled:false});f.flush();
 check(!f.video.disablePictureInPicture && !f.video.hasAttribute('disablepictureinpicture'),'latest setter intent restores through native and own descriptors');
}
for(const ownDescriptor of [false,true]) {
 const f=fixture({siteMethod:true,ownDescriptor});
 f.dispatch({command:'policy',youtube:true,enabled:true});f.dispatch({command:'background',enabled:true});f.flush();
 f.dispatch({command:'probe',request:'native'});
 check(f.dispatch({command:'enter',request:'native',video:'0'}),'original HTML video uses native WebKit mode');f.flush();
 check(f.video.webkitPresentationMode==='picture-in-picture' && f.messages.at(-1).active===true,'actual native event confirms PiP');
 check(!f.dispatch({command:'enter',request:'native',video:'0'}),'duplicate enter rejected');
 // Disabling during PiP must not lose the original restriction on subsequent exit.
 f.dispatch({command:'policy',youtube:true,enabled:false});f.flush();
 check(f.video.disablePictureInPicture,'OFF restores original video restriction');
 f.dispatch({command:'stop',request:'native'});f.flush();
 check(f.video.disablePictureInPicture && f.video.hasAttribute('disablepictureinpicture'),'exit does not undo OFF restoration');
 check(f.video.events.length===1 && f.video.currentTime===37,'one native listener and original position retained');
 if(ownDescriptor)check(Object.getOwnPropertyDescriptor(f.video,'disablePictureInPicture').value===true,'own descriptor restored');
}
{
 const f=fixture();const nativeHidden=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(f.document),'hidden').get;
 let sitePauses=0;
 f.listen('document','visibilitychange',()=>{if(nativeHidden.call(f.document)){sitePauses++;f.video.paused=true}});
 f.listen('window','pagehide',()=>{sitePauses++;f.video.paused=true});
 f.dispatch({command:'policy',youtube:true,enabled:true});f.dispatch({command:'background',enabled:true});f.flush();
 check(f.document.hidden===false && f.document.visibilityState==='visible','playing YouTube keeps playback visibility');
 f.emit('document','visibilitychange');f.emit('window','pagehide');
 check(sitePauses===0 && !f.video.paused,'hidden lifecycle cannot pause permitted playback');
 f.document.nativeHidden=false;
 check(!f.emit('window','blur').stopped,'foreground focus changes remain native');
 f.video.paused=true;
 check(!f.emit('document','visibilitychange').stopped,'paused playback is not restarted or hidden from site');
 check(f.video.plays===0,'no force-resume loop');
 f.video.paused=false;f.document.nativeHidden=true;f.dispatch({command:'background',enabled:false});
 check(f.document.hidden===true && !f.emit('document','visibilitychange').stopped,'background OFF restores native lifecycle');
}
{
 const f=fixture();f.dispatch({command:'policy',youtube:true,enabled:true});f.flush();
 f.video.disablePictureInPicture=false;
 f.frame.setAttribute('allow',"fullscreen; picture-in-picture 'none'");
 // OFF can beat the queued mutation callback.
 f.dispatch({command:'policy',youtube:true,enabled:false});f.flush();
 check(!f.video.disablePictureInPicture,'latest property intent survives OFF');
 check(f.frame.getAttribute('allow')==="fullscreen; picture-in-picture 'none'",'pending site iframe edit survives OFF');
}
{
 const f=fixture({blocked:false,hasFrame:false});f.dispatch({command:'policy',youtube:true,enabled:false});
 f.dispatch({command:'probe',request:'normal'});check(f.dispatch({command:'enter',request:'normal',video:'0'}),'unrestricted YouTube retains normal native path');f.flush();
 f.dispatch({command:'stop',request:'normal'});f.flush();check(!f.video.disablePictureInPicture,'unrestricted hint stays unchanged');
}
{
 const f=fixture();f.dispatch({command:'policy',youtube:true,enabled:true});f.flush();
 f.video.fails=true;f.dispatch({command:'probe',request:'unsupported'});
 check(!f.dispatch({command:'enter',request:'unsupported',video:'0'}),'unsupported system mode fails without custom player');f.flush();
 check(f.messages.at(-1).active===false && f.video.calls.length===0,'failure does not fabricate PiP start');
 f.dispatch({command:'policy',youtube:true,enabled:false});f.flush();check(f.video.disablePictureInPicture,'failure cleanup restores site hint');
}
{
 const f=fixture({hasFrame:false});f.dispatch({command:'policy',youtube:false,enabled:true});f.flush();
 check(f.video.disablePictureInPicture,'non-YouTube policy unchanged');
 f.dispatch({command:'probe',request:'generic'});check(f.dispatch({command:'enter',request:'generic',video:'0'}),'generic embed keeps previous native button path');f.flush();
 f.dispatch({command:'stop',request:'generic'});f.flush();check(f.video.disablePictureInPicture,'generic temporary flag restored');
 check(!f.dispatch({command:'enter',request:'generic',video:'0'}),'cancelled request cannot restart');
 check(!f.dispatch({command:'policy',youtube:true,enabled:true,token:'wrong'}),'wrong token cannot grant policy');
}
console.log('YouTube playback DOM production checks: '+checks);
'''

ORIGINAL_REGRESSION=r"""
const old = fixture({hasFrame:false});
old.dispatch({command:'background',enabled:true});
old.dispatch({command:'probe',request:'original'});
check(old.dispatch({command:'enter',request:'original',video:'0'}),'original native PiP begins');old.flush();
check(old.video.webkitPresentationMode==='picture-in-picture','original native PiP actually active');
old.video.disablePictureInPicture=true;old.video.setAttribute('disablepictureinpicture','site restriction');old.flush();
check(!old.video.disablePictureInPicture && !old.video.hasAttribute('disablepictureinpicture'),'site can restore restriction during system PiP');
"""
