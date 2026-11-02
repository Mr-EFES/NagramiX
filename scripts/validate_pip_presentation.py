#!/usr/bin/env python3
"""Проверить итоговый native PiP без прозрачной галереи поверх чата."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    args = parser.parse_args()
    from validate_pip_native_entry import delegate_if_applied
    if delegate_if_applied(args): return
    plan = json.loads((ROOT/'ios/pip_presentation_patches.json').read_text())
    native = json.loads((ROOT/'ios/pip_native_transaction_patches.json').read_text())
    current = all(hashlib.sha256((args.source/name).read_bytes()).hexdigest() == digest for name,digest in native['outputs'].items())
    expected = dict(plan['outputs'])
    if current: expected.update(native['outputs'])
    for name, digest in expected.items():
        assert hashlib.sha256((args.source/name).read_bytes()).hexdigest() == digest, name
    for name, digest in plan['templates'].items():
        assert hashlib.sha256((ROOT/'ios'/name).read_bytes()).hexdigest() == digest, name
    gesture = (args.source/'submodules/GalleryUI/Sources/NagramiXPiPGestureController.swift').read_text()
    assert 'self.sourcePreview(true)' not in gesture
    assert 'surface.initialBackgroundAlpha * (1 - pose.progress)' not in gesture
    node = (args.source/'submodules/GalleryUI/Sources/GalleryControllerNode.swift').read_text()
    callback = node.split('self.pager.completeCustomDismiss =', 1)[1].split('self.pager.baseNavigationController', 1)[0]
    assert 'nagramiXResetDirectionalPiPSwipe' not in callback
    assert 'previousLayout.size != layout.size' in node and 'self.nagramiXCancelSwipePreparation()' in node
    item = (args.source/'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift').read_text()
    assert 'self.dismissOnOrientationChange = item.landscape' not in item
    assert 'guard self.lifecycle.phase != .finished, self.node === node' in item
    assert 'guard self.lifecycle.phase == .preparing else { return }' in item
    assert 'self.nagramiXStartSystemPiP(requiresSwipeSetting: true' in item
    assert 'self.nagramiXStartSystemPiP(requiresSwipeSetting: false' in item
    if args.swiftc:
        if current:
            subprocess.run(['python3', str(ROOT/'scripts/validate_pip_native_transaction.py'),
                '--source', str(args.source), '--swiftc', str(args.swiftc)], check=True)
            print('PASS: previous presentation guards and current native transaction execution; iPhone pending')
            return
        subprocess.run(['python3', str(ROOT/'scripts/validate_pip_presentation_gesture.py'),
                        '--swiftc', str(args.swiftc)], check=True)
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            assignment = next(line.strip() for line in item.splitlines() if 'self.playbackControls.view?.isHidden =' in line)
            chrome = temp/'Chrome.swift'
            chrome.write_text('import Foundation\nfinal class ChromeView { var isHidden = false }\nfinal class Controls { var view: ChromeView? = ChromeView() }\nfinal class ChromeHost { let playbackControls = Controls(); var nagramiXPiPSwipeTransitionPending = false; var nagramiXPiPNativeTransitionInFlight = false; func update(isVisible: Bool) { '+assignment+' } }')
            for flags in [[], ['-O']]:
                subprocess.run([str(args.swiftc), '-parse-as-library', '-module-cache-path', str(temp/'cache'),
                    *flags, str(chrome), str(ROOT/'scripts/tests/NagramiXPiPChromeTests.swift'), '-o', str(temp/'test')], check=True)
                subprocess.run([str(temp/'test')], check=True)
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder)/'BadGesture.swift'
            assert gesture.count('surface.background.alpha = surface.initialBackgroundAlpha') == 1
            bad.write_text(gesture.replace('surface.background.alpha = surface.initialBackgroundAlpha',
                'surface.background.alpha = surface.initialBackgroundAlpha * (1 - pose.progress)'))
            failed = subprocess.run(['python3', str(ROOT/'scripts/validate_pip_presentation_gesture.py'),
                '--swiftc', str(args.swiftc), '--source-file', str(bad)], capture_output=True)
            assert failed.returncode != 0 and b'gallery stays opaque during motion' in failed.stderr
            print('PASS: transparent-background regression rejected during actual gesture execution')
        subprocess.run([str(args.swiftc), '-frontend', '-parse',
                        *[str(args.source/name) for name in plan['outputs']]], check=True)
    print('PASS: final PiP source/controls/rotation guards; SDK/device pending')

if __name__ == '__main__':
    main()
