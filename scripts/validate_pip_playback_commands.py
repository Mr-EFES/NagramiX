#!/usr/bin/env python3
"""Проверить идемпотентные команды воспроизведения штатного PiP."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import tempfile
from validate_quick_format import block, manifest
from validate_native_pip_baseline import runtime as native_fixture
from validate_round_caption_transport import runtime as caption_fixture
from validate_repost_copy_integrity import runtime as composer_fixture

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
STAGE = 'pip_playback_commands'
PLAN = json.loads((OVERLAY / (STAGE + '_patches.json')).read_text())
CORE = 'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift'
NODE = 'submodules/AccountContext/Sources/UniversalVideoNode.swift'
METHOD = '        public func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, setPlaying playing: Bool)'
NEW_COMMAND = '            if playing {\n                self.node.play()\n            } else {\n                self.node.pause()\n            }'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def verify(source):
    for name, digest in {**PLAN['outputs'], **PLAN['guards']}.items():
        assert sha((source / name).read_bytes()) == digest, name
    for name, digest in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest, name
    before = (OVERLAY / PLAN['previous'][CORE]).read_text()
    after = (source / CORE).read_text()
    old_method = block(before, METHOD)
    new_method = block(after, METHOD)
    assert old_method.count('            self.node.togglePlayPause()') == 1
    assert new_method == old_method.replace('            self.node.togglePlayPause()', NEW_COMMAND, 1)
    assert after == before.replace(old_method, new_method, 1), 'Unrelated native PiP changes'
    native = json.loads((OVERLAY / 'native_pip_baseline_patches.json').read_text())
    assert sha(before.encode()) == native['outputs'][CORE]
    # Exactly one agreed exception to the original native playback controller.
    original = (OVERLAY / native['native'][CORE]['source']).read_text()
    controller = 'private final class NativePictureInPictureContentImpl:'
    assert block(after.replace(new_method, old_method, 1), controller) == block(original, controller)
    post = json.loads((OVERLAY / 'upstream_13_2_post_patches.json').read_text())
    assert not set(PLAN['outputs']) & set(post['outputs'])
    node = (source / NODE).read_text()
    for method in ['play', 'pause', 'togglePlayPause']:
        body = block(node, '    public func ' + method + '(')
        assert 'self.manager.withUniversalVideoContent(id: self.content.id,' in body
        assert 'contentNode.' + method + '()' in body
    pipeline = (OVERLAY / 'apply_overlay.py').read_text()
    assert pipeline.index('    apply_round_caption_transport(') < pipeline.index('    apply_pip_playback_commands(')
    workflow = (ROOT / '.github/workflows/build-unsigned-ipa.yml').read_text()
    assert workflow.index('python3 scripts/validate_pip_playback_commands.py') < workflow.index('python3 scripts/validate_round_caption_transport.py')

def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location(STAGE, OVERLAY / (STAGE + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rejected = []

    def seed(label):
        tree = temp / label
        for name in {**PLAN['inputs'], **PLAN['guards']}:
            path = tree / name
            path.parent.mkdir(parents=True, exist_ok=True)
            origin = OVERLAY / PLAN['previous'][name] if name in PLAN['previous'] else source / name
            path.write_bytes(origin.read_bytes())
        return tree

    def reject(tree, label, overlay=OVERLAY):
        before = manifest(tree)
        try:
            module.apply_pip_playback_commands(tree, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Invalid input accepted: ' + label)
        assert manifest(tree) == before, 'Partial write: ' + label
        rejected.append(label)
        shutil.rmtree(tree)

    valid = seed('valid')
    module.apply_pip_playback_commands(valid, OVERLAY)
    for name in PLAN['outputs']:
        assert (valid / name).read_bytes() == (source / name).read_bytes(), name
    reject(valid, 'repeat')
    for index, name in enumerate({**PLAN['inputs'], **PLAN['guards']}):
        for kind in ['missing', 'drift']:
            tree = seed(str(index) + '-' + kind)
            if kind == 'missing':
                (tree / name).unlink()
            else:
                (tree / name).write_bytes(b'drift')
            reject(tree, kind + ' ' + name)
    variants = []
    for field in ['inputs', 'outputs', 'guards', 'templates']:
        bad = copy.deepcopy(PLAN)
        bad[field][next(iter(bad[field]))] = '0' * 64
        variants.append((field, bad))
    for field in ['previous', 'replacements']:
        bad = copy.deepcopy(PLAN)
        bad[field][CORE] = '../outside.swift'
        variants.append((field, bad))
    bad = copy.deepcopy(PLAN)
    bad['outputs'].clear()
    variants.append(('inconsistent', bad))
    for label, bad in variants:
        overlay = temp / ('overlay-' + label)
        for name in PLAN['templates']:
            path = overlay / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((OVERLAY / name).read_bytes())
        (overlay / (STAGE + '_patches.json')).write_text(json.dumps(bad))
        reject(seed('source-' + label), label, overlay)
    for index, name in enumerate([CORE, next(iter(PLAN['guards']))]):
        tree = seed('symlink-' + str(index))
        path = tree / name
        external = temp / ('outside-' + str(index))
        external.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(external)
        reject(tree, 'external symlink ' + name)
    return rejected

def runtime(source, legacy=False):
    code = native_fixture(source)
    assert code.count('enum Playback { case playing, paused, buffering }') == 1
    code = code.replace('enum Playback { case playing, paused, buffering }', 'enum Playback: Equatable { case playing, paused, buffering(whilePlaying: Bool) }', 1)
    old_node = block(code, 'final class UniversalVideoNode {')
    node = old_node.replace('    let layer = VideoLayer()', '    let content = PlaybackCommandIdentity()\n    lazy var manager = PlaybackCommandManager(status: status)\n    let layer = VideoLayer()', 1)
    original_node = (source / NODE).read_text()
    for method in ['pause', 'togglePlayPause']:
        old = block(node, '    func ' + method + '(')
        actual = block(original_node, '    public func ' + method + '(').replace('public ', '')
        node = node.replace(old, actual, 1)
    play = block(original_node, '    public func play(').replace('public ', '')
    node = node[:-1] + play + '\n}'
    boundary = (ROOT / 'scripts/tests/NagramiXPiPPlaybackCommandsBoundary.swift').read_text()
    code = code.replace(old_node, boundary + '\n' + node, 1)
    if legacy:
        return code
    return code.split('@main enum NativePiPTests')[0] + (ROOT / 'scripts/tests/NagramiXPiPPlaybackCommandsTests.swift').read_text()


def execute(source, swiftc, temp):
    code = runtime(source)
    before = (OVERLAY / PLAN['previous'][CORE]).read_text()
    old = block(before, METHOD).replace('public ', '')
    new = block((source / CORE).read_text(), METHOD).replace('public ', '')
    cached = old.replace('            self.node.togglePlayPause()', '            guard let status = self.status, (status.status == .playing) != playing else { return }\n            self.node.togglePlayPause()')
    inverted = new.replace('if playing {', 'if !playing {', 1)
    variants = {
        'current': code,
        'previous-native': runtime(source, legacy=True),
        'previous-caption': caption_fixture(source),
        'previous-composer': composer_fixture(source),
        'old-toggle-command': code.replace(new, old, 1),
        'cached-status-toggle': code.replace(new, cached, 1),
        'inverted-command': code.replace(new, inverted, 1),
    }
    positive = {'current', 'previous-native', 'previous-caption', 'previous-composer'}
    assert all(content != code for name, content in variants.items() if name not in positive)
    results = []
    for label, content in variants.items():
        path = temp / (label + '.swift')
        path.write_text(content)
        for optimized in [False, True]:
            name = label + ('-O' if optimized else '-debug')
            binary = temp / name
            files = temp / (name + '-files')
            files.mkdir()
            command = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache')]
            command += ['-O'] if optimized else []
            compiled = subprocess.run(command + [str(path), '-o', str(binary)], capture_output=True, text=True)
            assert compiled.returncode == 0, compiled.stdout + compiled.stderr
            run = subprocess.run([str(binary)], env={**os.environ, 'TMPDIR': str(files)}, capture_output=True, text=True, timeout=30, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if label in positive:
                assert run.returncode == 0, run.stdout + run.stderr
                status = run.stdout.strip()
            else:
                assert run.returncode != 0 and 'PiP playback command regression:' in run.stderr, run.stdout + run.stderr
                status = 'regression reproduced and rejected'
            results.append(name + ': ' + status)
            print(results[-1], flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-pip-playback-check-') as folder:
        temp = Path(folder)
        rejected = guard_checks(args.source, temp / 'guards')
        run = temp / 'runtime'
        run.mkdir()
        results = execute(args.source, args.swiftc, run) if args.swiftc else []
        if args.swiftc:
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / CORE)], check=True)
    report = {
        'replacements': len(PLAN['outputs']), 'guards': len(PLAN['guards']),
        'fail_closed': len(rejected), 'executions': results,
        'scope': 'R3: native PiP explicit playback commands; R1/R2 preserved',
        'sdk': 'not authorized or run', 'device': 'pending',
        'boundaries': 'Production AVKit playback delegate and UniversalVideoNode command methods. Content lookup, decoder, status scheduling and AVKit/UIKit are explicit boundaries; no physical animation/device execution.',
    }
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
