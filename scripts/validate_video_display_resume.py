#!/usr/bin/env python3
"""Исполнить реальный recovery/timer/foreground код с границей AVFoundation."""
import argparse,hashlib,importlib.util,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NAME='submodules/MediaPlayer/Sources/MediaPlayerNode.swift'
def module(stage):
 spec=importlib.util.spec_from_file_location(stage,ROOT/'ios'/f'{stage}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',required=True);a=p.parse_args()
 plan=json.loads((ROOT/'ios/video_display_resume_patches.json').read_text());before=(a.source/NAME).read_text();assert hashlib.sha256(before.encode()).hexdigest()==plan['inputs'][NAME]
 with tempfile.TemporaryDirectory() as folder:
  temp=Path(folder);native=temp/'native';path=native/NAME;path.parent.mkdir(parents=True);path.write_text(before)
  m=module('video_display_resume');m.apply_video_display_resume(native,ROOT/'ios');after=path.read_text();assert hashlib.sha256(after.encode()).hexdigest()==plan['outputs'][NAME]
  restored=after
  for n,old,new,count in reversed(plan['patches']):assert restored.count(new)==count;restored=restored.replace(new,old,count)
  assert restored==before
  guards=0
  def reject(overlay):
   nonlocal guards
   snap=path.read_bytes() if path.exists() else None
   try:m.apply_video_display_resume(native,overlay)
   except SystemExit:pass
   else:raise AssertionError('invalid mutation accepted')
   assert (path.read_bytes() if path.exists() else None)==snap;guards+=1
  reject(ROOT/'ios');path.write_text(before+'\n');reject(ROOT/'ios');path.unlink();reject(ROOT/'ios')
  overlay=temp/'overlay';overlay.mkdir()
  for kind in ['output','anchor']:
   path.write_text(before);bad=json.loads(json.dumps(plan))
   if kind=='output':bad['outputs'][NAME]='0'*64
   else:bad['patches'][-1][1]+='// drift'
   (overlay/'video_display_resume_patches.json').write_text(json.dumps(bad));reject(overlay)
  helper='    @discardableResult\n    private func nagramiXRecoverVideoDisplayIfNeeded()'+after.split('    @discardableResult\n    private func nagramiXRecoverVideoDisplayIfNeeded()',1)[1].split('    private func updateState()',1)[0]
  def timer(text):return text.split('strongSelf.timer = SwiftSignalKit.Timer( timeout: delay, repeat: true, completion: {',1)[1].split('}, queue: Queue.mainQueue())',1)[0]
  foreground=after.split('self.nagramiXDisplayRecoveryObserver = NotificationCenter.default.addObserver',1)[1].split('using: { [weak self] _ in',1)[1].split('        })',1)[0]
  assert after.index('node.nagramiXRecoverVideoDisplayIfNeeded()')<after.index('if !videoLayer.isReadyForMoreMediaData')
  assert 'NotificationCenter.default.removeObserver(observer)' in after
  assert after.count('flushAndRemoveImage()')==before.count('flushAndRemoveImage()')
  assert 'seek(' not in helper and '.play(' not in helper and '.pause(' not in helper
  swift='''import Foundation
final class Queue { static func mainQueue()->Queue { Queue() }; func isCurrent()->Bool { true } }
final class UIApplication {
 enum State { case active, inactive, background }
 static let shared=UIApplication(); var applicationState:State = .active
}
final class Layer {
 enum Status { case failed, rendering }
 var status:Status = .rendering; var requiresFlushToResumeDecoding=false
 var isReadyForMoreMediaData=true; var flushes=0
 var position=125.0; var timebase=17; var image=42
 func flush() { flushes += 1; status = .rendering; requiresFlushToResumeDecoding=false; isReadyForMoreMediaData=true }
}
final class Timer { func invalidate() {} }
final class Host {
 var videoInHierarchy=false; var canPlaybackWithoutHierarchy=false; var videoLayer:Layer?=Layer()
 var state:(Int,Bool,Int,Int)?=(17,true,0,0); var timer:Timer?=Timer(); var starts=0; var updates=0
 func startPolling() { starts += 1 }
 // AVFoundation/geometry are outside this boundary. Preserve the production requestFrames gate.
 func updateState() { updates += 1; self.nagramiXRecoverVideoDisplayIfNeeded(); if let s=state, s.1 { startPolling() } }
HELPER
 func tick() { let cb = { [weak self] in TIMER }; cb() }
 func foreground() { let cb = { [weak self] in FOREGROUND }; cb() }
}
func check(_ value:Bool,_ label:String="") { if !value { FileHandle.standardError.write(Data(label.utf8)); exit(1) } }
@main struct Test {
 static func main() {
  // Exact native timer branch: failed/not-ready after lock then Play/foreground.
  let h=Host(); h.canPlaybackWithoutHierarchy=true; let layer=h.videoLayer!
  layer.status = .failed; layer.requiresFlushToResumeDecoding=true; layer.isReadyForMoreMediaData=false
  h.tick(); check(h.starts==1 && layer.flushes==1,"failed renderer stays blocked in readiness timer")
  check(h.videoLayer === layer && layer.position==125 && layer.timebase==17 && layer.image==42)
  for _ in 0..<200 { h.tick() }; check(layer.flushes==1,"healthy renderer was flushed")
  // Pause/foreground: repair is independent of requestFrames, but never forces Play.
  let paused=Host(); paused.videoInHierarchy=true; paused.state=(17,false,0,0)
  paused.videoLayer!.requiresFlushToResumeDecoding=true
  paused.foreground(); check(paused.starts==0 && paused.videoLayer!.flushes==1)
  let nilLayer=Host(); nilLayer.videoInHierarchy=true; nilLayer.videoLayer=nil; nilLayer.tick(); nilLayer.foreground()
  for visible in [false,true] { for leased in [false,true] {
   for state in [UIApplication.State.active,.inactive,.background] {
    UIApplication.shared.applicationState=state
    for failed in [false,true] { for required in [false,true] {
     let n=Host(); n.videoInHierarchy=visible; n.canPlaybackWithoutHierarchy=leased
     n.videoLayer!.status=failed ? .failed : .rendering; n.videoLayer!.requiresFlushToResumeDecoding=required
     n.foreground()
     let should=state == .active && (visible || leased) && (failed || required)
     check(n.videoLayer!.flushes == (should ? 1:0),"recovery eligibility")
    } }
   }
  } }
  UIApplication.shared.applicationState = .active
  print("PASS: actual timer/repair/foreground; 48 eligibility states; lock pause/resume; no forced Play/seek/layer replacement")
 }
}
'''.replace('HELPER',helper).replace('FOREGROUND',foreground)
  for label,source in [('fixed',after),('baseline',before)]:
   file=temp/(label+'.swift');file.write_text(swift.replace('TIMER',timer(source)))
   for mode in [[],['-O']]:
    exe=temp/(label+('opt' if mode else 'debug'))
    subprocess.run([a.swiftc,'-parse-as-library','-module-cache-path',str(temp/'cache'),*mode,str(file),'-o',str(exe)],check=True)
    run=subprocess.run([str(exe)],capture_output=True,text=True)
    if label=='fixed':assert run.returncode==0,run.stderr;print(run.stdout.strip())
    else:assert run.returncode!=0 and 'failed renderer stays blocked' in run.stderr;print('PASS: baseline reproduces permanent readiness wait')
  path.write_text(after);subprocess.run([a.swiftc,'-frontend','-parse',str(path)],check=True)
  # Combine all three WIP stages against exactly the released source inputs.
  expected={}
  for stage in ['video_rotation_registration','crash_report_bot','video_display_resume']:
   pp=json.loads((ROOT/'ios'/f'{stage}_patches.json').read_text())
   for n,sha in pp['inputs'].items():
    out=native/n;out.parent.mkdir(parents=True,exist_ok=True);data=(a.source/n).read_bytes();assert hashlib.sha256(data).hexdigest()==sha;out.write_bytes(data)
   getattr(module(stage),'apply_'+stage)(native,ROOT/'ios');expected.update(pp['outputs'])
  for n,sha in expected.items():assert hashlib.sha256((native/n).read_bytes()).hexdigest()==sha
  print(f'PASS: {guards} fail-closed cases; inverse/native Swift parse; all three WIP stages ({len(expected)} files)')
if __name__=='__main__':main()
