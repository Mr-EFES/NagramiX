#!/usr/bin/env python3
"""Execute topic read scope regressions on final overlay Swift, without an IPA."""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]
THREAD = 'submodules/TelegramCore/Sources/TelegramEngine/Messages/ReplyThreadHistory.swift'
ENQUEUE = 'submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift'
CORE = 'submodules/TelegramCore/Sources/'
HELPERS = ['NagramiXGhostReadActions.swift', 'NagramiXReadModeActions.swift']


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


def standalone(text):
    return '\n'.join(line for line in text.splitlines() if not line.startswith('import ') or line == 'import Foundation') + '\n'


def validate(before, after, swiftc):
    a, b = manifest(before), manifest(after)
    expected = {THREAD, ENQUEUE, *[CORE + n for n in HELPERS]}
    assert a.keys() == b.keys()
    assert {n for n in a if a[n] != b[n]} == expected
    plan = json.loads((ROOT / 'ios/thread_read_scope_patches.json').read_text())
    for n, sha in plan['hashes'].items():
        assert a[n] == sha
        restored = (after / n).read_text()
        for name, old, new, count in reversed(plan['patches']):
            if n == name:
                assert restored.count(new) == count
                restored = restored.replace(new, old, count)
        assert restored == (before / n).read_text(), 'Unrelated native change: ' + n
    for template, name in plan['provided'].items():
        assert (after / name).read_bytes() == (ROOT / 'ios' / template).read_bytes()
    # Native topic-local accounting is shared, not reimplemented for actions.
    old_thread = (before / THREAD).read_text()
    original_accounting = old_thread.split('            var markMainAsRead = false', 1)[1].split('            if markMainAsRead {', 1)[0]
    original_accounting = '            var markMainAsRead = false' + original_accounting
    ghost = (after / (CORE + HELPERS[0])).read_text()
    extracted = ghost.split('messageIndex: MessageIndex) -> Bool {\n', 1)[1].split('    return markMainAsRead\n}', 1)[0]
    assert extracted.rstrip() == textwrap.indent(textwrap.dedent(original_accounting).rstrip(), '    ')
    thread = (after / THREAD).read_text()
    assert thread.count('nagramiXApplyThreadReadIndex(') == 1
    assert 'if markMainAsRead && !NagramiXGhostSettings.current.hidesMessageReads {' in thread
    assert 'nagramiXRecordPrivateRead(transaction: transaction, index: messageIndex, threadId: threadId)' in thread
    assert thread.count('nagramiXAcknowledgePrivateRead(transaction: transaction, peerId: peerId, maxId: messageIndex.id.id, threadId: threadId)') == 2
    enqueue = (after / ENQUEUE).read_text()
    start = enqueue.index('            var nagramiXReadStarted = Set<NagramiXReadActionBoundary>()')
    dispatch = enqueue[start:enqueue.index('            return resultIds', start)]
    assert 'resultId != nil' in dispatch and 'threadId: boundary.threadId' in dispatch
    assert 'let hadImmediateSend' not in enqueue
    results = []
    spec = importlib.util.spec_from_file_location('thread_scope', ROOT / 'ios/thread_read_scope.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    rejected = 0
    with tempfile.TemporaryDirectory(prefix='nagramix-thread-scope-') as folder:
        folder = Path(folder)
        tests = ROOT / 'scripts/tests/NagramiXReadModeActionTests.swift'
        boundary = folder / 'Boundary.swift'
        boundary.write_text(tests.read_text().split('@main struct ReadModeActionTests', 1)[0])
        production = folder / 'EnqueueDispatch.swift'
        # Compile the actual native completion loop, with only its surrounding
        # account/UI dependencies substituted at the boundary.
        visible = thread.split('                |> mapToSignal { result -> Signal<Api.Bool, NoError> in\n', 1)[1].split('                }\n                |> ignoreValues', 1)[0]
        production.write_text('import Foundation\nfunc productionReadAfterEnqueue(account: Account, peerId: PeerId, resultIds: [MessageId?], nagramiXReadBoundaries: [NagramiXReadActionBoundary?]) {\n' + dispatch + '}\nfunc productionAcknowledgeVisibleThread(account: Account, peerId: PeerId, threadId: Int64, messageIndex: MessageIndex, result: Api.Bool) -> Signal<Api.Bool, NoError> {\n' + visible + '\n}\n')
        support_condition = enqueue.split('    if account.isSupportUser', 1)[1].split(' {\n', 1)[0]
        with production.open('a') as output:
            output.write('func productionSupportReadAllowed(account: Account) -> Bool { account.isSupportUser' + support_condition + ' }\n')
        model_names = ['NagramiXReadModeSettings.swift', 'NagramiXPrivacySettings.swift', 'NagramiXGhostSettings.swift', 'NagramiXStorySettings.swift']
        models = [after / 'submodules/NagramiXMediaSettings/Sources' / n for n in model_names]
        for n, model in zip(model_names, models):
            assert model.read_bytes() == (ROOT / 'ios/Sources/NagramiXMediaSettings/Sources' / n).read_bytes()
        old_sources, new_sources = [], []
        for label, native, target in [('old', before, old_sources), ('new', after, new_sources)]:
            for n in HELPERS:
                path = folder / (label + n); path.write_text(standalone((native / (CORE + n)).read_text())); target.append(path)
        regression = ROOT / 'scripts/tests/NagramiXThreadReadScopeRegression.swift'

        def run(label, sources, mode, regression_only=False):
            binary = folder / (label + '-' + mode)
            command = [str(swiftc), '-warnings-as-errors', '-module-cache-path', str(folder / 'cache'), *map(str, models + sources), '-o', str(binary)]
            if mode == 'optimized': command.insert(1, '-O')
            subprocess.run(command, check=True)
            result = subprocess.run([str(binary)], env=dict(os.environ, XDG_CONFIG_HOME=str(folder / (binary.name + '-preferences'))), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=40)
            if regression_only:
                assert result.returncode == 1 and 'broad RPCs=1' in result.stdout and 'broad local reads=1' in result.stdout, result.stdout
                results.append(mode + ': old regression reproduced: ' + result.stdout.strip())
            else:
                assert result.returncode == 0, result.stdout
                results.append(mode + ': ' + result.stdout.strip())
        for mode in ['debug', 'optimized']:
            run('old', [boundary, *old_sources, regression], mode, regression_only=True)
            run('new-regression', [boundary, *new_sources, regression], mode)
            run('new', [*new_sources, production, tests], mode)

        def seed(case_plan):
            source = folder / 'native'; overlay = folder / 'overlay'
            for n in set(plan['hashes']) | set(plan['provided'].values()):
                p = source / n; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes((before / n).read_bytes())
            for template, n in plan['provided'].items():
                (source / n).write_bytes((ROOT / 'ios' / template).read_bytes())
                p = overlay / template; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes((ROOT / 'ios' / template).read_bytes())
            (overlay / 'thread_read_scope_patches.json').write_text(json.dumps(case_plan))
            return source, overlay

        def reject(source, overlay):
            nonlocal rejected
            snapshot = manifest(source)
            try: module.apply_thread_read_scope(source, overlay)
            except (SystemExit, FileNotFoundError):
                assert snapshot == manifest(source), 'Partial write'
                rejected += 1
            else: raise AssertionError('Drift accepted')

        source, overlay = seed(plan); module.apply_thread_read_scope(source, overlay)
        for n in expected: assert (source / n).read_bytes() == (after / n).read_bytes()
        reject(source, overlay)
        for n in plan['hashes']:
            source, overlay = seed(plan); p = source / n; p.write_bytes(p.read_bytes() + b'\n// drift'); reject(source, overlay)
            source, overlay = seed(plan); (source / n).unlink(); reject(source, overlay)
        for n in plan['provided'].values():
            source, overlay = seed(plan); (source / n).write_text('drift'); reject(source, overlay)
        for n, old, _, _ in plan['patches']:
            case_plan = copy.deepcopy(plan); source, overlay = seed(case_plan)
            p = source / n; p.write_text(p.read_text().replace(old, '// moved anchor\n', 1))
            case_plan['hashes'][n] = hashlib.sha256(p.read_bytes()).hexdigest()
            (overlay / 'thread_read_scope_patches.json').write_text(json.dumps(case_plan)); reject(source, overlay)
        subprocess.run([str(swiftc), '-frontend', '-parse', *[str(after / n) for n in sorted(expected)]], check=True)
    for n in ['ios/thread_read_scope.py', 'ios/apply_features.py', 'scripts/validate_thread_read_scope.py']: ast.parse((ROOT / n).read_text())
    return {'outputs': len(b), 'changed': sorted(expected), 'unchanged': len(b) - len(expected), 'native_exact_reverse': 'PASS', 'shared_native_accounting': 'byte-identical body', 'overlay_replay': 'PASS', 'fail_closed_cases_without_writes': rejected, 'execution': results, 'Apple_SDK': 'not run', 'physical_iPhone': 'pending', 'IPA': 'not started'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for n in ['before', 'after', 'swiftc', 'report']: parser.add_argument('--' + n, type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.before, args.after, args.swiftc)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
