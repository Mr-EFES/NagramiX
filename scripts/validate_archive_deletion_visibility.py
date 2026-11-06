#!/usr/bin/env python3
"""Validate real history dust admission and visibility when archive rows replace native rows."""
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

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'archive_deletion_visibility_patches.json').read_text())
HISTORY = next(iter(PLAN['inputs']))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(source):
    for name, digest in {**PLAN['outputs'], **PLAN['guards']}.items():
        assert sha((source / name).read_bytes()) == digest, name
    for name, digest in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest, name
    source_code = (source / HISTORY).read_text()
    before = (OVERLAY / PLAN['previous'][HISTORY]).read_text()
    # Exact native grouping, retention, read, deletion ownership, and list
    # geometry outside the reviewed transition/storage ranges stay unchanged.
    def outside(text, after):
        if after:
            text = text.replace(block(text, 'private final class NagramiXDustHiddenMessageNode'), '')
            a = text.index('    private var nagramiXDustHiddenMessageNodes:')
            b = text.index('    private var currentDeleteAnimationCorrelationIds', a)
            text = text[:a] + text[b:]
        start = text.index('        // A native -> local replacement') if after else text.index('        var expiredMessageStableIds = Set<UInt32>()')
        end = text.index('        let animated = transition.options.contains(.AnimateInsertion)', start)
        return text[:start], text[end:]
    old_prefix, old_suffix = outside(before, False)
    new_prefix, new_suffix = outside(source_code, True)
    # Only the explanatory comment preceding the weak wrapper differs here.
    new_prefix = new_prefix.replace('// The dust snapshot must not keep a list cell alive or leave a cell reused\n// for an archived copy hidden after the original disappears from Postbox.\n\n\n', '')
    assert old_prefix == new_prefix, 'Unrelated history code changed'
    assert old_suffix == new_suffix, 'Unrelated list layout/storage changed'
    pipeline = (OVERLAY / 'apply_overlay.py').read_text()
    assert pipeline.index('    apply_temporary_media_actions(') < pipeline.index('    apply_archive_deletion_visibility(')


