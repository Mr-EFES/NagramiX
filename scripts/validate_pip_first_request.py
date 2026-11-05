#!/usr/bin/env python3
"""Проверить первый запрос PiP, готовность слоя и передачу анимации AVKit."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from validate_quick_format import block, manifest
from validate_system_video_pip import runtime_source as original_runtime_source

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'pip_first_request_patches.json').read_text())
I = next(iter(PLAN['inputs']))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(source):
    for name, digest in {**PLAN['outputs'], **PLAN['guards']}.items():
        assert sha((source / name).read_bytes()) == digest, name
    for name, digest in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest, name
    text = (source / I).read_text()
    before = (OVERLAY / PLAN['previous'][I]).read_text()
    assert block(text, 'private final class PlaybackDelegate:') == block(before, 'private final class PlaybackDelegate:')
    for marker in ['func expandPIP(', 'override func maybePerformActionForSwipeDownDismiss(', 'override func centralityUpdated(']:
        assert block(text, marker) == block(before, marker), marker
    assert text.count('private final class NativePictureInPictureContentImpl:') == 1
    assert text.count('AVPictureInPictureController(contentSource:') == 1
    assert 'AVPlayer(' not in text and 'UIWindow(' not in text
    assert 'guard item.content is NativeVideoContent || videoNode.getVideoLayer() != nil' in text
    appearance = block(text, 'private final class SourceAppearance {')
    assert '.presentation(' not in appearance and 'CABasicAnimation(' not in appearance
    assert 'layer.add(' not in appearance and 'setDisableActions(true)' in appearance
    player = (source / 'submodules/MediaPlayer/Sources/MediaPlayerNode.swift').read_text()
    assert 'init(layer:' not in block(player, 'private final class MediaPlayerNodeLayer:')


def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location('pip_first_request', OVERLAY / 'pip_first_request.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rejected = []
    def seed(label):
        tree = temp / label
        for name in {**PLAN['inputs'], **PLAN['guards']}:
            path = tree / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((OVERLAY / PLAN['previous'][name] if name in PLAN['previous'] else source / name).read_bytes())
        return tree
    def reject(tree, label, overlay=OVERLAY):
        before = manifest(tree)
        try:
            module.apply_pip_first_request(tree, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Invalid input accepted: ' + label)
        assert manifest(tree) == before, 'Partial write: ' + label
        rejected.append(label)
    valid = seed('valid')
    module.apply_pip_first_request(valid, OVERLAY)
    assert (valid / I).read_bytes() == (source / I).read_bytes()
    reject(valid, 'repeat')
    for index, name in enumerate({**PLAN['inputs'], **PLAN['guards']}):
        for kind in ['missing', 'drift']:
            tree = seed(f'{index}-{kind}')
            if kind == 'missing': (tree / name).unlink()
            else: (tree / name).write_bytes(b'drift')
            reject(tree, kind + ' ' + name)
    mutations = []
    for field in ['inputs', 'outputs', 'guards', 'templates']:
        bad = copy.deepcopy(PLAN)
        bad[field][next(iter(bad[field]))] = '0' * 64
        mutations.append((field, bad))
    for field in ['previous', 'replacements']:
        bad = copy.deepcopy(PLAN); bad[field][I] = '../outside.swift'
        mutations.append((field, bad))
    bad = copy.deepcopy(PLAN); bad['outputs'].clear(); mutations.append(('inconsistent', bad))
    for label, bad in mutations:
        overlay = temp / ('overlay-' + label)
        for name in PLAN['templates']:
            path = overlay / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((OVERLAY / name).read_bytes())
        (overlay / 'pip_first_request_patches.json').write_text(json.dumps(bad))
        reject(seed('source-' + label), label, overlay)
    for index, name in enumerate([I, next(iter(PLAN['guards']))]):
        tree = seed('symlink-' + str(index)); outside = temp / ('external-' + str(index))
        path = tree / name; outside.write_bytes(path.read_bytes()); path.unlink(); path.symlink_to(outside)
        reject(tree, 'external symlink ' + name)
    return rejected


def runtime_source(source, mode):
    text = original_runtime_source(source)
    text = text.replace((ROOT / 'scripts/tests/NagramiXSystemVideoPiPBoundary.swift').read_text(), (ROOT / 'scripts/tests/NagramiXPiPFirstRequestBoundary.swift').read_text())
    text = text.replace((ROOT / 'scripts/tests/NagramiXSystemVideoPiPTests.swift').read_text(), (ROOT / 'scripts/tests/NagramiXPiPFirstRequestTests.swift').read_text())
    text = text.replace('    var isCentral: Bool?\n', '    var isCentral: Bool?\n    var _isVisible: Bool?\n')
    visibility = block((source / I).read_text(), 'override func visibilityUpdated(')
    cancel_visibility = block(visibility, 'if !isVisible, let content =')
    text = text.replace('func updateCentral(_ isCentral: Bool) {', 'func setVisible(_ value: Bool) {\n    self._isVisible = value\n    let isVisible = value\n' + cancel_visibility + '\n}\nfunc updateCentral(_ isCentral: Bool) {')
    if mode == 'discarded-request':
        before = (OVERLAY / PLAN['previous'][I]).read_text()
        old = block(before, 'func beginPictureInPicture(').replace('func beginPictureInPicture()', '@discardableResult func beginPictureInPicture() -> Bool').replace('return\n', 'return false\n')
        old = old[:-1] + '    return true\n    }'
        text = text.replace(block(text, '@discardableResult func beginPictureInPicture('), old)
    elif mode == 'cold-swipe':
        before = (OVERLAY / PLAN['previous'][I]).read_text()
        old = block(before, 'override func maybePerformActionForSwipeDismiss(')
        text = text.replace(block(text, 'override func maybePerformActionForSwipeDismiss('), old)
    elif mode == 'early-dismiss':
        fade = '''                self.beginCustomDismiss(.pip)
                controller.view.alpha = 0.0
                controller.view.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.2, completion: { [weak self] _ in
                    self?.completeCustomDismiss(true)
                })'''
        assert text.count(fade) == 1
        text = text.replace(fade, '                let _ = controller')
        text = text.replace('                self.updateControlsVisibility(false)\n                didExpand = false', fade + '\n                didExpand = false')
    elif mode == 'square-corners':
        assert text.count('        self.prepareSourceAppearance()') == 2
        text = text.replace('        self.prepareSourceAppearance()', '')
    elif mode in ['sample-buffer-presentation', 'sample-buffer-animation']:
        marker = '            let toRadius = max(self.radius, min(layer.bounds.width, layer.bounds.height) * 0.06)'
        assert text.count(marker) == 1
        old = ('            let _ = layer.presentation()' if mode == 'sample-buffer-presentation' else
               '            layer.add(CABasicAnimation(keyPath: "cornerRadius"), forKey: "nagramiXPiPSourceCorners")')
        text = text.replace(marker, old + '\n' + marker)
    return text


def execute(source, swiftc, temp):
    runs = []
    for mode in ['current', 'discarded-request', 'cold-swipe', 'early-dismiss', 'square-corners', 'sample-buffer-presentation', 'sample-buffer-animation']:
        suite = temp / (mode + '.swift'); suite.write_text(runtime_source(source, mode))
        for optimized in [False, True]:
            name = mode + ('-O' if optimized else '-debug'); binary = temp / name
            command = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache')]
            if optimized: command.append('-O')
            subprocess.run([*command, str(suite), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if mode == 'current':
                assert result.returncode == 0, result.stdout + result.stderr
                message = result.stdout.strip()
            else:
                assert result.returncode != 0 and 'first PiP regression:' in result.stderr, result.stdout + result.stderr
                if mode.startswith('sample-buffer-'):
                    assert 'unsupported' in result.stderr and 'copy' in result.stderr, result.stderr
                message = 'previous behavior reproduced and rejected'
            print(name + ': ' + message, flush=True)
            runs.append(name + ': ' + message)
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    if delegate_icon_stage_if_applied(args, Path(__file__), 'message_copy_availability'):
        return
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-pip-first-') as folder:
        temp = Path(folder)
        rejected = guard_checks(args.source, temp)
        runs = execute(args.source, args.swiftc, temp) if args.swiftc else []
        if args.swiftc: subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / I)], check=True)
    report = {'files': 1, 'guards': len(PLAN['guards']), 'rejected': rejected, 'executions': runs, 'sdk': 'not run', 'device': 'pending', 'boundaries': 'Actual native controller, setup, centrality, button, swipe and restore; deterministic main queue and AVKit/UIKit/CA stand-ins. Source appearance properties/order verified, not physical system window rendering.'}
    if args.report: args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
