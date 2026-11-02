#!/usr/bin/env python3
"""Проверить PiP без локальной миниатюры и задержанного rollback."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import resource
from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
GALLERY = 'submodules/GalleryUI/Sources/'
ITEM = GALLERY+'Items/UniversalVideoGalleryItem.swift'
GESTURE = GALLERY+'NagramiXPiPGestureController.swift'
VISUAL = GALLERY+'NagramiXPiPVisualHandoff.swift'

def sha(data): return hashlib.sha256(data).hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--swiftc', type=Path)
    args = p.parse_args()
    from validate_pip_native_entry import delegate_if_applied
    if delegate_if_applied(args): return
    plan = json.loads((ROOT/'ios/pip_native_transaction_patches.json').read_text())
    for name, digest in {**plan['guards'], **plan['outputs']}.items():
        assert sha((args.source/name).read_bytes()) == digest, name
    for name,digest in plan['templates'].items():
        assert sha((ROOT/'ios'/name).read_bytes()) == digest, name
    final = {name:(args.source/name).read_text() for name in plan['outputs']}
    before = dict(final)
    for name,a,b,count in reversed(plan['patches']):
        assert before[name].count(b) == count
        before[name] = before[name].replace(b,a,count)
    for name,text in before.items(): assert sha(text.encode()) == plan['inputs'][name],name
    gesture,item,visual = final[GESTURE],final[ITEM],final[VISUAL]
    assert all(text not in gesture for text in ['scaledBy(', 'surface.transform(', 'UIViewPropertyAnimator(', 'prepareForPictureInPictureSwipe()'])
    assert 'abs(velocity.y) > abs(velocity.x)' in gesture
    assert 'self.active, self.faded' not in visual
    assert 'self.lifecycle.phase == .preparing' in item
    assert item.count('startPictureInPicture()') == 1
    for marker in ['private var nagramiXCanUseSystemPiP:', 'override func nagramiXStartDirectionalPiP(',
                   'private func nagramiXUpdateBackgroundVideoPlayback(', '@objc func pictureInPictureButtonPressed()',
                   'override func containerLayoutUpdated(']:
        assert block(item,marker) == block(before[ITEM],marker),marker
    assert 'self?.rollbackTransition()' in block(item,'func start(acquirePrevious:')
    assert 'self.nagramiXPiPSurface.view.transform = .identity' in block(item,'private func nagramiXStartSystemPiP(')
    assert 'visual.restore()' in item and 'nagramiXPreparePiPRestoration()' in item
    print('PASS: native-only source, exact rollback/commit integration, untouched eligibility/ownership/audio/recovery/rotation guards')
    if args.swiftc:
        with tempfile.TemporaryDirectory() as folder:
            temp=Path(folder)
            native='import Foundation\n'+gesture.replace('import UIKit\n','').replace('import Display\n','').replace('@objc private func pan(', 'private func pan(').replace('#selector(self.pan(_:))','0')
            native+='\nextension NagramiXPiPGestureController { func testDrivePan() { self.pan(self.recognizer) } }\n'
            source=temp/'Gesture.swift';source.write_text(native)
            method=block(item,'func start(acquirePrevious:')
            harness=temp/'Transaction.swift'
            harness.write_text((ROOT/'scripts/tests/NagramiXPiPNativeTransactionTests.swift').read_text().replace('// START_METHOD',method))
            lifecycle=args.source/(GALLERY+'NagramiXPiPLifecycle.swift')
            for flags in [[],['-O']]:
                for inputs in [
                    [ROOT/'scripts/tests/NagramiXPiPGestureSupport.swift',ROOT/'ios/Sources/GalleryUI/NagramiXPiPReleaseDecision.swift',source,ROOT/'scripts/tests/NagramiXPiPNativeGestureTests.swift'],
                    [lifecycle,args.source/VISUAL,harness],
                    [lifecycle,ROOT/'scripts/tests/NagramiXPiPLifecycleTests.swift'],
                ]:
                    subprocess.run([str(args.swiftc),'-warnings-as-errors','-module-cache-path',str(temp/'cache'),*flags,*map(str,inputs),'-o',str(temp/'tests')],check=True)
                    subprocess.run([str(temp/'tests')],check=True,timeout=30)
            # Реальные прежние тела должны воспроизвести оба исправляемых сбоя.
            old_visual=temp/'OldVisual.swift';old_visual.write_text(before[VISUAL])
            old_start=temp/'OldStart.swift'
            old_start.write_text((ROOT/'scripts/tests/NagramiXPiPNativeTransactionTests.swift').read_text().replace('// START_METHOD',block(before[ITEM],'func start(acquirePrevious:')))
            for inputs,message in [
                ([lifecycle,old_visual,harness],b'native success must dismiss without fade completion'),
                ([lifecycle,args.source/VISUAL,old_start],b'rollback before completion'),
            ]:
                subprocess.run([str(args.swiftc),'-module-cache-path',str(temp/'cache'),*map(str,inputs),'-o',str(temp/'old')],check=True)
                result=subprocess.run([str(temp/'old')],capture_output=True,cwd=temp,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
                assert result.returncode != 0 and message in result.stderr,message
            print('PASS: previous fade gate and delayed timeout rollback regressions reproduced and rejected')
            subprocess.run([str(args.swiftc),'-frontend','-parse',*[str(args.source/name) for name in plan['outputs']]],check=True)
    print('PASS: native PiP transaction; Apple SDK/AVKit animation/physical iPhone pending')

if __name__ == '__main__': main()