def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location('archive_deletion_visibility', OVERLAY / 'archive_deletion_visibility.py')
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
        previous = manifest(tree)
        try:
            module.apply_archive_deletion_visibility(tree, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Invalid input accepted: ' + label)
        assert manifest(tree) == previous, 'Partial mutation: ' + label
        rejected.append(label)

    valid = seed('valid')
    module.apply_archive_deletion_visibility(valid, OVERLAY)
    assert (valid / HISTORY).read_bytes() == (source / HISTORY).read_bytes()
    reject(valid, 'repeat')
    for i, name in enumerate({**PLAN['inputs'], **PLAN['guards']}):
        for kind in ['missing', 'drift']:
            tree = seed(str(i) + '-' + kind)
            if kind == 'missing':
                (tree / name).unlink()
            else:
                (tree / name).write_bytes(b'changed')
            reject(tree, kind + ' ' + name)
    variants = []
    for field in ['inputs', 'outputs', 'guards', 'templates']:
        bad = copy.deepcopy(PLAN)
        bad[field][next(iter(bad[field]))] = '0' * 64
        variants.append((field, bad))
    for field in ['previous', 'replacements']:
        bad = copy.deepcopy(PLAN)
        bad[field][HISTORY] = '../outside.swift'
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
        (overlay / 'archive_deletion_visibility_patches.json').write_text(json.dumps(bad))
        reject(seed('source-' + label), label, overlay)
    for i, name in enumerate([HISTORY, next(iter(PLAN['guards']))]):
        tree = seed('symlink-' + str(i))
        path = tree / name
        outside = temp / ('external-' + str(i))
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
        reject(tree, 'external symlink ' + name)
    return rejected


def runtime_checks(source, swiftc, temp):
    code = (source / HISTORY).read_text()
    before = (OVERLAY / PLAN['previous'][HISTORY]).read_text()
    weak = block(code, 'private final class NagramiXDustHiddenMessageNode')
    a = code.index('    private var nagramiXDustHiddenMessageNodes:')
    b = code.index('    func setCurrentDeleteAnimationCorrelationIds(', a)
    storage = code[a:b]
    a = code.index('        // A native -> local replacement')
    b = code.index('        let animated = transition.options.contains(.AnimateInsertion)', a)
    transition = code[a:b]
    a = before.index('        var expiredMessageStableIds = Set<UInt32>()')
    b = before.index('        let animated = transition.options.contains(.AnimateInsertion)', a)
    old_transition = before[a:b]
    no_identity = transition.replace(' && !nagramiXExistingMessageIds.contains(message.id)', '').replace(' || nagramiXExistingMessageIds.contains(message.0.id)', '')
    no_restore = storage.replace(block(storage, '    private func nagramiXRestoreRetainedDeletionNodes('), '    private func nagramiXRestoreRetainedDeletionNodes(existingMessageIds: Set<EngineMessage.Id>) {}')
    premature_duration = transition.replace('matchedDeleteAnimationCorrelationIds.insert(message.stableId)', 'matchedDeleteAnimationCorrelationIds.insert(message.stableId)\n                            appliedDeleteAnimationCorrelationIds.insert(message.stableId)')
    no_dedup = transition.replace('if foundItemNodeIds.insert(ObjectIdentifier(itemNode)).inserted {', 'if true {')
    # Keep the collection referenced to avoid a diagnostic masking the regression.
    no_dedup = no_dedup.replace('if true {\n                                foundItemNodes', '_ = foundItemNodeIds.insert(ObjectIdentifier(itemNode))\n                            if true {\n                                foundItemNodes')
    modes = {
        'current': (weak, storage, transition),
        'previous-transition': (weak, storage, old_transition),
        'stable-id-only': (weak, storage, no_identity),
        'no-restore': (weak, no_restore, transition),
        'premature-duration': (weak, storage, premature_duration),
        'duplicate-album': (weak, storage, no_dedup),
        'strong-ownership': (weak.replace('weak var node:', 'var node:'), storage, transition),
    }
    boundary = (ROOT / 'scripts/tests/NagramiXArchiveDeletionVisibilityBoundary.swift').read_text()
    # Keep the real public enum case shapes: album members are five-tuples,
    # whereas ChatMessageItem.content uses pairs. A pair-only mock misses SDK errors.
    entry_code=(source/'submodules/TelegramUI/Components/Chat/ChatHistoryEntry/Sources/ChatHistoryEntry.swift').read_text()
    for case, marker in [('MessageEntry','MESSAGE_ENTRY'),('MessageGroupEntry','GROUP_ENTRY')]:
        declaration=next(line.strip() for line in entry_code.splitlines() if line.strip().startswith('case '+case+'('))
        for real, fake in [('EngineMessageHistoryEntryLocation','Int'),('EngineRawMessage','Message'),('ChatPresentationData','Int'),('ChatHistoryMessageSelection','Int'),('ChatMessageEntryAttributes','Int')]:
            declaration=declaration.replace(real,fake)
        boundary=boundary.replace('// PRODUCTION_'+marker+'_CASE',declaration)

    tests = ROOT / 'scripts/tests/NagramiXArchiveDeletionVisibilityTests.swift'
    results = []
    for name, (node, state, body) in modes.items():
        fixture = temp / (name + '.swift')
        fixture.write_text(boundary.replace('// PRODUCTION_WEAK_NODE', node).replace('// PRODUCTION_RESTORE_AND_STORAGE', state).replace('// PRODUCTION_TRANSITION', body))
        for optimized in [False, True]:
            binary = temp / (name + ('-O' if optimized else '-debug'))
            subprocess.run([str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache'), *(['-O'] if optimized else []), str(fixture), str(tests), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if name == 'current':
                assert result.returncode == 0, result.stdout + result.stderr
                message = result.stdout.strip()
            else:
                assert result.returncode != 0 and 'Archive deletion visibility regression:' in result.stderr, name + result.stdout + result.stderr
                message = 'regression reproduced and rejected'
            results.append(binary.name + ': ' + message)
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
    if delegate_icon_stage_if_applied(args, Path(__file__), 'round_caption_transport'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'repost_copy_integrity'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'native_pip_baseline'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'copy_delivery'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'rich_draft_upload_retry'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_transition_geometry'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'transfer_consistency'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'editor_attachment_delivery'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'local_model_size'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'archive_deletion_effect'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_visual_handoff'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'local_model_menu'):
        return
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-deletion-visibility-') as folder:
        temp = Path(folder)
        rejected = guard_checks(args.source, temp / 'guards')
        runtime = temp / 'runtime'
        runtime.mkdir()
        runs = runtime_checks(args.source, args.swiftc, runtime) if args.swiftc else []
        if args.swiftc:
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / HISTORY)], check=True)
    report = {'replacements': len(PLAN['outputs']), 'guards': len(PLAN['guards']), 'fail_closed': len(rejected), 'executions': runs, 'sdk': 'not run', 'device': 'pending', 'boundaries': 'Actual history transition, dust gating, node visibility and weak ownership. UIKit/CA snapshots and native deletion engine answers are doubles; no device animation result is claimed.'}
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
