#!/usr/bin/env python3
"""Проверяет новый runtime PiP, охрану overlay и реальные Swift-переходы.

Apple SDK и системное окно на физическом iPhone проверяются отдельно.
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
    plan = json.loads((ROOT / 'ios/pip_runtime_patches.json').read_text())
    a, b = manifest(before), manifest(after)
    changed = {n for n in a.keys() & b.keys() if a[n] != b[n]}
    assert changed == {p[0] for p in plan['patches']}
    assert b.keys() - a.keys() == set(plan['copies'].values())
    assert a.keys() - b.keys() == set(plan['remove'])
    assert plan['hashes'] == {n: a[n] for n in plan['hashes']}
    templates = {m: (ROOT / 'ios' / n).read_text().rstrip('\n') for m, n in plan['templates'].items()}
    applied = {n: (before / n).read_text() for n in plan['hashes']}
    for name, old, new, count in plan['patches']:
        for marker, value in templates.items():
            new = new.replace(marker, value)
        assert applied[name].count(old) == count
        applied[name] = applied[name].replace(old, new, count)
    for n in changed:
        assert applied[n].encode() == (after / n).read_bytes(), n
    for template, n in plan['copies'].items():
        assert (after / n).read_bytes() == (ROOT / 'ios' / template).read_bytes()

    spec = importlib.util.spec_from_file_location('pip_runtime', ROOT / 'ios/pip_runtime.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    guards = []
    with tempfile.TemporaryDirectory() as folder:
        native, overlay = Path(folder) / 'native', Path(folder) / 'ios'

        def seed():
            for p in [native, overlay]:
                if p.exists(): shutil.rmtree(p)
            for n in plan['hashes']:
                p = native / n
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(before / n, p)
            for n in ['pip_runtime_patches.json', *plan['templates'].values(), *plan['copies']]:
                p = overlay / n
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / 'ios' / n, p)

        def reject(label):
            snapshot = manifest(native)
            try: module.apply_pip_runtime(native, overlay)
            except (SystemExit, FileNotFoundError): pass
            else: raise AssertionError(label)
            assert manifest(native) == snapshot, label + ': partial mutation'
            guards.append(label)

        seed()
        module.apply_pip_runtime(native, overlay)
        assert all((native / n).read_bytes() == (after / n).read_bytes()
                   for n in [*changed, *plan['copies'].values()])
        assert all(not (native / n).exists() for n in plan['remove'])
        reject('повторное применение')
        for n in plan['hashes']:
            seed(); (native / n).write_bytes((native / n).read_bytes() + b'\n// drift\n')
            reject('SHA drift: ' + n)
            seed(); (native / n).unlink()
            reject('нет исходника: ' + n)
        for n in ['pip_runtime_patches.json', *plan['templates'].values(), *plan['copies']]:
            seed(); (overlay / n).unlink()
            reject('нет ресурса: ' + n)
        for n in plan['copies'].values():
            seed(); (native / n).write_text('// collision')
            reject('конфликт helper: ' + n)
        seed()
        invalid = json.loads(json.dumps(plan)); invalid['patches'][-1][3] += 1
        (overlay / 'pip_runtime_patches.json').write_text(json.dumps(invalid))
        reject('последний anchor до первой записи')
        seed()
        build = 'submodules/GalleryUI/BUILD'
        data = (native / build).read_bytes().replace(b'Sources/**/*.swift', b'Other/**/*.swift')
        (native / build).write_bytes(data)
        invalid = json.loads(json.dumps(plan)); invalid['hashes'][build] = hashlib.sha256(data).hexdigest()
        (overlay / 'pip_runtime_patches.json').write_text(json.dumps(invalid))
        reject('нет Swift glob')

    video = (after / 'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift').read_text()
    gallery = (after / 'submodules/GalleryUI/Sources/GalleryControllerNode.swift').read_text()
    gesture = (after / 'submodules/GalleryUI/Sources/NagramiXPiPGestureController.swift').read_text()
    manager_path = 'submodules/TelegramUI/Sources/MediaManager.swift'
    manager = (after / manager_path).read_text()
    old_manager = (before / manager_path).read_text()
    start = '        let shouldKeepAudioSession:'
    assert old_manager.split(start, 1)[1].split('    public func setNagramiXBackgroundVideoPlayback', 1)[0] == manager.split(start, 1)[1].split('    public func setNagramiXSystemPiPPlayback', 1)[0]
    assert 'setNagramiXSystemPiPPlayback(id: UUID, active: Bool)' in (after / 'submodules/AccountContext/Sources/MediaManager.swift').read_text()
    assert video.count('self.mediaManager.setNagramiXSystemPiPPlayback(id: self.playbackOwner, active: true)') == 1
    assert video.count('self.mediaManager.setNagramiXSystemPiPPlayback(id: self.playbackOwner, active: false)') == 2
    for removed in ['NativePictureInPictureContentImpl', 'NagramiXPiPPlaybackSession',
                    'nagramiXDirectionalPiPSourceTimer', 'nagramiXFinishDirectionalPiPSource']:
        assert removed not in video
    assert 'nagramiXDirectionalPiPInitialTransform' not in gallery
    assert 'CATransaction.setCompletionBlock' not in gallery
    assert video.count('startPictureInPicture()') == 1
    assert video.count('self.nagramiXStartSystemPiP(requiresSwipeSetting:') == 2
    assert 'return self.nagramiXPiPSurface.view' in video
    assert 'self.nagramiXPiPSurface.addSubnode(self.scrollNode)' in video
    assert 'aboveSubnode: self.scrollNode)' not in video
    assert 'belowSubview: self.scrollNode.view)' not in video
    assert video.count('belowSubview: self.nagramiXPiPSurface.view)') == 2
    assert 'aboveSubnode: self.nagramiXPiPSurface)' in video
    assert 'setNagramiXBackgroundPlayback(id: self.playbackOwner, active: true)' in video
    assert 'switch AVAudioSession.sharedInstance().category' in video
    assert 'NagramiXPiPAudioPolicy.needsPlaybackLease(managedPlaybackActive: self.managedPlaybackActive' in video
    assert 'setCanPlaybackWithoutHierarchy(' not in video.split('private final class NagramiXSystemPiPController:', 1)[1].split('final class UniversalVideoGalleryItemNode:', 1)[0]
    assert 'self.skipInitialPause = true' not in video.split('private func setupNativePictureInPicture()', 1)[1]
    assert 'if self.nagramiXPiPNativeTransitionInFlight {\n                    videoNode.canAttachContent = true\n                } else if isCentral' in video
    assert 'controller.view.window != nil' in video
    assert 'if node?.ownsContentNode == true { node?.pause() }' in video
    assert 'self.lifecycle.restoreInterface(completion: completion)' in video
    assert 'self.lifecycle.restoreInterface { [weak self] restored in if restored { self?.stop() } }' in video
    assert 'self.controller?.startPictureInPicture()' not in gesture
    assert gesture.index('guard gesture.state == .ended') < gesture.index('surface.item.nagramiXStartDirectionalPiP')
    assert 'surface.item.nagramiXPiPSwipeTransitionPending = false' in gesture
    assert 'duration: 0.18' not in gesture and 'surface.transform(release:' not in gesture
    assert 'surface.view.transform = surface.transform(for: pose)' in gesture
    assert 'surface.background.alpha = surface.initialBackgroundAlpha * (1 - pose.progress)' in gesture
    assert 'item.prepareForPictureInPictureSwipe()' in gesture
    assert 'surface.background.alpha = surface.restBackgroundAlpha' in gesture
    assert 'self.generation == generation' in gesture
    assert 'shouldBeRequiredToFailBy otherGestureRecognizer:' in gesture
    assert 'otherGestureRecognizer is TapLongTapOrDoubleTapGestureRecognizer' in gesture
    assert 'surface.item.updateControlsVisibility(surface.controlsWereVisible)' in gesture
    assert video.count('?.nagramiXAllowsSystemPiPTransition == true') == 3
    assert 'guard let self, let source, self.videoNode === source, !started, !self.nagramiXPiPSourceWasCancelled' in video
    assert 'self.pager.centralItemNode()?.cancelPictureInPictureSwipePreparation()' in gallery

    executed = []
    with tempfile.TemporaryDirectory() as folder:
        owner_methods = manager[manager.index('    public func setNagramiXSystemPiPPlayback'):]
        owner_methods = owner_methods[:owner_methods.index('    deinit {')]
        owner_properties = '\n'.join(line for line in manager.splitlines()
            if any(('private var ' + name + ' ') in line or ('private let ' + name + ' ') in line
                   for name in ['nagramiXBackgroundVideoOwners', 'nagramiXSystemPiPOwners', 'nagramiXBackgroundVideoPlaying']))
        assert len(owner_properties.splitlines()) == 3
        harness = Path(folder) / 'MediaManagerHarness.swift'
        harness.write_text('''import Foundation
enum NagramiXTabSettings { static var backgroundVideoPlaybackEnabled = false }
final class ValuePromise<T: Equatable> {
    var value: T
    init(_ value: T, ignoreRepeated: Bool) { self.value = value }
    func set(_ value: T) { self.value = value }
}
final class Queue {
    static func mainQueue() -> Queue { Queue() }
    func async(_ f: @escaping () -> Void) { f() }
}
protocol PiPMediaManager { func setNagramiXSystemPiPPlayback(id: UUID, active: Bool) }
extension PiPMediaManager { func setNagramiXSystemPiPPlayback(id: UUID, active: Bool) {} }
final class MediaManagerHarness: PiPMediaManager {
''' + owner_properties + '\n' + owner_methods + '''
    var keepAudio: Bool { self.nagramiXBackgroundVideoPlaying.value }
    func settingsChanged(_ value: Bool) {
        NagramiXTabSettings.backgroundVideoPlaybackEnabled = value
        self.nagramiXUpdateBackgroundVideoState()
    }
}
''')
        groups = [
            ('жизненный цикл', ['ios/Sources/GalleryUI/NagramiXPiPLifecycle.swift', 'scripts/tests/NagramiXPiPLifecycleTests.swift']),
            ('аудиоготовность', ['ios/Sources/GalleryUI/NagramiXPiPLifecycle.swift', 'scripts/tests/NagramiXPiPAudioPolicyTests.swift']),
            ('сессия PiP в фоне', [str(harness), 'scripts/tests/NagramiXPiPBackgroundOwnershipTests.swift']),
            ('геометрия трёх форматов', ['ios/Sources/GalleryUI/NagramiXPiPReleaseDecision.swift', 'ios/Sources/GalleryUI/NagramiXPiPSourceGeometry.swift', 'scripts/tests/NagramiXPiPSourceGeometryTests.swift']),
            ('непрерывность отпускания', ['ios/Sources/GalleryUI/NagramiXPiPReleaseDecision.swift', 'ios/Sources/GalleryUI/NagramiXPiPSourceGeometry.swift', 'scripts/tests/NagramiXPiPHandoffContinuityTests.swift']),
            ('свайп / удерживание', ['ios/Sources/GalleryUI/NagramiXPiPReleaseDecision.swift', 'scripts/tests/NagramiXPiPReleaseDecisionTests.swift']),
        ]
        for mode in ['debug', 'optimized']:
            for label, paths in groups:
                args = [str(swiftc), '-warnings-as-errors', '-module-cache-path', folder + '/cache',
                        *[str(ROOT / n) for n in paths], '-o', folder + '/test']
                if mode == 'optimized': args.insert(1, '-O')
                if sys.platform.startswith('linux'): args.append('-lm')
                subprocess.run(args, check=True)
                result = subprocess.check_output([folder + '/test'], text=True).strip()
                executed.append(mode + ' ' + label + ': ' + result)
        native_swift = sorted(changed | set(plan['copies'].values()))
        subprocess.run([str(swiftc), '-frontend', '-parse', *[str(after / n) for n in native_swift]], check=True)
    return {'outputs': len(b), 'changed': sorted(changed), 'new': list(plan['copies'].values()),
            'removed': plan['remove'], 'unchanged': len(a) - len(changed) - len(plan['remove']),
            'full_hashes': len(plan['hashes']), 'exact_operations': len(plan['patches']),
            'native_automatic_dropAll_and_calls': 'Штатные foreground/dropAll и звонки побайтно прежние; отдельный PiP-владелец меняет только разрешение удержания аудио',
            'fail_closed_cases': guards, 'swift_execution': executed,
            'Apple_SDK': 'проверяется отдельно', 'physical_iPhone': 'ожидается'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'swiftc']:
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    output = json.dumps(validate(args.before, args.after, args.swiftc), ensure_ascii=False, indent=2) + '\n'
    if args.report: args.report.write_text(output)
    print(output, end='')
