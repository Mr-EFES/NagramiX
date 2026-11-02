#!/usr/bin/env python3
"""Проверить stage гибридного PiP, actual half policy и неизменный AVKit lifecycle."""
import argparse,hashlib,importlib.util,json,subprocess,tempfile
from pathlib import Path
from validate_quick_format import block
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',required=True);a=p.parse_args()
 plan=json.loads((ROOT/'ios/hybrid_pip_patches.json').read_text());G='submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift'
 spec=importlib.util.spec_from_file_location('hybrid',ROOT/'ios/hybrid_pip.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 with tempfile.TemporaryDirectory() as folder:
  t=Path(folder);native=t/'native'
  originals={}
  for name in set(plan['inputs'])|set(plan['guards']):
   text=(a.source/name).read_text()
   if name==G:
    for n,old,new,count in json.loads((ROOT/'ios/video_rotation_registration_patches.json').read_text())['patches']:
     if n==name:assert text.count(old)==count;text=text.replace(old,new,count)
   originals[name]=text
  def seed():
   for name,text in originals.items():
    f=native/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(text)
   for name in plan['copies']:
    if (native/name).exists():(native/name).unlink()
  def snapshot():return {str(f.relative_to(native)):hashlib.sha256(f.read_bytes()).hexdigest() for f in native.rglob('*') if f.is_file()}
  failures=0
  def reject(overlay):
   nonlocal failures
   before=snapshot()
   try:m.apply_hybrid_pip(native,overlay)
   except SystemExit:pass
   else:raise AssertionError('drift accepted')
   assert before==snapshot();failures+=1
  seed();m.apply_hybrid_pip(native,ROOT/'ios')
  for name,digest in plan['outputs'].items():assert hashlib.sha256((native/name).read_bytes()).hexdigest()==digest
  g=(native/G).read_text()
  # The tested AVKit state machine, registration guard and decoder control remain intact.
  old=originals[G]
  first='private final class NagramiXSystemPiPController:'
  last='final class UniversalVideoGalleryItemNode:'
  controller=g.split(first)[1].split(last)[0]
  controller=controller.replace('    var nagramiXBackgroundSourceAllowed = false\n\n','').replace('(UIApplication.shared.applicationState == .active || self.nagramiXBackgroundSourceAllowed)','UIApplication.shared.applicationState == .active')
  assert old.split(first)[1].split(last)[0]==controller
  assert g.count('UniversalVideoNode(')==old.count('UniversalVideoNode(')
  owner=(ROOT/'ios/hybrid_pip/Owner.swift.inc').read_text()
  assert '.seek(' not in owner and '.play(' not in owner
  assert 'self.lifecycle.phase == .preparing' in g
  subprocess.run([a.swiftc,'-frontend','-parse',*[str(native/n) for n in list(plan['inputs'])+list(plan['copies'])]],check=True)
  for mode in [[],['-O']]:
   exe=t/('placement-opt' if mode else 'placement')
   subprocess.run([a.swiftc,'-module-cache-path',str(t/'cache'),*mode,str(ROOT/'ios/hybrid_pip/Placement.swift'),str(ROOT/'scripts/tests/NagramiXHybridPiPPlacementTests.swift'),'-o',str(exe)],check=True)
   subprocess.run([str(exe)],check=True)
  methods='\n'.join(block(owner,'private func '+name+'(').replace('private func','func',1) for name in ['nagramiXHybridBackground','nagramiXHybridForeground','nagramiXCloseHybrid','nagramiXFinishHybridClose'])
  gate=next(line for line in g.splitlines() if 'self.nagramiXBackgroundSourceAllowed)' in line)
  boundary=r'''import Foundation
class UIApplication {enum State:CaseIterable {case active,inactive,background};static let shared=UIApplication();var applicationState=State.active}
class ReadinessNode {class View {var window:NSObject?=NSObject()};var view=View()}
enum GateState {case invalid,ready}
class Mini {var alpha:Double=1;var removing=false}
typealias NagramiXHybridMiniNode=Mini
class NagramiXSystemPiPController {var nagramiXHasPiPRequest=true;var stops=0;func stop(){stops += 1}}
class Video {var ownsContentNode=true;var canAttachContent=true;var pauses=0;var leased=true
 func pause(){pauses += 1};func setNagramiXBackgroundPlayback(id:UUID,active:Bool){leased=active}}
class Manager {var currentPictureInPictureNode:AnyObject?;var node:Mini?;var removes=0
 func hasOverlayVideoNode(_ n:Mini)->Bool {node === n}
 func setOverlayVideoNode(_ n:Mini?){node=n;removes += 1}}
class Shared {let mediaManager=Manager()};class Context {let sharedContext=Shared()}
class Host {
 var nagramiXBackgroundSourceAllowed=false;var node=ReadinessNode()
 func readinessGate()->GateState { GATE;return .ready }
 var nagramiXHybridMini:Mini?=Mini(),nagramiXHybridRetiring:Mini?
 var nagramiXHybridClosing=false,nagramiXHybridExpandPending=false,nagramiXHybridReturning=false
 var nagramiXHybridGeneration=UUID();var nagramiXHybridLease=UUID();let context=Context();var videoNode:Video?=Video()
 var nativePictureInPictureContent:AnyObject?;var activePictureInPictureController:Int?=1,activePictureInPictureNavigationController:Int?=1
 var updates=0,expands=0,starts=0;var started=true
 func nagramiXUpdateBackgroundVideoPlayback(){updates += 1}
 func nagramiXExpandHybrid(){expands += 1}
 func nagramiXScheduleHybridBackgroundRetry(){}
 func nagramiXStartSystemPiP(requiresSwipeSetting:Bool,completion:(Bool)->Void)->Bool {precondition(!requiresSwipeSetting);starts += 1;completion(started);return true}
 METHODS
}
@main struct BridgeTest {static func main(){
 let gate=Host()
 for state in UIApplication.State.allCases {for allowed in [false,true] {
  UIApplication.shared.applicationState=state;gate.nagramiXBackgroundSourceAllowed=allowed
  precondition((gate.readinessGate() == .ready) == (state == .active || allowed))
  gate.node.view.window=nil;precondition(gate.readinessGate() == .invalid);gate.node.view.window=NSObject()
 }}
 let h=Host();let mini=h.nagramiXHybridMini!;let native=NagramiXSystemPiPController()
 h.context.sharedContext.mediaManager.node=mini;h.context.sharedContext.mediaManager.currentPictureInPictureNode=h
 h.nativePictureInPictureContent=native;native.nagramiXHasPiPRequest=false
 h.nagramiXHybridBackground();precondition(h.starts==1);native.nagramiXHasPiPRequest=true
 h.nagramiXHybridForeground();precondition(h.nagramiXHybridReturning && native.stops==1)
 h.nagramiXCloseHybrid(remove:true);precondition(h.nagramiXHybridClosing && h.nagramiXHybridRetiring === mini)
 precondition(native.stops==2 && h.context.sharedContext.mediaManager.node==nil && h.videoNode!.pauses==0)
 h.nagramiXCloseHybrid(remove:true);h.nagramiXHybridBackground();h.nagramiXHybridForeground()
 precondition(native.stops==2 && h.starts==1)
 h.nagramiXFinishHybridClose();precondition(h.nagramiXHybridRetiring==nil && h.nagramiXHybridMini==nil)
 precondition(h.videoNode!.pauses==1 && !h.videoNode!.leased && !h.videoNode!.canAttachContent)
 precondition(h.context.sharedContext.mediaManager.currentPictureInPictureNode==nil)
 let replaced=Host();let newer=NSObject();replaced.context.sharedContext.mediaManager.currentPictureInPictureNode=newer
 replaced.videoNode!.ownsContentNode=false;replaced.nagramiXCloseHybrid(remove:false)
 precondition(replaced.videoNode!.pauses==0 && replaced.context.sharedContext.mediaManager.currentPictureInPictureNode === newer)
 let rejected=Host();rejected.started=false;rejected.nagramiXHybridBackground();precondition(rejected.nagramiXHybridMini!.alpha==1)
 let paused=Host();paused.nagramiXHybridForeground();precondition(!paused.nagramiXHybridReturning && paused.videoNode!.pauses==0)
 print("PASS: actual background/foreground/close/cleanup gates, delayed stop, retired ownership; UIKit/AVKit boundaries")
}}
'''.replace('METHODS',methods).replace('GATE',gate)
  file=t/'Bridge.swift';file.write_text(boundary)
  for mode in [[],['-O']]:
   exe=t/('bridge-opt' if mode else 'bridge')
   subprocess.run([a.swiftc,'-parse-as-library','-module-cache-path',str(t/'cache'),*mode,str(file),'-o',str(exe)],check=True)
   subprocess.run([str(exe)],check=True)
  reject(ROOT/'ios')
  for name in originals:
   seed();(native/name).write_text(originals[name]+'\n');reject(ROOT/'ios')
  seed();name=next(iter(plan['copies']));(native/name).parent.mkdir(parents=True,exist_ok=True);(native/name).write_text('collision');reject(ROOT/'ios')
  overlay=t/'overlay';overlay.mkdir()
  for name in plan.get('template_guards',{}):
   f=overlay/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes((ROOT/'ios'/name).read_bytes())
  for kind in ['anchor','output']:
   seed();broken=json.loads(json.dumps(plan))
   if kind=='anchor':broken['patches'][-1][1]+='//drift'
   else:broken['outputs'][G]='0'*64
   (overlay/'hybrid_pip_patches.json').write_text(json.dumps(broken));reject(overlay)
  for name in plan.get('template_guards',{}):
   seed();(overlay/'hybrid_pip_patches.json').write_text(json.dumps(plan))
   f=overlay/name;data=f.read_bytes();f.write_bytes(data+b'\n');reject(overlay);f.write_bytes(data)
  print(f'PASS: native Swift parse, same decoder/scoped readiness, {failures} atomic fail-closed cases')
if __name__=='__main__':main()
