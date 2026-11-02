#!/usr/bin/env python3
"""Validate actual source geometry and the final guarded GalleryUI integration.

Does not build the iOS application or claim to execute AVKit on an iPhone.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def validate(before, after, swiftc):
    plan = json.loads((ROOT / 'ios/pip_transition_patches.json').read_text())
    a, b = manifest(before), manifest(after)
    changed = {n for n in a.keys() & b.keys() if a[n] != b[n]}
    assert b.keys() - a.keys() == set(plan['copies'].values())
    assert not a.keys() - b.keys()
    assert changed == {p[0] for p in plan['patches']}
    assert plan['hashes'] == {n: a[n] for n in plan['hashes']}
    templates = {marker: (ROOT / 'ios' / path).read_text().rstrip('\n')
                 for marker, path in plan['templates'].items()}
    restored = {n: (after / n).read_text() for n in plan['hashes']}
    for name, old, new, count in reversed(plan['patches']):
        for marker, template in templates.items():
            new = new.replace(marker, template)
        assert restored[name].count(new) == count, (name, new[:100])
        restored[name] = restored[name].replace(new, old, count)
    assert all(restored[n].encode() == (before / n).read_bytes() for n in restored)
    for template, name in plan['copies'].items():
        assert (after / name).read_bytes() == (ROOT / 'ios' / template).read_bytes()

    spec = importlib.util.spec_from_file_location('pip_transition', ROOT / 'ios/pip_transition.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    guards = []
    with tempfile.TemporaryDirectory() as folder:
        native, overlay = Path(folder) / 'native', Path(folder) / 'ios'

        def seed():
            for path in [native, overlay]:
                if path.exists():
                    shutil.rmtree(path)
            for n in plan['hashes']:
                path = native / n
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(before / n, path)
            for n in ['pip_transition_patches.json', *plan['templates'].values(), *plan['copies']]:
                path = overlay / n
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / 'ios' / n, path)

        def reject(label):
            previous = manifest(native)
            try:
                module.apply_pip_transition(native, overlay)
            except (SystemExit, FileNotFoundError):
                pass
            else:
                raise AssertionError(label)
            assert manifest(native) == previous, label + ' partially mutated native files'
            guards.append(label)

        seed()
        module.apply_pip_transition(native, overlay)
        assert all((native / n).read_bytes() == (after / n).read_bytes()
                   for n in [*plan['hashes'], *plan['copies'].values()])
        reject('repeat application')
        for n in plan['hashes']:
            seed()
            (native / n).write_bytes((native / n).read_bytes() + b'\n// drift\n')
            reject('full hash drift: ' + n)
            seed()
            (native / n).unlink()
            reject('missing input: ' + n)
        for n in ['pip_transition_patches.json', *plan['templates'].values(), *plan['copies']]:
            seed()
            (overlay / n).unlink()
            reject('missing integration resource: ' + n)
        for n in plan['copies'].values():
            seed()
            (native / n).write_text('// collision')
            reject('existing helper: ' + n)
        seed()
        invalid = json.loads(json.dumps(plan))
        invalid['patches'][-1][3] += 1
        (overlay / 'pip_transition_patches.json').write_text(json.dumps(invalid))
        reject('last anchor mismatch before writes')
        seed()
        build = 'submodules/GalleryUI/BUILD'
        data = (native / build).read_bytes().replace(b'Sources/**/*.swift', b'Other/**/*.swift')
        (native / build).write_bytes(data)
        invalid = json.loads(json.dumps(plan))
        invalid['hashes'][build] = hashlib.sha256(data).hexdigest()
        (overlay / 'pip_transition_patches.json').write_text(json.dumps(invalid))
        reject('missing native Swift glob')

    gallery = (after / 'submodules/GalleryUI/Sources/GalleryControllerNode.swift').read_text()
    video = (after / 'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift').read_text()
    assert 'nagramiXAnimateDirectionalPiPTransfer' not in gallery
    assert 'nagramiX.pip.swipe.exit' not in gallery
    assert 'CATransaction.setCompletionBlock(start)' in gallery
    assert 'self.nagramiXDirectionalPiPSourceFrame = item.nagramiXPiPSourceFrame(in: space)' in gallery
    assert 'gesture.translation(in: space)' in gallery
    assert 'item.nagramiXPiPSwipeTransitionPending = true' in gallery
    assert 'item.nagramiXPiPSwipeTransitionPending = false' in gallery
    assert 'touch.view?.isDescendant(of: self.scrollView) == true' in gallery
    assert 'if current is UISlider || current is UISwitch' in gallery
    assert 'current.asyncdisplaykit_node is ASButtonNode' not in gallery
    fade = gallery.split('self.pager.completeCustomDismiss =', 1)[1].split('self.pager.baseNavigationController', 1)[0]
    assert fade.index('strongSelf.completeCustomDismiss(isPictureInPicture)') < fade.index('strongSelf.nagramiXResetDirectionalPiPSwipe')
    assert 'nagramiXPiPRequestRequiresSwipeSetting = requiresSwipeSetting' in video
    assert 'videoNode.ownsContentNode && !self.nagramiXPiPNativeTransitionInFlight' in video
    visibility = video.split('override func visibilityUpdated', 1)[1].split('override func processAction', 1)[0]
    assert visibility.index('if self.nagramiXPiPNativeTransitionInFlight') < visibility.index('videoNode.canAttachContent = isVisible')
    assert 'videoNode.canAttachContent = true\n                    return' in visibility
    assert video.count('controller?.startPictureInPicture()') == 1
    assert video.count('self.nagramiXStartSystemPiP(requiresSwipeSetting:') == 2
    assert 'self.nativePictureInPictureContent === content, !didExpand else { return }' in video
    assert '(activePictureInPictureController.displayNode as? GalleryControllerNode)?.nagramiXPreparePiPRestoration()' in video

    executed = []
    with tempfile.TemporaryDirectory() as folder:
        for mode in ['debug', 'optimized']:
            groups = [
                ('source geometry', ['ios/Sources/GalleryUI/NagramiXPiPReleaseDecision.swift',
                    'ios/Sources/GalleryUI/NagramiXPiPSourceGeometry.swift', 'scripts/tests/NagramiXPiPSourceGeometryTests.swift']),
                ('playback lifecycle', ['ios/Sources/GalleryUI/NagramiXPiPPlaybackSession.swift',
                    'scripts/tests/NagramiXPiPPlaybackSessionTests.swift']),
                ('release decisions', ['ios/Sources/GalleryUI/NagramiXPiPReleaseDecision.swift',
                    'scripts/tests/NagramiXPiPReleaseDecisionTests.swift']),
            ]
            for label, paths in groups:
                args = [str(swiftc), '-warnings-as-errors', '-module-cache-path', folder + '/cache',
                        *[str(ROOT / n) for n in paths], '-o', folder + '/test']
                if mode == 'optimized':
                    args.insert(1, '-O')
                if sys.platform.startswith('linux'):
                    args.append('-lm')
                subprocess.run(args, check=True)
                result = subprocess.check_output([folder + '/test'], text=True).strip()
                executed.append(mode + ' ' + label + ': ' + result)
        subprocess.run([str(swiftc), '-frontend', '-parse', *[str(after / n) for n in changed]], check=True)
    return {'outputs': len(b), 'changed': sorted(changed), 'new': list(plan['copies'].values()),
            'unchanged': len(a) - len(changed), 'full_hashes': len(plan['hashes']),
            'reversed_operations': len(plan['patches']), 'fail_closed_cases': guards,
            'swift_execution': executed, 'ios_build': 'not started; separate user command required',
            'physical_iPhone': 'pending'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'swiftc']:
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    output = json.dumps(validate(args.before, args.after, args.swiftc), ensure_ascii=False, indent=2) + '\n'
    if args.report:
        args.report.write_text(output)
    print(output, end='')
