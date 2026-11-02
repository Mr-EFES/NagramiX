#!/usr/bin/env python3
"""Проверка отложенной регистрации AVKit, без SDK/IPA и доступа к устройству."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
NAME = 'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift'
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',required=True);a=p.parse_args()
    plan=json.loads((ROOT/'ios/video_rotation_registration_patches.json').read_text())
    spec=importlib.util.spec_from_file_location('rotation',ROOT/'ios/video_rotation_registration.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    before=(a.source/NAME).read_text()
    assert digest(a.source/NAME)==plan['inputs'][NAME]
    with tempfile.TemporaryDirectory() as folder:
        folder=Path(folder);native=folder/'native';target=native/NAME;target.parent.mkdir(parents=True);target.write_text(before)
        m.apply_video_rotation_registration(native,ROOT/'ios');after=target.read_text()
        assert digest(target)==plan['outputs'][NAME]
        for n,old,new,count in reversed(plan['patches']):
            assert after.count(new)==count
            after=after.replace(new,old,count)
        assert after==before
        after=target.read_text()
        # An ordinary status callback cannot construct even a source owner.
        status=after.split('self.statusDisposable.set((combineLatest(queue: .mainQueue(), videoNode.status, mediaFileStatus)',1)[1].split('var initialBuffering',1)[0]
        assert 'setupNativePictureInPicture()' not in status
        ctor=after.split('init(context: AccountContext, videoNode: UniversalVideoNode, hiddenMedia:',1)[1].split('    deinit {',1)[0]
        assert 'bindSourceIfNeeded()' not in ctor
        assert after.count('self.bindSourceIfNeeded()')==1 # readiness only
        assert after.count('self.setupNativePictureInPicture()')==2 # explicit button/start + swipe preparation
        # Verify fail-closed on rerun, changed input, absent input, changed output
        # and changed anchor. Every rejection must leave native bytes intact.
        guards=0
        def rejected(overlay):
            nonlocal guards
            snapshot=target.read_bytes() if target.exists() else None
            try:m.apply_video_rotation_registration(native,overlay)
            except SystemExit:pass
            else:raise AssertionError('mutation accepted')
            assert (target.read_bytes() if target.exists() else None)==snapshot
            guards+=1
        rejected(ROOT/'ios')
        target.write_text(before+'\n');rejected(ROOT/'ios')
        target.unlink();rejected(ROOT/'ios')
        overlay=folder/'overlay';overlay.mkdir()
        for kind in ['output','anchor']:
            target.write_text(before);mut=json.loads(json.dumps(plan))
            if kind=='output':mut['outputs'][NAME]='0'*64
            else:mut['patches'][-1][1]+='// invalid'
            (overlay/'video_rotation_registration_patches.json').write_text(json.dumps(mut));rejected(overlay)
        def method(text):
            return '    private func bindSourceIfNeeded() {'+text.split('    private func bindSourceIfNeeded() {',1)[1].split('    private func readiness()',1)[0]
        # Execute the ACTUAL native binding method against controlled AVKit
        # classes, with the REAL lifecycle, for both old and corrected code.
        host='''
final class Host {
    let node = UniversalVideoNode()
    let playback = NSObject()
    var sourceLayer: CALayer?
    var controller: AVPictureInPictureController?
    var possibleObservation: Observation?
    var ready = false
    lazy var lifecycle = NagramiXPiPLifecycle(now: { 0 }, valid: { true }, prepare: {},
        readiness: { [unowned self] in self.bindSourceIfNeeded(); return self.ready ? .ready : .waiting },
        nativeActive: { false }, start: {}, stop: {}, commit: { true }, restore: { $0(true) },
        release: { [unowned self] in self.controller = nil; self.sourceLayer = nil }, ended: { _ in }, changed: {})
    func probe() { self.bindSourceIfNeeded() }
METHOD
}
'''
        tests='''
func check(_ condition: @autoclosure () -> Bool, _ message: String = "") {
    if !condition() {
        FileHandle.standardError.write(Data((message + "\\n").utf8))
        exit(1)
    }
}
@main struct Test {
    static func main() {
        for sample in [true, false] {
            let h = Host()
            h.node.layer = sample ? AVSampleBufferDisplayLayer() : AVPlayerLayer()
            let initial = AVPictureInPictureController.creations
            for _ in 0..<200 { h.probe(); h.lifecycle.update() }
            precondition(AVPictureInPictureController.creations == initial, "idle/fullscreen registered AVKit")
            precondition(h.lifecycle.begin(timeout: 8, completion: { _ in }))
            precondition(AVPictureInPictureController.creations == initial + 1)
            for _ in 0..<200 { h.probe(); h.lifecycle.update() }
            precondition(AVPictureInPictureController.creations == initial + 1)
            h.node.layer = sample ? AVSampleBufferDisplayLayer() : AVPlayerLayer()
            h.lifecycle.update()
            precondition(AVPictureInPictureController.creations == initial + 2, "quality rebind failed")
            h.ready = true; h.lifecycle.update(); h.lifecycle.didStart()
            precondition(h.lifecycle.phase == .active)
            for _ in 0..<200 { h.probe() }
            precondition(AVPictureInPictureController.creations == initial + 2)
            let cancelled = Host(); cancelled.node.layer = AVSampleBufferDisplayLayer()
            precondition(cancelled.lifecycle.begin(timeout: 8, completion: { _ in }))
            cancelled.lifecycle.cancelPreparation()
            let finished = AVPictureInPictureController.creations
            for _ in 0..<200 { cancelled.probe(); cancelled.lifecycle.update() }
            precondition(AVPictureInPictureController.creations == finished, "cancelled request rebound")
        }
        print("PASS: actual native binding, 1600 repeated callbacks, native/HLS, readiness/rebinding/active/cancel")
    }
}
'''
        tests=tests.replace('precondition(', 'check(')
        boundary=(ROOT/'scripts/tests/NagramiXRotationRegistrationBoundary.swift').read_text()
        lifecycle=ROOT/'ios/Sources/GalleryUI/NagramiXPiPLifecycle.swift'
        for label,text in [('fixed',after),('baseline',before)]:
            swift=folder/(label+'.swift');swift.write_text(boundary+host.replace('METHOD',method(text))+tests)
            for mode in [[],['-O']]:
                exe=folder/(label+('opt' if mode else 'debug'))
                subprocess.run([a.swiftc,'-module-cache-path',str(folder/'module-cache'),*mode,str(lifecycle),str(swift),'-o',str(exe)],check=True)
                run=subprocess.run([str(exe)],capture_output=True,text=True)
                if label=='fixed':assert run.returncode==0,run.stderr;print(run.stdout.strip())
                else:assert run.returncode!=0 and 'idle/fullscreen registered AVKit' in run.stderr;print('PASS: baseline reproduces unwanted idle AVKit registration')
        native_swift=folder/'Native.swift';native_swift.write_text(after)
        subprocess.run([a.swiftc,'-frontend','-parse',str(native_swift)],check=True)
        print(f'PASS: {guards} fail-closed cases; exact inverse; Swift parse; canonical stages unchanged')
if __name__=='__main__':main()
