#!/usr/bin/env python3
"""Проверить подпись кружка, политику превью и повтор обеих частей копии."""
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

from validate_copy_delivery import clean, payload_fixture, temporary_fixture
from validate_quick_format import block, manifest
from validate_repost_copy_integrity import runtime as composer_fixture

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
STAGE = 'round_caption_transport'
PLAN = json.loads((OVERLAY / (STAGE + '_patches.json')).read_text())
CORE = 'submodules/TelegramCore/Sources/Utils/NagramiXOutgoingCopy.swift'
OLD_FILTER = 'attributes.filter { $0 is TextEntitiesMessageAttribute }'
NEW_FILTER = 'attributes.filter { $0 is TextEntitiesMessageAttribute || $0 is OutgoingContentInfoMessageAttribute }'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(source):
    for name, digest in {**PLAN['outputs'], **PLAN['guards']}.items():
        assert sha((source / name).read_bytes()) == digest, name
    for name, digest in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest, name
    before = (OVERLAY / PLAN['previous'][CORE]).read_text()
    after = (source / CORE).read_text()
    old_caption = block(before, '        if separateRoundCaption {')
    new_caption = block(after, '        if separateRoundCaption {')
    assert old_caption.count(OLD_FILTER) == 1
    assert new_caption == old_caption.replace(OLD_FILTER, NEW_FILTER, 1)
    assert after == before.replace(old_caption, new_caption, 1), 'Unrelated copy/retry behavior changed'
    prior = json.loads((OVERLAY / 'repost_copy_integrity_patches.json').read_text())
    assert sha(before.encode()) == prior['outputs'][CORE]
    assert 'nagramiXBuildCopiedMessages' in after and 'sourceRanges' in after
    assert block(before, 'public func nagramiXRetryCopiedMessages(') == block(after, 'public func nagramiXRetryCopiedMessages(')
    post = json.loads((OVERLAY / 'upstream_13_2_post_patches.json').read_text())
    assert not set(PLAN['outputs']) & set(post['outputs'])
    pipeline = (OVERLAY / 'apply_overlay.py').read_text()
    assert pipeline.index('    apply_repost_copy_integrity(') < pipeline.index('    apply_round_caption_transport(')
    workflow = (ROOT / '.github/workflows/build-unsigned-ipa.yml').read_text()
    assert workflow.index('python3 scripts/validate_round_caption_transport.py') < workflow.index('python3 scripts/validate_repost_copy_integrity.py')


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
            module.apply_round_caption_transport(tree, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Invalid input accepted: ' + label)
        assert manifest(tree) == before, 'Partial write: ' + label
        rejected.append(label)
        shutil.rmtree(tree)

    valid = seed('valid')
    module.apply_round_caption_transport(valid, OVERLAY)
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


def runtime(source):
    base = payload_fixture(source).split('@main struct CopyDeliveryTests')[0]
    assert base.count('struct Message {') == 1
    assert base.count('final class TestCopyPostbox {') == 1
    base = base.replace('struct Message {', '''struct Message {
    var globallyUniqueId: Int64? = nil
    var threadId: Int64? = nil
    var timestamp: Int32 = 0
    var tags = 1, globalTags = 2, localTags = 3
''', 1)
    base = base.replace('final class TestCopyPostbox {', 'final class TestCopyPostbox {\n    let storage = RoundCaptionTransaction()', 1)
    boundary = (ROOT / 'scripts/tests/NagramiXRoundCaptionTransportBoundary.swift').read_text()
    retry = clean(block((source / CORE).read_text(), 'public func nagramiXRetryCopiedMessages('))
    return base + '\n' + boundary.replace('// PRODUCTION_RETRY', retry) + '\n' + (ROOT / 'scripts/tests/NagramiXRoundCaptionTransportTests.swift').read_text()


def execute(source, swiftc, temp):
    code = runtime(source)
    stripped = lambda flag: NEW_FILTER + '.map { attribute -> MessageAttribute in if let info = attribute as? OutgoingContentInfoMessageAttribute { return info.withUpdatedFlags(info.flags.subtracting(.' + flag + ')) }; return attribute }'
    variants = {
        'current': code,
        'previous-payload': payload_fixture(source),
        'previous-temporary': temporary_fixture(source),
        'previous-composer': composer_fixture(source),
        'lost-caption-transport': code.replace(NEW_FILTER, OLD_FILTER),
        'lost-caption-copy-marker': code.replace(NEW_FILTER, stripped('nagramiXCopy')),
        'lost-caption-preview-policy': code.replace(NEW_FILTER, stripped('disableLinkPreviews')),
        'unsafe-retry-state': code.replace('guard message.flags.contains(.Failed), !message.flags.contains(.Incoming),', 'guard true,'),
        'lost-retry-identity': code.replace('globallyUniqueId: message.globallyUniqueId,', 'globallyUniqueId: nil,'),
    }
    positive = {'current', 'previous-payload', 'previous-temporary', 'previous-composer'}
    assert all(value != code for name, value in variants.items() if name not in positive)
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
                assert run.returncode != 0 and 'Round caption regression:' in run.stderr, run.stdout + run.stderr
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
    from validate_system_video_pip import delegate_icon_stage_if_applied
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_playback_commands'):
        return
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-round-caption-check-') as folder:
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
        'scope': 'R2 caption transport; R1 preserved; R3 native playback unchanged',
        'sdk': 'not authorized or run', 'device': 'pending',
        'boundaries': 'Current production copier, Foundation staging and production retry body run together. Postbox persistence, UIKit and Telegram RPC are explicit boundaries; no device execution.',
    }
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
