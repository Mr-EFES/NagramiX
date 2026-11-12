"""Выполнить реальный all-frame JS через Node vm с явным DOM/video adapter."""
import json,subprocess
from pathlib import Path
from system_web_picture_in_picture_runtime import script


def check(source,folder):
 code=HARNESS.replace('__SOURCE_JSON__',json.dumps(script(source)))
 path=folder/'system-web-dom.cjs';path.write_text(code)
 p=subprocess.run(['node',str(path)],capture_output=True,text=True,timeout=30)
 assert p.returncode==0,p.stdout+p.stderr
 return {'status':'passed','output':p.stdout.strip(),'boundary':'Actual injected JavaScript in Node vm; explicit DOM/frame/video events, no real iOS WebKit or media pixels'}

HARNESS=r'''
const vm = require('node:vm');
const code = __SOURCE_JSON__;
let checks=0;
function check(value,why){if(!value)throw new Error(why);checks++;}
function fixture() {
 const messages=[],jobs=[],relays=[];
 class Video {
  constructor(){this.readyState=4;this.paused=false;this.ended=false;this.disabled=true;this.disablePictureInPicture=true;this.attrs=new Set(['disablepictureinpicture']);this.events=[];this.webkitPresentationMode='inline';this.sets=[];this.fails=false;}
  getBoundingClientRect(){return {width:640,height:360};}
  hasAttribute(key){return this.attrs.has(key);}
  setAttribute(key,value){this.attrs.add(key);}
  removeAttribute(key){this.attrs.delete(key);}
  addEventListener(event,listener){this.events.push(listener);}
  webkitSetPresentationMode(mode){if(this.fails && mode==='picture-in-picture')throw Error('not available');this.webkitPresentationMode=mode;this.sets.push(mode);for(const listener of this.events)listener();}
 }
 const video=new Video();
 class Document {get hidden(){return true}get visibilityState(){return 'hidden'}querySelectorAll(){return [video]}}
 const document=new Document();
 const window={frames:[{postMessage:(data)=>relays.push(data)}],addEventListener(){},webkit:{messageHandlers:{nagramiXSystemPiP:{postMessage:data=>messages.push(data)}}}};
 const context=vm.createContext({window,document,Document,Date,Math,setTimeout:job=>jobs.push(job)});
 vm.runInContext(code,context);
 const frameKey=messages[0].frameKey;
 const dispatch=data=>window.nagramiXNativePiPDispatch(Object.assign({token:'__TOKEN__',frameKey},data));
 const flush=()=>{let limit=100;while(jobs.length && --limit)jobs.shift()();check(limit>0,'events settle without a replay loop');};
 return {video,document,window,messages,relays,dispatch,flush,frameKey};
}
{
 const f=fixture();check(f.messages[0].kind==='ready','all-frame ready handshake');
 f.dispatch({command:'background',enabled:true});check(!f.document.hidden && f.document.visibilityState==='visible','background owner preserves page playback visibility');
 check(f.relays.length===1,'background policy reaches iframe descendants');
 f.dispatch({command:'background',enabled:false});check(f.document.hidden && f.document.visibilityState==='hidden','background OFF restores native visibility');
 f.dispatch({command:'probe',request:'A'});check(f.messages.at(-1).kind==='candidate','HTML video candidate discovery');
 check(f.video.disablePictureInPicture,'probing leaves site flags intact');
 check(!f.dispatch({command:'enter',request:'A',video:'0',token:'wrong'}),'wrong token rejected');
 check(!f.dispatch({command:'enter',request:'A',video:'0',frameKey:'wrong'}),'unselected frame rejected');
 check(f.dispatch({command:'enter',request:'A',video:'0'}),'selected video enters native presentation mode');
 f.flush();check(f.messages.at(-1).active===true,'actual presentation event reports active');
 check(f.video.webkitPresentationMode==='picture-in-picture' && !f.video.disablePictureInPicture,'system WebKit mode with original video');
 check(!f.dispatch({command:'enter',request:'A',video:'0'}),'duplicate entry rejected');
 f.dispatch({command:'stop',request:'A'});f.flush();
 check(f.video.webkitPresentationMode==='inline' && f.video.disablePictureInPicture && f.video.hasAttribute('disablepictureinpicture'),'cancel restores original video flags');
 check(f.messages.at(-1).restore===false,'programmatic cancellation does not request restore');
 check(!f.dispatch({command:'enter',request:'A',video:'0'}),'late enter after cancellation rejected');
 for(let i=0;i<30;i++) {
  const request='repeat'+i;f.dispatch({command:'probe',request});f.dispatch({command:'enter',request,video:'0'});f.flush();
  f.dispatch({command:'stop',request});f.flush();
 }
 check(f.video.events.length===1,'replay does not accumulate listeners');
}
for(const paused of [false,true]) {
 const f=fixture();f.dispatch({command:'probe',request:'B'});f.dispatch({command:'enter',request:'B',video:'0'});f.flush();
 f.video.paused=paused;f.video.webkitPresentationMode='inline';for(const event of f.video.events)event();f.flush();
 check(f.messages.at(-1).active===false && f.messages.at(-1).restore===!paused,'native return continues and native close releases source');
}
{
 const f=fixture();f.dispatch({command:'probe',request:'cancel-before-enter'});f.dispatch({command:'stop',request:'cancel-before-enter'});
 check(!f.dispatch({command:'enter',request:'cancel-before-enter',video:'0'}),'cancel can precede frame evaluation');
 f.dispatch({command:'probe',request:'new'});
 check(!f.dispatch({command:'enter',request:'cancel-before-enter',video:'0'}),'new probe invalidates previous request');
 f.video.fails=true;check(!f.dispatch({command:'enter',request:'new',video:'0'}),'unsupported native mode fails without another player');
 check(f.video.disablePictureInPicture,'failure restores site flag');
}
console.log('system web DOM production checks: '+checks);
'''
