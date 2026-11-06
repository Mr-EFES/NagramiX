#!/usr/bin/env python3
"""Validate first-deletion dust while preserving archived row visibility and layout."""
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
PLAN = json.loads((OVERLAY / 'archive_deletion_effect_patches.json').read_text())
HISTORY = next(iter(PLAN['inputs']))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(source):
    for name, digest in {**PLAN['outputs'], **PLAN['guards']}.items():
        assert sha((source / name).read_bytes()) == digest, name
    for name, digest in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest, name
    source_code = (source / HISTORY).read_text()
    before_code = (OVERLAY / PLAN['previous'][HISTORY]).read_text()
    marker = '        // A native -> local replacement'
    end_marker = '        let animated = transition.options.contains(.AnimateInsertion)'
    def outside(text):
        a = text.index(marker); b = text.index(end_marker, a)
        return text[:a], text[b:]
    assert outside(source_code) == outside(before_code), 'Unrelated history/storage/geometry changed'
    pipeline = (OVERLAY / 'apply_overlay.py').read_text()
    assert pipeline.index('    apply_pip_visual_handoff(') < pipeline.index('    apply_archive_deletion_effect(')


def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location('archive_deletion_effect', OVERLAY / 'archive_deletion_effect.py')
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
            module.apply_archive_deletion_effect(tree, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Invalid input accepted: ' + label)
        assert manifest(tree) == previous, 'Partial mutation: ' + label
        rejected.append(label)

    valid = seed('valid')
    module.apply_archive_deletion_effect(valid, OVERLAY)
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
        (overlay / 'archive_deletion_effect_patches.json').write_text(json.dumps(bad))
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


def runtime_source(source):
    code = (source / HISTORY).read_text()
    weak = block(code, 'private final class NagramiXDustHiddenMessageNode')
    a = code.index('    private var nagramiXDustHiddenMessageNodes:')
    b = code.index('    func setCurrentDeleteAnimationCorrelationIds(', a)
    storage = code[a:b]
    a = code.index('        // A native -> local replacement')
    b = code.index('        let animated = transition.options.contains(.AnimateInsertion)', a)
    transition = code[a:b]
    boundary = (ROOT / 'scripts/tests/NagramiXArchiveDeletionVisibilityBoundary.swift').read_text()
    boundary = boundary.replace('struct Message { var stableId:', 'protocol MessageAttribute {}\nfinal class NagramiXArchivedMessageAttribute: MessageAttribute {}\nstruct Message { var attributes: [MessageAttribute] = []; var stableId:')
    entry_code = (source / 'submodules/TelegramUI/Components/Chat/ChatHistoryEntry/Sources/ChatHistoryEntry.swift').read_text()
    for case, marker in [('MessageEntry', 'MESSAGE_ENTRY'), ('MessageGroupEntry', 'GROUP_ENTRY')]:
        declaration = next(line.strip() for line in entry_code.splitlines() if line.strip().startswith('case ' + case + '('))
        for real, fake in [('EngineMessageHistoryEntryLocation','Int'),('EngineRawMessage','Message'),('ChatPresentationData','Int'),('ChatHistoryMessageSelection','Int'),('ChatMessageEntryAttributes','Int')]:
            declaration = declaration.replace(real, fake)
        boundary = boundary.replace('// PRODUCTION_' + marker + '_CASE', declaration)
    previous_tests = (ROOT / 'scripts/tests/NagramiXArchiveDeletionVisibilityTests.swift').read_text().replace('@main struct ', 'struct ')
    tests = (ROOT / 'scripts/tests/NagramiXArchiveDeletionEffectTests.swift').read_text()
    return boundary, weak, storage, transition, previous_tests, tests


def runtime_checks(source, swiftc, temp):
    boundary, weak, storage, transition, previous_tests, tests = runtime_source(source)
    before = (OVERLAY / PLAN['previous'][HISTORY]).read_text()
    a = before.index('        // A native -> local replacement')
    b = before.index('        let animated = transition.options.contains(.AnimateInsertion)', a)
    old = before[a:b]
    retained_gate = "                        if nagramiXRetainedDustNodeIds.contains(ObjectIdentifier(itemNode)) {\n                            continue\n                        }"
    assert transition.count(retained_gate) == 1
    phantom = retained_gate.replace('                            continue', '                            if let item = itemNode.item { appliedDeleteAnimationCorrelationIds.formUnion(item.content.map { $0.0.stableId }) }\n                            continue')
    native_only = transition.replace('(!self.currentDeleteAnimationCorrelationIds.isEmpty || !nagramiXNewlyArchivedMessageIds.isEmpty)', '!self.currentDeleteAnimationCorrelationIds.isEmpty')
    repeat = transition.replace('if !message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) {', 'if true {').replace('for value in messages where !value.0.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) {', 'for value in messages {')
    initial = transition.replace('        let nagramiXNewlyArchivedMessageIds =', '        if self.historyView == nil { nagramiXPreviousLiveMessageIds = nagramiXArchivedMessageIds }\n        let nagramiXNewlyArchivedMessageIds =')
    current_stable_ids = """        var nagramiXStableIds = Set<UInt32>()
        for entry in transition.historyView.filteredEntries {
            switch entry {
            case let .MessageEntry(message, _, _, _, _, _): nagramiXStableIds.insert(message.stableId)
            case let .MessageGroupEntry(_, messages, _): for value in messages { nagramiXStableIds.insert(value.0.stableId) }
            default: break
            }
        }
"""
    stable_only = current_stable_ids + transition.replace('nagramiXNewlyArchivedMessageIds.contains(message.id)', 'nagramiXNewlyArchivedMessageIds.contains(message.id) && !nagramiXStableIds.contains(message.stableId)')
    duplicate = transition.replace('if foundItemNodeIds.insert(ObjectIdentifier(itemNode)).inserted {', '_ = foundItemNodeIds.insert(ObjectIdentifier(itemNode))\n                            if true {')
    modes = {
        'current': transition,
        'previous-no-first-effect': old,
        'only-correlation-gate': native_only,
        'hide-retained-row': transition.replace(retained_gate, ''),
        'phantom-collapse': transition.replace(retained_gate, phantom),
        'stable-id-only': stable_only,
        'reanimate-archived-update': repeat,
        'animate-initial-load': initial,
        'ignore-effect-off': transition.replace(' && deletionEffectEnabled {', ' {'),
        'duplicate-album': duplicate,
    }
    results = []
    for name, body in modes.items():
        fixture = temp / (name + '.swift')
        code = boundary.replace('// PRODUCTION_WEAK_NODE', weak).replace('// PRODUCTION_RESTORE_AND_STORAGE', storage).replace('// PRODUCTION_TRANSITION', body)
        fixture.write_text(code + '\n' + previous_tests + '\n' + tests)
        for optimized in [False, True]:
            binary = temp / (name + ('-O' if optimized else '-debug'))
            subprocess.run([str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache'), *(['-O'] if optimized else []), str(fixture), '-o', str(binary)], check=True)
            run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if name == 'current':
                assert run.returncode == 0, run.stdout + run.stderr
                message = run.stdout.strip()
            else:
                assert run.returncode != 0 and ('Archive deletion effect regression:' in run.stderr or 'Archive deletion visibility regression:' in run.stderr), name + run.stdout + run.stderr
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
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_transition_geometry'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'transfer_consistency'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'editor_attachment_delivery'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'local_model_size'):
        return
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-deletion-effect-') as folder:
        temp = Path(folder)
        rejected = guard_checks(args.source, temp / 'guards')
        runtime = temp / 'runtime'
        runtime.mkdir()
        runs = runtime_checks(args.source, args.swiftc, runtime) if args.swiftc else []
        if args.swiftc:
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / HISTORY)], check=True)
    report = {'replacements': len(PLAN['outputs']), 'guards': len(PLAN['guards']), 'fail_closed': len(rejected), 'executions': runs, 'sdk': 'not run', 'device': 'pending', 'boundaries': 'Actual history transition and retained/native snapshot routing, including previous visibility/weak ownership suite. Renderer, archive storage and 50% opacity code stay byte-identical. UIKit/CA, snapshot and engine responses are doubles; device animation pending.'}
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
